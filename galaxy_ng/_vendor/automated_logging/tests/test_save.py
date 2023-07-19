""" Test the save functionality """
import datetime

from django.http import JsonResponse

from automated_logging.helpers import Operation
from automated_logging.models import ModelEvent
from automated_logging.tests.base import BaseTestCase, USER_CREDENTIALS
from automated_logging.tests.helpers import random_string
from automated_logging.tests.models import OrdinaryTest


class LoggedOutSaveModificationsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        # delete all previous model events
        ModelEvent.objects.all().delete()

    def test_create_simple_value(self):
        """
        test if creation results in the correct fields
        :return:
        """
        self.bypass_request_restrictions()
        value = random_string()

        instance = OrdinaryTest()
        instance.random = value
        instance.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]

        self.assertEqual(event.operation, int(Operation.CREATE))
        self.assertEqual(event.user, None)

        self.assertEqual(event.entry.primary_key, str(instance.pk))
        self.assertEqual(event.entry.value, repr(instance))

        self.assertEqual(event.entry.mirror.name, 'OrdinaryTest')
        self.assertEqual(event.entry.mirror.application.name, 'automated_logging')

        modifications = event.modifications.all()
        # pk and random added and modified
        self.assertEqual(modifications.count(), 2)
        self.assertEqual({m.field.name for m in modifications}, {'random', 'id'})

        modification = [m for m in modifications if m.field.name == 'random'][0]
        self.assertEqual(modification.operation, int(Operation.CREATE))
        self.assertEqual(modification.previous, None)
        self.assertEqual(modification.current, value)
        self.assertEqual(modification.event, event)

        self.assertEqual(modification.field.name, 'random')
        self.assertEqual(modification.field.type, 'CharField')

        relationships = event.relationships.all()
        self.assertEqual(relationships.count(), 0)

    def test_modify(self):
        """
        test if modification results
        in proper delete and create field operations
        :return:
        """
        previous, current = random_string(10), random_string(10)

        # create instance
        instance = OrdinaryTest()
        instance.random = previous
        instance.save()

        # delete all stuff related to the instance events to have a clean slate
        ModelEvent.objects.all().delete()

        instance.random = current
        instance.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]

        self.assertEqual(event.user, None)
        self.assertEqual(event.operation, int(Operation.MODIFY))

        modifications = event.modifications.all()
        self.assertEqual(modifications.count(), 1)

        modification = modifications[0]
        self.assertEqual(modification.operation, int(Operation.MODIFY))
        self.assertEqual(modification.previous, previous)
        self.assertEqual(modification.current, current)

        relationships = event.relationships.all()
        self.assertEqual(relationships.count(), 0)

    def test_honor_save(self):
        """
        test if saving honors the only attribute

        :return:
        """
        previous1, random1, random2 = (
            random_string(10),
            random_string(10),
            random_string(10),
        )

        # create instance
        instance = OrdinaryTest()
        instance.random = previous1
        instance.save()

        ModelEvent.objects.all().delete()

        instance.random = random1
        instance.random2 = random2
        instance.save(update_fields=['random2'])

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        modifications = event.modifications.all()
        self.assertEqual(modifications.count(), 1)

        modification = modifications[0]
        self.assertEqual(modification.operation, int(Operation.CREATE))
        self.assertEqual(modification.field.name, 'random2')

    def test_delete(self):
        """
        test if deletion is working correctly and records all the changes
        :return:
        """
        value = random_string(10)

        # create instance
        instance = OrdinaryTest()
        instance.random = value
        instance.save()

        pk = instance.pk
        re = repr(instance)

        ModelEvent.objects.all().delete()

        instance.delete()

        # DUP of save
        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertEqual(event.operation, int(Operation.DELETE))
        self.assertEqual(event.user, None)

        self.assertEqual(event.entry.primary_key, str(pk))
        self.assertEqual(event.entry.value, re)

        # DELETE does currently not record deleted values
        modifications = event.modifications.all()
        self.assertEqual(modifications.count(), 0)

    def test_reproducibility(self):
        """
        test if all the changes where done
        correctly so that you can properly derive the
        current state from all the accumulated changes

        TODO
        """
        pass

    def test_performance(self):
        """
        test if setting the performance parameter works correctly

        :return:
        """
        from django.conf import settings
        from automated_logging.settings import settings as conf

        self.bypass_request_restrictions()

        settings.AUTOMATED_LOGGING['model']['performance'] = True
        conf.load.cache_clear()

        ModelEvent.objects.all().delete()
        instance = OrdinaryTest()
        instance.random = random_string(10)
        checkpoint = datetime.datetime.now()
        instance.save()
        checkpoint = datetime.datetime.now() - checkpoint

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertIsNotNone(event.performance)
        self.assertLess(event.performance.total_seconds(), checkpoint.total_seconds())

    def test_snapshot(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        self.bypass_request_restrictions()

        settings.AUTOMATED_LOGGING['model']['snapshot'] = True
        conf.load.cache_clear()

        instance = OrdinaryTest(random=random_string())
        instance.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertIsNotNone(event.snapshot)
        self.assertEqual(instance, event.snapshot)


class LoggedInSaveModificationsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.client.login(**USER_CREDENTIALS)

        self.clear()

    @staticmethod
    def view(request):
        value = random_string()

        instance = OrdinaryTest()
        instance.random = value
        instance.save()

        return JsonResponse({})

    def test_user(self):
        """ Test if DAL recognizes the user through the middleware """
        self.bypass_request_restrictions()

        response = self.request('GET', self.view)
        self.assertEqual(response.content, b'{}')

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertEqual(event.user, self.user)


# TODO: test snapshot
