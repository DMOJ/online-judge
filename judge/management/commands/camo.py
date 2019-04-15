from django.core.management.base import BaseCommand, CommandError

from judge.utils.camo import client as camo_client


class Command(BaseCommand):
    help = 'obtains the camo url for the specified url'

    def add_arguments(self, parser):
        parser.add_argument('url', help='url to use camo on')

    def handle(self, *args, **options):
        if camo_client is None:
            raise CommandError('Camo not available')

        print(camo_client.image_url(options['url']))
