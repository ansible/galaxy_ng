import logging

from galaxy_ng.app.constants import DeploymentMode
from galaxy_ng.app.models import auth as auth_models

from .base import BaseTestCase, get_current_ui_url

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


class TestLocalization(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.group_url = get_current_ui_url('groups')
        self.admin_user = auth_models.User.objects.create(username='admin',
                                                          is_superuser=True)
        self.group = auth_models.Group.objects.create(name='test_group')
        self.user.groups.add(self.group)
        self.admin_user.save()

    def _switch_lang_post(self, language):
        response = self.client.post(
            self.group_url,
            {"name": "test_group"},
            HTTP_ACCEPT_LANGUAGE=language
        )
        return response.data['errors'][0]['detail']

    def _switch_lang_get(self, language):
        response = self.client.get(
            self.group_url + 'notfoundgroup/',
            HTTP_ACCEPT_LANGUAGE=language
        )
        return response.data['errors'][0]['title']

    def test_auto_localization(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            self.client.force_authenticate(user=self.admin_user)

            response = self.client.get(
                self.group_url + 'notfoundgroup/'
            )
            self.assertEqual(
                response.data['errors'][0]['title'],
                'Not found.'
            )

            response = self._switch_lang_get('es')
            self.assertEqual(
                response,
                'No encontrado.'
            )

            response = self._switch_lang_get('fr')
            self.assertEqual(
                response,
                'Pas trouvé.'
            )

            response = self._switch_lang_get('nl')
            self.assertEqual(
                response,
                'Niet gevonden.'
            )

            response = self._switch_lang_get('ja')
            self.assertEqual(
                response,
                '見つかりませんでした。'
            )

            response = self._switch_lang_get('zh')
            self.assertEqual(
                response,
                '未找到。'
            )

            response = self._switch_lang_get('cs')
            self.assertEqual(
                response,
                'Not found.'
            )

    def test_localization_files(self):
        with self.settings(GALAXY_DEPLOYMENT_MODE=DeploymentMode.STANDALONE.value):
            self.client.force_authenticate(user=self.admin_user)

            response = self.client.post(
                self.group_url,
                {"name": "test_group"}
            )
            self.assertEqual(
                response.data['errors'][0]['detail'],
                'A group named test_group already exists.'
            )

            response = self._switch_lang_post('fr')
            self.assertEqual(
                response,
                'Un groupe nommé test_group existe déjà.'
            )

            response = self._switch_lang_post('es')
            self.assertEqual(
                response,
                'Ya existe un grupo llamado test_group.'
            )

            response = self._switch_lang_post('nl')
            self.assertEqual(
                response,
                'Een groep met de naam test_group bestaat al.'
            )

            response = self._switch_lang_post('ja')
            self.assertEqual(
                response,
                'test_group という名前のグループはすでに存在します。'
            )

            response = self._switch_lang_post('zh')
            self.assertEqual(
                response,
                '名为 test_group 的组已存在。'
            )

            response = self._switch_lang_post('cs')
            self.assertEqual(
                response,
                'A group named test_group already exists.'
            )
