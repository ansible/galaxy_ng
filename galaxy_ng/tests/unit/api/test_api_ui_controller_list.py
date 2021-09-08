from django.conf import settings

from .base import BaseTestCase, get_current_ui_url


class TestUiFeatureFlagsView(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.original_setting = settings.GALAXY_FEATURE_FLAGS
        settings.CONNECTED_ANSIBLE_CONTROLLERS = [
            "https://my-controller1.example.com/",
            "https://controllerino.contotrolisimo.com/",
            "https://boring-url.example.com/",
        ]

    def tearDown(self):
        super().tearDown()
        settings.CONNECTED_ANSIBLE_CONTROLLERS = self.original_setting

    def test_feature_flags_url(self):
        self.feature_flags_url = get_current_ui_url('controllers')

        controller_list = self.client.get(self.feature_flags_url).data['data']
        self.assertEqual(len(controller_list), len(settings.CONNECTED_ANSIBLE_CONTROLLERS))
        for controller in controller_list:
            self.assertTrue(controller['host'] in settings.CONNECTED_ANSIBLE_CONTROLLERS)

        controller_list = self.client.get(self.feature_flags_url + "?limit=1").data['data']
        self.assertEqual(len(controller_list), 1)

        controller_list = self.client.get(
            self.feature_flags_url + "?host__icontains=EXAMPLE.COM").data['data']
        self.assertEqual(len(controller_list), 2)
        for controller in controller_list:
            self.assertTrue('example.com' in controller['host'])

        controller_list = self.client.get(
            self.feature_flags_url + "?host=https://boring-url.example.com/").data['data']
        self.assertEqual(len(controller_list), 1)
        self.assertEqual(controller_list[0]["host"], "https://boring-url.example.com/")
