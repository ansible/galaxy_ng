from django.urls.base import reverse

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand
from rest_framework.test import APIClient
from rest_framework import status as http_code

User = get_user_model()


class Command(BaseCommand):
    """
    Django management command for creating groups
    """

    help = 'Verify that the app has initialized successfully.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--user',
            default=None,
            help='Specify a username to perform tests with.'
        )

    repos_to_verify = [
        'published',
        'staging',
        'rejected',
        'community',
        'rh-certified'
    ]

    def handle(self, *args, **options):
        user = None
        if options['user']:
            user = User.objects.get(username=options['user'])
        else:
            user = User.objects.first()

        print(f'Authenticating with: {user.username}')

        client = APIClient()
        client.force_authenticate(user=user)
        for repo in self.repos_to_verify:
            url = reverse(
                'galaxy:api:content:v3:collections-list',
                kwargs={
                    'path': repo,
                }
            )
            response = client.get(url)
            if response.status_code != http_code.HTTP_200_OK:
                print(f'Failure: {url} returned status {response.status_code}.')
                exit(1)

        print('Healthcheck passed.')
