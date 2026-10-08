from unittest import mock

from django.urls import reverse
from rest_framework import status

from galaxy_ng.app.api.v3.serializers import NamespaceSerializer
from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import NamespaceLink
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase

LEGACY_LINK_URL = 'https://example.com/$(whoami)'
SAFE_LINK_URL = 'https://example.com/docs'
SAFE_LINK_URL_OTHER = 'https://example.com/other'
SAFE_LINK_URL_V2 = 'https://example.com/v2'
# Tier 1 rejects `$()`; used to assert URL-only edits revalidate the name.
LEGACY_LINK_NAME = 'Docs$(whoami)'


def _link_error_keys(errors):
    keys = set()
    for err in errors.get('links', []):
        keys.update(err.keys())
    return keys


@mock.patch('ansible_base.lib.serializers.mixins.get_setting', return_value=True)
class TestNamespaceLinkGrandfathering(BaseTestCase):
    """Nested many=True links must grandfather unchanged stored rows.

    DRF does not bind child.instance during list validation, so without the
    NamespaceLinkListSerializer match, an unmodified legacy link would be
    re-rejected on an unrelated namespace update.
    """

    def _namespace_with_link(self, name, link_name='Docs', url=LEGACY_LINK_URL):
        namespace = self._create_namespace(name)
        NamespaceLink.objects.create(namespace=namespace, name=link_name, url=url)
        return namespace

    def _update_payload(self, namespace, description='updated description', links=None):
        if links is None:
            links = [{'name': link.name, 'url': link.url} for link in namespace.links.all()]
        return {
            'name': namespace.name,
            'description': description,
            'links': links,
        }

    def test_unchanged_legacy_link_is_grandfathered_on_description_update(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_desc')
        serializer = NamespaceSerializer(
            namespace, data=self._update_payload(namespace, description='new description'))

        self.assertTrue(serializer.is_valid(), serializer.errors)
        self.assertIsNone(serializer.fields['links'].child.instance)

    def test_partial_description_patch_without_links_is_valid(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_patch')
        serializer = NamespaceSerializer(
            namespace, data={'description': 'new description'}, partial=True)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_rejects_dangerous_link(self, mock_get_setting):
        serializer = NamespaceSerializer(data={
            'name': 'ns_link_gf_create',
            'links': [{'name': 'Docs', 'url': LEGACY_LINK_URL}],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__url', _link_error_keys(serializer.errors))

    def test_create_accepts_display_caption_punctuation(self, mock_get_setting):
        """Captions are Tier 2 labels; parentheses, &, and / must be allowed."""
        for caption in ('Docs (EN)', 'Q&A', 'GitHub / Docs'):
            with self.subTest(caption=caption):
                serializer = NamespaceSerializer(data={
                    'name': 'ns_link_caption_ok',
                    'links': [{'name': caption, 'url': SAFE_LINK_URL}],
                })
                self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_create_rejects_html_in_link_caption(self, mock_get_setting):
        serializer = NamespaceSerializer(data={
            'name': 'ns_link_caption_html',
            'links': [{'name': 'Docs <b>EN</b>', 'url': SAFE_LINK_URL}],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__name', _link_error_keys(serializer.errors))

    def test_update_rejects_html_in_edited_link_caption(self, mock_get_setting):
        """Edited captions follow the same Tier 2 rule as new ones."""
        namespace = self._namespace_with_link('ns_link_caption_edit', url=SAFE_LINK_URL)
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs <b>EN</b>', 'url': SAFE_LINK_URL},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__name', _link_error_keys(serializer.errors))

    def test_new_dangerous_link_on_update_is_rejected(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_new', url=SAFE_LINK_URL)
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs', 'url': SAFE_LINK_URL},
            {'name': 'Evil', 'url': LEGACY_LINK_URL},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__url', _link_error_keys(serializer.errors))

    def test_edited_legacy_link_is_revalidated(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_edit')
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs', 'url': 'https://example.com/$(other)'},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__url', _link_error_keys(serializer.errors))

    def test_url_update_on_legacy_invalid_name_is_revalidated(self, mock_get_setting):
        """URL-only edits must not grandfather an invalid stored name."""
        namespace = self._namespace_with_link(
            'ns_link_gf_name_url', link_name=LEGACY_LINK_NAME, url=SAFE_LINK_URL)
        payload = self._update_payload(namespace, links=[
            {'name': LEGACY_LINK_NAME, 'url': SAFE_LINK_URL_OTHER},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__name', _link_error_keys(serializer.errors))

    def test_fixing_legacy_invalid_name_and_url_in_same_update_is_valid(
            self, mock_get_setting):
        namespace = self._namespace_with_link(
            'ns_link_gf_name_url_fix', link_name=LEGACY_LINK_NAME, url=SAFE_LINK_URL)
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs', 'url': SAFE_LINK_URL_V2},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_unchanged_legacy_invalid_name_is_grandfathered(self, mock_get_setting):
        namespace = self._namespace_with_link(
            'ns_link_gf_name_ok', link_name=LEGACY_LINK_NAME, url=SAFE_LINK_URL)
        serializer = NamespaceSerializer(
            namespace, data=self._update_payload(namespace, description='new description'))

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_replacing_legacy_link_with_safe_url_is_valid(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_replace')
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs', 'url': SAFE_LINK_URL},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_reordered_unchanged_links_are_grandfathered(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_reorder')
        NamespaceLink.objects.create(
            namespace=namespace, name='Home', url=SAFE_LINK_URL)
        payload = self._update_payload(namespace, links=[
            {'name': 'Home', 'url': SAFE_LINK_URL},
            {'name': 'Docs', 'url': LEGACY_LINK_URL},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertTrue(serializer.is_valid(), serializer.errors)

    def test_duplicating_a_legacy_link_is_rejected(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_dup')
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs', 'url': LEGACY_LINK_URL},
            {'name': 'Docs', 'url': LEGACY_LINK_URL},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__url', _link_error_keys(serializer.errors))

    def test_copying_legacy_url_onto_a_new_name_is_rejected(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_gf_copy')
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs', 'url': LEGACY_LINK_URL},
            {'name': 'Mirror', 'url': LEGACY_LINK_URL},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__url', _link_error_keys(serializer.errors))

    def test_create_rejects_non_string_link_name(self, mock_get_setting):
        serializer = NamespaceSerializer(data={
            'name': 'ns_link_bad_name',
            'links': [{'name': ['not', 'a', 'string'], 'url': SAFE_LINK_URL}],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__name', _link_error_keys(serializer.errors))

    def test_create_rejects_non_string_link_url(self, mock_get_setting):
        serializer = NamespaceSerializer(data={
            'name': 'ns_link_bad_url',
            'links': [{'name': 'Docs', 'url': {'not': 'a string'}}],
        })

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__url', _link_error_keys(serializer.errors))

    def test_update_rejects_non_string_link_name(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_bad_name_upd', url=SAFE_LINK_URL)
        payload = self._update_payload(namespace, links=[
            {'name': {'bad': 'type'}, 'url': SAFE_LINK_URL},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__name', _link_error_keys(serializer.errors))

    def test_update_rejects_non_string_link_url(self, mock_get_setting):
        namespace = self._namespace_with_link('ns_link_bad_url_upd', url=SAFE_LINK_URL)
        payload = self._update_payload(namespace, links=[
            {'name': 'Docs', 'url': ['https://example.com']},
        ])
        serializer = NamespaceSerializer(namespace, data=payload)

        self.assertFalse(serializer.is_valid())
        self.assertIn('links__url', _link_error_keys(serializer.errors))


@mock.patch('ansible_base.lib.serializers.mixins.get_setting', return_value=True)
class TestV3NamespaceLinkGrandfatheringApi(BaseTestCase):
    deployment_mode = DeploymentMode.STANDALONE.value

    def setUp(self):
        super().setUp()
        self.admin_user = auth_models.User.objects.create(username='ns_link_gf_admin')
        self.pe_group = self._create_partner_engineer_group()
        self.admin_user.groups.add(self.pe_group)
        self.admin_user.save()
        self.client.force_authenticate(user=self.admin_user)

    def test_put_description_with_unchanged_legacy_link_succeeds(self, mock_get_setting):
        namespace = self._create_namespace('ns_link_gf_api', groups=[self.pe_group])
        NamespaceLink.objects.create(
            namespace=namespace, name='Docs', url=LEGACY_LINK_URL)
        ns_detail_url = reverse(
            'galaxy:api:v3:namespaces-detail', kwargs={'name': namespace.name})

        with self.settings(GALAXY_DEPLOYMENT_MODE=self.deployment_mode):
            response = self.client.put(ns_detail_url, {
                'name': namespace.name,
                'description': 'updated via put',
                'links': [{'name': 'Docs', 'url': LEGACY_LINK_URL}],
            }, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
        self.assertEqual(response.data['description'], 'updated via put')
        self.assertEqual(response.data['links'], [
            {'name': 'Docs', 'url': LEGACY_LINK_URL},
        ])
