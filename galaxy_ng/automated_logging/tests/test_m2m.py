""" Test all Many-To-Many related things """


import random

from automated_logging.helpers import Operation
from automated_logging.models import ModelEvent
from automated_logging.tests.models import (
    M2MTest,
    OrdinaryTest,
    OneToOneTest,
    ForeignKeyTest,
)
from automated_logging.signals.m2m import find_m2m_rel
from automated_logging.tests.base import BaseTestCase
from automated_logging.tests.helpers import random_string


class LoggedOutM2MRelationshipsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        # delete all previous model events
        ModelEvent.objects.all().delete()

    @staticmethod
    def generate_children(samples=10):
        """ generate X children that are going to be used in various tests """
        children = [OrdinaryTest(random=random_string()) for _ in range(samples)]
        [c.save() for c in children]

        return children

    def test_add(self):
        """ check if adding X members works correctly """

        samples = 10
        children = self.generate_children(samples)

        m2m = M2MTest()
        m2m.save()

        ModelEvent.objects.all().delete()
        m2m.relationship.add(*children)
        m2m.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertEqual(event.modifications.count(), 0)
        self.assertEqual(event.relationships.count(), samples)

        children = {str(c.id): c for c in children}

        for relationship in event.relationships.all():
            self.assertEqual(relationship.operation, int(Operation.CREATE))
            self.assertEqual(relationship.field.name, 'relationship')
            self.assertIn(relationship.entry.primary_key, children)

    def test_delete(self):
        """ check if deleting X elements works correctly """

        samples = 10
        removed = 5
        children = self.generate_children(samples)

        m2m = M2MTest()
        m2m.save()
        m2m.relationship.add(*children)
        m2m.save()
        ModelEvent.objects.all().delete()

        selected = random.sample(children, k=removed)
        m2m.relationship.remove(*selected)
        m2m.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertEqual(event.modifications.count(), 0)
        self.assertEqual(event.relationships.count(), removed)

        children = {str(c.id): c for c in children}
        for relationship in event.relationships.all():
            self.assertEqual(relationship.operation, int(Operation.DELETE))
            self.assertEqual(relationship.field.name, 'relationship')
            self.assertIn(relationship.entry.primary_key, children)

    def test_clear(self):
        """ test if clearing all elements works correctly """

        samples = 10
        children = self.generate_children(samples)

        m2m = M2MTest()
        m2m.save()
        m2m.relationship.add(*children)
        m2m.save()
        ModelEvent.objects.all().delete()

        m2m.relationship.clear()
        m2m.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertEqual(event.modifications.count(), 0)
        self.assertEqual(event.relationships.count(), samples)

        children = {str(c.id): c for c in children}
        for relationship in event.relationships.all():
            self.assertEqual(relationship.operation, int(Operation.DELETE))
            self.assertEqual(relationship.field.name, 'relationship')
            self.assertIn(relationship.entry.primary_key, children)

    def test_one2one(self):
        """
        test if OneToOne are correctly recognized,
        should be handled by save.py
        """

        o2o = OneToOneTest()
        o2o.save()

        subject = OrdinaryTest(random=random_string())
        subject.save()
        ModelEvent.objects.all().delete()

        o2o.relationship = subject
        o2o.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]

        self.assertEqual(event.modifications.count(), 1)
        self.assertEqual(event.relationships.count(), 0)

        modification = event.modifications.all()[0]
        self.assertEqual(modification.field.name, 'relationship_id')
        self.assertEqual(modification.current, repr(subject.pk))

    def test_foreign(self):
        """
        test if ForeignKey are correctly recognized.

        should be handled by save.py
        """

        fk = ForeignKeyTest()
        fk.save()

        subject = OrdinaryTest(random=random_string())
        subject.save()

        ModelEvent.objects.all().delete()

        fk.relationship = subject
        fk.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]

        self.assertEqual(event.modifications.count(), 1)
        self.assertEqual(event.relationships.count(), 0)

        modification = event.modifications.all()[0]
        self.assertEqual(modification.field.name, 'relationship_id')
        self.assertEqual(modification.current, repr(subject.pk))

    # def test_no_change(self):
    #     samples = 10
    #     children = self.generate_children(samples)
    #
    #     subject = OrdinaryTest(random=random_string())
    #     subject.save()
    #
    #     m2m = M2MTest()
    #     m2m.save()
    #     m2m.relationship.add(*children)
    #     m2m.save()
    #     ModelEvent.objects.all().delete()
    #
    #     m2m.relationship.remove(subject)
    #     m2m.save()
    #
    #     events = ModelEvent.objects.all()
    #     # TODO: fails
    #     # self.assertEqual(events.count(), 0)

    def test_find(self):
        m2m = M2MTest()
        m2m.save()

        self.assertIsNotNone(find_m2m_rel(m2m.relationship.through, M2MTest))
        self.assertIsNone(find_m2m_rel(m2m.relationship.through, OrdinaryTest))

    def test_reverse(self):
        m2m = M2MTest()
        m2m.save()

        subject = OrdinaryTest(random=random_string())
        subject.save()

        ModelEvent.objects.all().delete()

        subject.m2mtest_set.add(m2m)
        subject.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]

        self.assertEqual(event.modifications.count(), 0)
        self.assertEqual(event.relationships.count(), 1)
        self.assertEqual(event.entry.mirror.name, 'M2MTest')

        relationship = event.relationships.all()[0]
        self.assertEqual(relationship.operation, int(Operation.CREATE))
        self.assertEqual(relationship.field.name, 'relationship')
        self.assertEqual(relationship.entry.primary_key, str(subject.id))


# TODO: test lazy_model_exclusion
