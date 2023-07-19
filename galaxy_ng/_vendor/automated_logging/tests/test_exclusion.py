import logging
import threading
from pathlib import Path

from django.contrib import admin
from django.http import JsonResponse

from automated_logging.decorators import (
    include_model,
    exclude_view,
    include_view,
    exclude_model,
)
from automated_logging.helpers import Operation
from automated_logging.middleware import AutomatedLoggingMiddleware
from automated_logging.models import (
    ModelEvent,
    RequestEvent,
    UnspecifiedEvent,
    Application,
)
from automated_logging.signals import (
    cached_model_exclusion,
    model_exclusion,
    request_exclusion,
)
from automated_logging.tests.models import (
    OrdinaryTest,
    OneToOneTest,
    FullClassBasedExclusionTest,
    PartialClassBasedExclusionTest,
    FullDecoratorBasedExclusionTest,
    PartialDecoratorBasedExclusionTest,
    DecoratorOverrideExclusionTest,
    M2MTest,
)
from automated_logging.tests.base import BaseTestCase, USER_CREDENTIALS, clear_cache
from automated_logging.tests.helpers import random_string


class ConfigurationBasedExclusionsTestCase(BaseTestCase):
    def setUp(self):
        super().setUp()

        self.client.login(**USER_CREDENTIALS)

    @staticmethod
    def view(request):
        return JsonResponse({})

    def test_globals(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        self.clear()

        settings.AUTOMATED_LOGGING['unspecified']['exclude']['applications'] = []
        settings.AUTOMATED_LOGGING['model']['exclude']['applications'] = []
        settings.AUTOMATED_LOGGING['request']['exclude']['applications'] = []
        settings.AUTOMATED_LOGGING['globals']['exclude']['applications'] = [
            'automated*'
        ]

        conf.load.cache_clear()

        OrdinaryTest(random=random_string()).save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        self.request('GET', self.view)
        self.assertEqual(RequestEvent.objects.count(), 0)

        logger = logging.getLogger(__name__)
        logger.info('[TEST]')
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

    def test_applications(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        self.clear()

        settings.AUTOMATED_LOGGING['globals']['exclude']['applications'] = []
        conf.load.cache_clear()

        logger = logging.getLogger(__name__)
        logger.info('[TEST]')
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)
        self.clear()

        settings.AUTOMATED_LOGGING['unspecified']['exclude']['applications'] = [
            'automated*'
        ]
        conf.load.cache_clear()

        logger = logging.getLogger(__name__)
        logger.info('[TEST]')
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['model']['exclude']['applications'] = ['automated*']
        conf.load.cache_clear()

        OrdinaryTest(random=random_string()).save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['request']['exclude']['applications'] = [
            'automated*'
        ]
        conf.load.cache_clear()

        self.request('GET', self.view)
        self.assertEqual(RequestEvent.objects.count(), 0)

    def test_fields(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        subject = OrdinaryTest()
        subject.save()

        self.clear()
        settings.AUTOMATED_LOGGING['model']['exclude']['fields'] = [
            'automated_logging.OrdinaryTest.random'
        ]
        conf.load.cache_clear()

        subject.random = random_string()
        subject.save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['model']['exclude']['fields'] = [
            'OrdinaryTest.random'
        ]
        conf.load.cache_clear()

        subject.random = random_string()
        subject.save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['model']['exclude']['fields'] = ['random']
        conf.load.cache_clear()
        subject.random = random_string()
        subject.save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        subject.random = random_string()
        subject.random2 = random_string()
        subject.save()
        self.assertEqual(ModelEvent.objects.count(), 1)
        self.assertEqual(ModelEvent.objects.all()[0].modifications.count(), 1)

    def test_models(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        self.clear()

        settings.AUTOMATED_LOGGING['model']['exclude']['models'] = [
            'automated_logging.tests.models.OrdinaryTest'
        ]
        conf.load.cache_clear()

        OrdinaryTest(random=random_string()).save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['model']['exclude']['models'] = [
            'automated_logging.OrdinaryTest'
        ]
        conf.load.cache_clear()

        OrdinaryTest(random=random_string()).save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['model']['exclude']['models'] = ['OrdinaryTest']
        conf.load.cache_clear()

        OrdinaryTest(random=random_string()).save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        OneToOneTest().save()
        self.assertEqual(ModelEvent.objects.count(), 1)
        self.assertEqual(ModelEvent.objects.all()[0].modifications.count(), 1)

    @staticmethod
    def redirect_view(request):
        return JsonResponse({}, status=301)

    def test_status(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['request']['exclude']['methods'] = []
        settings.AUTOMATED_LOGGING['request']['exclude']['status'] = [200]
        conf.load.cache_clear()

        self.clear()

        self.request('GET', self.view)
        self.assertEqual(RequestEvent.objects.count(), 0)

        self.request('GET', self.redirect_view)
        self.assertEqual(RequestEvent.objects.count(), 1)

    def test_method(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['request']['exclude']['methods'] = ['GET']
        settings.AUTOMATED_LOGGING['request']['exclude']['status'] = []
        conf.load.cache_clear()

        self.clear()

        self.request('GET', self.view)
        self.assertEqual(RequestEvent.objects.count(), 0)

        self.request('POST', self.view)
        self.assertEqual(RequestEvent.objects.count(), 1)

    def test_files(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        path = Path(__file__).absolute()
        project = Path(__file__).parent.parent.parent
        relative = path.relative_to(project)

        logger = logging.getLogger(__name__)
        self.clear()

        # absolute path
        settings.AUTOMATED_LOGGING['unspecified']['exclude']['files'] = [
            path.as_posix()
        ]
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

        # relative path
        settings.AUTOMATED_LOGGING['unspecified']['exclude']['files'] = [
            relative.as_posix()
        ]
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

        # file name
        settings.AUTOMATED_LOGGING['unspecified']['exclude']['files'] = [relative.name]
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

        # single directory name
        settings.AUTOMATED_LOGGING['unspecified']['exclude']['files'] = [
            'automated_logging'
        ]
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

        # absolute directory
        settings.AUTOMATED_LOGGING['unspecified']['exclude']['files'] = [
            path.parent.as_posix()
        ]
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

        # file not excluded
        settings.AUTOMATED_LOGGING['unspecified']['exclude']['files'] = ['dal']
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)

    def test_unknown(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        logger = logging.getLogger(__name__)

        default_factory = logging.getLogRecordFactory()

        def factory(*args, **kwargs):
            """
            force setting the pathname and module
            wrong so that we can pretend to exclude unknowns
            """

            record = default_factory(*args, **kwargs)

            record.pathname = '/example.py'
            record.module = 'default'
            return record

        self.clear()
        logging.setLogRecordFactory(factory=factory)

        settings.AUTOMATED_LOGGING['unspecified']['exclude']['unknown'] = True
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['unspecified']['exclude']['unknown'] = False
        conf.load.cache_clear()

        logger.info(random_string())
        self.assertEqual(UnspecifiedEvent.objects.count(), 1)

        logging.setLogRecordFactory(default_factory)

    def test_search_types(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['globals']['exclude']['applications'] = []
        settings.AUTOMATED_LOGGING['model']['exclude']['applications'] = [
            'pl:automated_logging'
        ]
        conf.load.cache_clear()
        cached_model_exclusion.cache_clear()

        self.clear()
        OrdinaryTest().save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['model']['exclude']['applications'] = [
            'gl:automated_*'
        ]
        conf.load.cache_clear()
        cached_model_exclusion.cache_clear()

        OrdinaryTest().save()
        self.assertEqual(ModelEvent.objects.count(), 0)

        settings.AUTOMATED_LOGGING['request']['exclude']['applications'] = [
            're:automated.*'
        ]
        self.bypass_request_restrictions()
        conf.load.cache_clear()
        cached_model_exclusion.cache_clear()

        self.request('GET', self.view)
        self.assertEqual(RequestEvent.objects.count(), 0)

    def test_module(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['globals']['exclude']['applications'] = []
        settings.AUTOMATED_LOGGING['model']['exclude']['models'] = [
            'automated_logging.tests.models'
        ]
        conf.load.cache_clear()
        cached_model_exclusion.cache_clear()
        self.clear()

        OrdinaryTest().save()
        self.assertEqual(ModelEvent.objects.count(), 0)

    def test_mock_sender(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        class MockModel:
            __module__ = '[TEST]'
            __name__ = 'MockModel'

        class MockMeta:
            app_label = None

        settings.AUTOMATED_LOGGING['model']['exclude']['unknown'] = True
        conf.load.cache_clear()

        self.assertTrue(model_exclusion(MockModel, MockMeta, Operation.CREATE))

        settings.AUTOMATED_LOGGING['request']['exclude']['unknown'] = True
        conf.load.cache_clear()

        self.assertTrue(
            request_exclusion(RequestEvent(application=Application(name=None)))
        )

    def test_m2m_exclusion(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['model']['exclude']['applications'] = [
            'gl:automated*'
        ]
        conf.load.cache_clear()
        cached_model_exclusion.cache_clear()

        instance = M2MTest()
        instance.save()

        children = [OrdinaryTest()]
        [c.save() for c in children]

        self.clear()

        instance.relationship.add(*children)
        instance.save()

        self.assertEqual(ModelEvent.objects.count(), 0)


class ClassBasedExclusionsTestCase(BaseTestCase):
    def test_complete(self):
        self.clear()

        FullClassBasedExclusionTest().save()
        self.assertEqual(ModelEvent.objects.count(), 0)

    def test_partial(self):
        self.clear()

        subject = PartialClassBasedExclusionTest(random=random_string())
        subject.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertEqual(event.modifications.count(), 1)
        self.assertEqual(event.modifications.all()[0].field.name, 'id')

        self.clear()

        subject.delete()
        self.assertEqual(ModelEvent.objects.count(), 0)


class DecoratorBasedExclusionsTestCase(BaseTestCase):
    def test_exclude_model(self):
        self.clear()

        # manual here as the cache clear, clears the first appliance
        FullDecoratorBasedExclusionTest.__dal_register__()
        subject = FullDecoratorBasedExclusionTest()
        subject.save()

        self.assertEqual(ModelEvent.objects.count(), 0)

        subject = PartialDecoratorBasedExclusionTest.__dal_register__()(
            random=random_string()
        )
        subject.save()

        events = ModelEvent.objects.all()
        self.assertEqual(events.count(), 1)

        event = events[0]
        self.assertEqual(event.modifications.count(), 1)

        self.clear()
        subject.delete()

        self.assertEqual(ModelEvent.objects.count(), 0)

    def test_include_model(self):
        self.clear()

        subject = DecoratorOverrideExclusionTest.__dal_register__()(
            random=random_string()
        )
        subject.save()

        self.assertEqual(ModelEvent.objects.count(), 1)

        self.clear()

        # test if overriding works
        include_model(FullClassBasedExclusionTest, operations=['delete'])()

        subject = FullClassBasedExclusionTest(random=random_string())
        subject.save()

        self.assertEqual(ModelEvent.objects.count(), 0)

        subject.delete()

        self.assertEqual(ModelEvent.objects.count(), 1)

        # just to make sure we clean up
        clear_cache()

    @staticmethod
    @exclude_view
    def complete_exclusion(request):
        return JsonResponse({})

    @staticmethod
    @exclude_view(methods=['GET'])
    def partial_exclusion(request):
        return JsonResponse({})

    def test_exclude_view(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        settings.AUTOMATED_LOGGING['request']['exclude']['methods'] = []
        settings.AUTOMATED_LOGGING['request']['exclude']['status'] = []
        conf.load.cache_clear()
        self.clear()

        self.request('GET', self.complete_exclusion)
        self.assertEqual(RequestEvent.objects.count(), 0)

        self.request('GET', self.partial_exclusion)
        self.assertEqual(RequestEvent.objects.count(), 0)
        self.request('POST', self.partial_exclusion)
        self.assertEqual(RequestEvent.objects.count(), 1)

    @staticmethod
    @include_view
    def complete_inclusion(request):
        return JsonResponse({})

    @staticmethod
    @include_view(methods=['POST'])
    def partial_inclusion(request):
        return JsonResponse({})

    def test_include_view(self):
        from django.conf import settings
        from automated_logging.settings import settings as conf

        self.clear()
        # settings default to ignoring 200/GET, include_model should still record

        self.request('GET', self.complete_inclusion)
        self.assertEqual(RequestEvent.objects.count(), 1)
        self.clear()

        settings.AUTOMATED_LOGGING['request']['exclude']['status'] = []
        settings.AUTOMATED_LOGGING['request']['exclude']['methods'] = ['GET', 'POST']
        conf.load.cache_clear()

        self.request('GET', self.partial_inclusion)
        self.assertEqual(RequestEvent.objects.count(), 0)
        self.request('POST', self.partial_inclusion)
        self.assertEqual(RequestEvent.objects.count(), 1)
        self.clear()

        settings.AUTOMATED_LOGGING['request']['exclude']['methods'] = []
        conf.load.cache_clear()

        # test if include_view has higher priority than exclude_view
        view = include_view(self.complete_exclusion, methods=['GET'])
        self.request('GET', view)
        self.assertEqual(RequestEvent.objects.count(), 1)
        self.request('POST', view)
        self.assertEqual(RequestEvent.objects.count(), 1)

        clear_cache()

    def test_partial_decorator(self):
        self.clear()
        Model = include_model(operations=['create'])(OrdinaryTest)
        Model().save()
        self.assertEqual(ModelEvent.objects.count(), 1)

    def test_layering(self):
        Model = include_model(operations=['modify'], fields=['random2'])(
            include_model(operations=['create'], fields=['random2'])(OrdinaryTest)
        )

        self.clear()
        subject = Model()
        subject.save()

        subject.random = random_string()
        subject.save()

        self.assertEqual(ModelEvent.objects.count(), 2)

        clear_cache()

        Model = exclude_model(operations=['modify'], fields=['random2'])(
            exclude_model(operations=['create'], fields=['random2'])(OrdinaryTest)
        )

        self.clear()

        subject = Model()
        subject.save()

        subject.random = random_string()
        subject.save()

        self.assertEqual(ModelEvent.objects.count(), 0)

    def test_model_fields(self):
        Model = include_model(operations=[], fields=['random'])(
            exclude_model(operations=None, fields=['random2'])(OrdinaryTest)
        )

        subject = Model()
        subject.save()

        self.clear()

        subject.random = random_string()
        subject.save()

        self.assertEqual(ModelEvent.objects.count(), 1)

        subject.random2 = random_string()
        subject.save()

        self.assertEqual(ModelEvent.objects.count(), 1)

    def test_model_admin(self):
        FullDecoratorBasedExclusionTest.__dal_register__()

        admin.site.register(FullDecoratorBasedExclusionTest)
