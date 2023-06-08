import logging

from pulp_ansible.app.models import CollectionRemote

from .base import BaseTestCase

log = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


class TestCollectionRemotes(BaseTestCase):

    def setUp(self):
        super().setUp()

    def test_default_ansible_collectionremotes_have_correct_pulp_type(self):
        """
        Remotes must have the correct pulp type or pulpcore >3.24 will explode
        on stack spinup.
        """
        for cremote in CollectionRemote.objects.all():
            assert cremote.pulp_type == 'ansible.collection'
