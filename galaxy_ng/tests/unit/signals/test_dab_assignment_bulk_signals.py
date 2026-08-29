"""Regression tests for the DAB bulk-assignment signal handlers.

These tests exercise the real DAB bulk grant/remove pipeline (``bulk_give_permissions`` /
``bulk_remove_permissions`` / ``save_user_claims``) rather than calling the Galaxy signal
receivers directly with mocks. They cover the bug that motivated migrating the four per-row
receivers (``copy_dab_*_role_assignment`` / ``delete_dab_*_role_assignment``) onto the two
bulk signals ``dab_rbac_assignments_created`` / ``dab_rbac_assignments_pre_delete``:

    The JWT/SSO claim path grants object roles through ``bulk_give_permissions``, which uses
    ``bulk_create`` and therefore skips Django's per-row ``post_save``. The old per-row
    receivers never fired for those grants, so JWT/SSO-granted roles were not mirrored into
    Pulp ``Role`` objects or Django ``Group`` membership. The bulk signals fire on every
    path, so the mirror now happens for the bulk/JWT path too.
"""
from django.test import TestCase

from ansible_base.rbac.claims import save_user_claims
from ansible_base.rbac.models import RoleDefinition
from ansible_base.rbac.pipeline import bulk_give_permissions, bulk_remove_permissions

from pulpcore.plugin.models.role import UserRole, GroupRole

from galaxy_ng.app.models import User, Team, Namespace
from galaxy_ng.app.models.organization import Organization
from galaxy_ng.app.signals.handlers import dab_rbac_signals


# A Galaxy role that exists both as a DAB RoleDefinition and a Pulp Role, so assignments
# should be mirrored into Pulp.
NAMESPACE_ROLE = "galaxy.collection_namespace_owner"

# A global/singleton role that exists both as a DAB RoleDefinition ("Platform Auditor")
# and a Pulp Role ("galaxy.auditor"), and is a JWT-managed role. Global assignments carry
# no content object (object_id / content_type are None), so they exercise the null-object
# path through the bulk handlers.
GLOBAL_ROLEDEF = "Platform Auditor"
GLOBAL_PULP_ROLE = "galaxy.auditor"


class TestBulkGrantMirrorsToPulp(TestCase):
    """Newly-created assignments made through the bulk path mirror into Pulp / Django."""

    def setUp(self):
        self.user = User.objects.create(username="bulk_user")
        self.namespace = Namespace.objects.create(name="bulk_namespace")
        self.namespace_rd = RoleDefinition.objects.get(name=NAMESPACE_ROLE)

        self.org = Organization.objects.create(name="Bulk Org")
        self.team = Team.objects.create(name="Bulk Team", organization=self.org)
        self.group = self.team.group
        self.team_member_rd = RoleDefinition.objects.get(name="Team Member")

    def test_bulk_give_user_object_role_creates_pulp_user_role(self):
        """The core bug: a role granted via the bulk (JWT-style) path is mirrored to Pulp.

        ``bulk_give_permissions`` uses ``bulk_create`` which skips ``post_save`` -- the
        reason the old per-row receiver missed JWT grants. The bulk signal fixes it.
        """
        self.assertFalse(
            UserRole.objects.filter(user=self.user, role__name=NAMESPACE_ROLE).exists()
        )

        bulk_give_permissions(
            user_permissions=[(self.namespace_rd, self.user, self.namespace)]
        )

        self.assertTrue(
            UserRole.objects.filter(user=self.user, role__name=NAMESPACE_ROLE).exists(),
            "Bulk-granted user role should be mirrored into a Pulp UserRole",
        )

    def test_bulk_give_team_object_role_creates_pulp_group_role(self):
        """A team assignment via the bulk path mirrors into a Pulp GroupRole."""
        self.assertFalse(
            GroupRole.objects.filter(group=self.group, role__name=NAMESPACE_ROLE).exists()
        )

        bulk_give_permissions(
            team_permissions=[(self.namespace_rd, self.team, self.namespace)]
        )

        self.assertTrue(
            GroupRole.objects.filter(group=self.group, role__name=NAMESPACE_ROLE).exists(),
            "Bulk-granted team role should be mirrored into a Pulp GroupRole",
        )

    def test_bulk_give_team_member_to_user_adds_to_django_group(self):
        """A ``Team Member`` user assignment via the bulk path lands the user in the Group."""
        self.assertNotIn(self.user, self.group.user_set.all())

        bulk_give_permissions(
            user_permissions=[(self.team_member_rd, self.user, self.team)]
        )

        self.assertIn(
            self.user,
            self.group.user_set.all(),
            "Bulk-granted Team Member should add the user to the team's Django Group",
        )

    def test_idempotent_regrant_does_not_duplicate(self):
        """Re-granting the same role sends no ``created`` signal (no duplicate mirror)."""
        first = bulk_give_permissions(
            user_permissions=[(self.namespace_rd, self.user, self.namespace)]
        )
        self.assertTrue(first, "First grant should create an assignment")

        # A second, identical grant creates nothing -- so no created signal fires.
        second = bulk_give_permissions(
            user_permissions=[(self.namespace_rd, self.user, self.namespace)]
        )
        self.assertEqual(second, [], "Idempotent re-grant should create no new assignments")

        self.assertEqual(
            UserRole.objects.filter(user=self.user, role__name=NAMESPACE_ROLE).count(),
            1,
            "Idempotent re-grant should not duplicate the Pulp UserRole",
        )

    def test_reentrancy_guard_short_circuits(self):
        """While a mirror write is in progress, the bulk handler does not re-mirror.

        Simulates the mirror-write context (``dab_rbac_signals``) being active when a grant
        happens; the handler must short-circuit so its own writes don't bounce back.
        """
        with dab_rbac_signals():
            bulk_give_permissions(
                user_permissions=[(self.namespace_rd, self.user, self.namespace)]
            )

        self.assertFalse(
            UserRole.objects.filter(user=self.user, role__name=NAMESPACE_ROLE).exists(),
            "Grant made while an RBAC signal is in progress must not be mirrored to Pulp",
        )


class TestBulkRemoveUnmirrors(TestCase):
    """Removals through the bulk path un-mirror from Pulp / Django Group membership."""

    def setUp(self):
        self.user = User.objects.create(username="remove_user")
        self.namespace = Namespace.objects.create(name="remove_namespace")
        self.namespace_rd = RoleDefinition.objects.get(name=NAMESPACE_ROLE)

        self.org = Organization.objects.create(name="Remove Org")
        self.team = Team.objects.create(name="Remove Team", organization=self.org)
        self.group = self.team.group
        self.team_member_rd = RoleDefinition.objects.get(name="Team Member")
        self.team_admin_rd = RoleDefinition.objects.get(name="Team Admin")

    def test_bulk_remove_user_object_role_removes_pulp_user_role(self):
        """Removing a user object role via the bulk path removes the Pulp UserRole."""
        bulk_give_permissions(
            user_permissions=[(self.namespace_rd, self.user, self.namespace)]
        )
        self.assertTrue(
            UserRole.objects.filter(user=self.user, role__name=NAMESPACE_ROLE).exists()
        )

        bulk_remove_permissions(
            user_permissions=[(self.namespace_rd, self.user, self.namespace)]
        )

        self.assertFalse(
            UserRole.objects.filter(user=self.user, role__name=NAMESPACE_ROLE).exists(),
            "Bulk removal should remove the mirrored Pulp UserRole",
        )

    def test_remove_one_team_role_keeps_group_when_other_survives(self):
        """Removing Team Admin keeps the user in the Group while Team Member survives."""
        bulk_give_permissions(
            user_permissions=[
                (self.team_member_rd, self.user, self.team),
                (self.team_admin_rd, self.user, self.team),
            ]
        )
        self.assertIn(self.user, self.group.user_set.all())

        # Remove only Team Admin; Team Member still grants membership.
        bulk_remove_permissions(
            user_permissions=[(self.team_admin_rd, self.user, self.team)]
        )

        self.assertIn(
            self.user,
            self.group.user_set.all(),
            "User should stay in the Group while Team Member still grants membership",
        )

    def test_remove_both_team_roles_in_one_batch_removes_from_group(self):
        """The same-batch case: the last two grants removed together clear group membership.

        Both Team Member and Team Admin are removed in a single ``bulk_remove_permissions``
        call. Because the signal fires ``pre_delete``, both rows still exist in the DB when
        the handler runs; the handler must exclude the batch's own PKs from the
        "does another assignment survive?" check, otherwise the user would be wrongly kept
        in the Group.
        """
        bulk_give_permissions(
            user_permissions=[
                (self.team_member_rd, self.user, self.team),
                (self.team_admin_rd, self.user, self.team),
            ]
        )
        self.assertIn(self.user, self.group.user_set.all())

        bulk_remove_permissions(
            user_permissions=[
                (self.team_member_rd, self.user, self.team),
                (self.team_admin_rd, self.user, self.team),
            ]
        )

        self.assertNotIn(
            self.user,
            self.group.user_set.all(),
            "Removing every team-role grant in one batch should remove the user from "
            "the Group, even though the competing grant is in the same delete batch",
        )


class TestMultiItemBatches(TestCase):
    """Batches with many assignments mirror correctly (the batched-lookup paths).

    The handlers resolve Pulp role existence and team-membership survival once for the
    whole batch and coalesce Group writes per Group, rather than iterating one row at a
    time. These tests exercise those paths with N > 1 so a regression in the batched
    logic (e.g. a wrong grouping key or an over-broad survivor query) is caught.
    """

    def setUp(self):
        self.org = Organization.objects.create(name="Multi Org")
        self.team = Team.objects.create(name="Multi Team", organization=self.org)
        self.group = self.team.group
        self.namespace_rd = RoleDefinition.objects.get(name=NAMESPACE_ROLE)
        self.team_member_rd = RoleDefinition.objects.get(name="Team Member")
        self.users = [User.objects.create(username=f"multi_user_{i}") for i in range(3)]
        self.namespaces = [Namespace.objects.create(name=f"multi_ns_{i}") for i in range(3)]

    def test_many_object_roles_one_batch_all_mirrored(self):
        """Every user object role in a single bulk grant is mirrored into Pulp."""
        bulk_give_permissions(
            user_permissions=[
                (self.namespace_rd, user, ns)
                for user, ns in zip(self.users, self.namespaces, strict=True)
            ]
        )

        for user, ns in zip(self.users, self.namespaces, strict=True):
            self.assertTrue(
                UserRole.objects.filter(
                    user=user, role__name=NAMESPACE_ROLE, object_id=ns.pk
                ).exists(),
                f"Object role for {user.username} should be mirrored to a Pulp UserRole",
            )

    def test_many_team_members_one_batch_all_added_to_group(self):
        """Granting Team Member to several users in one batch adds them all to the Group."""
        bulk_give_permissions(
            user_permissions=[(self.team_member_rd, user, self.team) for user in self.users]
        )

        members = set(self.group.user_set.all())
        for user in self.users:
            self.assertIn(user, members, f"{user.username} should be in the team Group")

    def test_many_team_members_removed_one_batch_all_removed_from_group(self):
        """Removing every Team Member in one batch clears them all from the Group."""
        bulk_give_permissions(
            user_permissions=[(self.team_member_rd, user, self.team) for user in self.users]
        )
        self.assertEqual(set(self.group.user_set.all()), set(self.users))

        bulk_remove_permissions(
            user_permissions=[(self.team_member_rd, user, self.team) for user in self.users]
        )

        self.assertEqual(
            set(self.group.user_set.all()),
            set(),
            "Removing every Team Member in one batch should empty the Group",
        )

    def test_removing_some_team_members_leaves_others(self):
        """A batched removal must not evict users whose grants are not in the batch.

        This guards the survivor query: it uses ``user_id__in``/``object_id__in`` (a cross
        product) but the per-row decision checks the exact ``(user_id, object_id)`` pair,
        so removing one user's grant must not remove a different user still in the team.
        """
        bulk_give_permissions(
            user_permissions=[(self.team_member_rd, user, self.team) for user in self.users]
        )

        # Remove only the first user's Team Member grant.
        bulk_remove_permissions(
            user_permissions=[(self.team_member_rd, self.users[0], self.team)]
        )

        members = set(self.group.user_set.all())
        self.assertNotIn(self.users[0], members, "Removed user should leave the Group")
        self.assertIn(self.users[1], members, "Other users must remain in the Group")
        self.assertIn(self.users[2], members, "Other users must remain in the Group")


class TestGlobalRoleMirrorsToPulp(TestCase):
    """Global/singleton role assignments (no content object) mirror into global Pulp roles.

    The DAB branch routes ``give_global_permission`` / ``remove_global_permission`` through
    the bulk pipeline, so these fire the same ``dab_rbac_assignments_created`` /
    ``dab_rbac_assignments_pre_delete`` signals. The payload carries a null content object
    (``object_id``/``content_type`` are ``None`` and ``content_objects`` is empty), so this
    exercises the null-object path the handlers must tolerate. Pre-migration behavior was to
    ``assign_role``/``remove_role`` with no ``obj``, creating a global (object-less) Pulp
    ``UserRole``/``GroupRole``; these tests assert that behavior is preserved.
    """

    def setUp(self):
        self.user = User.objects.create(username="global_user")
        self.org = Organization.objects.create(name="Global Org")
        self.team = Team.objects.create(name="Global Team", organization=self.org)
        self.group = self.team.group
        self.global_rd = RoleDefinition.objects.get(name=GLOBAL_ROLEDEF)

    def _global_user_role_qs(self):
        return UserRole.objects.filter(
            user=self.user, role__name=GLOBAL_PULP_ROLE, object_id__isnull=True
        )

    def _global_group_role_qs(self):
        return GroupRole.objects.filter(
            group=self.group, role__name=GLOBAL_PULP_ROLE, object_id__isnull=True
        )

    def test_give_global_permission_user_creates_global_pulp_user_role(self):
        """``rd.give_global_permission(user)`` mirrors to an object-less Pulp UserRole."""
        self.assertFalse(self._global_user_role_qs().exists())

        self.global_rd.give_global_permission(self.user)

        self.assertTrue(
            self._global_user_role_qs().exists(),
            "Global user role should be mirrored into an object-less Pulp UserRole",
        )

    def test_remove_global_permission_user_removes_global_pulp_user_role(self):
        """``rd.remove_global_permission(user)`` un-mirrors the global Pulp UserRole."""
        self.global_rd.give_global_permission(self.user)
        self.assertTrue(self._global_user_role_qs().exists())

        self.global_rd.remove_global_permission(self.user)

        self.assertFalse(
            self._global_user_role_qs().exists(),
            "Removing the global user role should remove the mirrored Pulp UserRole",
        )

    def test_give_global_permission_team_creates_global_pulp_group_role(self):
        """``rd.give_global_permission(team)`` mirrors to an object-less Pulp GroupRole."""
        self.assertFalse(self._global_group_role_qs().exists())

        self.global_rd.give_global_permission(self.team)

        self.assertTrue(
            self._global_group_role_qs().exists(),
            "Global team role should be mirrored into an object-less Pulp GroupRole",
        )

    def test_remove_global_permission_team_removes_global_pulp_group_role(self):
        """``rd.remove_global_permission(team)`` un-mirrors the global Pulp GroupRole."""
        self.global_rd.give_global_permission(self.team)
        self.assertTrue(self._global_group_role_qs().exists())

        self.global_rd.remove_global_permission(self.team)

        self.assertFalse(
            self._global_group_role_qs().exists(),
            "Removing the global team role should remove the mirrored Pulp GroupRole",
        )

    def test_save_user_claims_global_role_mirrors_to_pulp(self):
        """The JWT/SSO claim path grants a global role via ``give_global_permission``.

        ``save_user_claims`` applies each JWT-managed global role through
        ``rd.give_global_permission(user)``, which routes through the bulk pipeline and
        fires the created signal. The global role in the claim set must be mirrored into an
        object-less Pulp UserRole.
        """
        self.assertFalse(self._global_user_role_qs().exists())

        save_user_claims(
            user=self.user,
            objects={},
            object_roles={},
            global_roles=[GLOBAL_ROLEDEF],
        )

        self.assertTrue(
            self._global_user_role_qs().exists(),
            "A global role in the JWT claim set should be mirrored into a Pulp UserRole",
        )
