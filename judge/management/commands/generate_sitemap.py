import sys
from pathlib import Path
from urllib.parse import urljoin

from django.contrib.sites.models import Site
from django.core.management import BaseCommand
from django.template.loader import get_template

from judge.sitemap import sitemaps


class Command(BaseCommand):
    requires_system_checks = False

    def add_arguments(self, parser):
        parser.add_argument('directory', help='directory to generate the sitemap in')
        parser.add_argument('-s', '--site', type=int, help='ID of the site to generate the sitemap for')
        parser.add_argument('-p', '--protocol', default='https', help='protocol to use for links')
        parser.add_argument('-d', '--subdir', '--subdirectory', default='sitemaps',
                            help='subdirectory for individual sitemap files')
        parser.add_argument('-P', '--prefix', help='URL prefix for individual sitemaps')

    def handle(self, *args, **options):
        directory = Path(options['directory'])
        protocol = options['protocol']
        subdirectory = options['subdir']
        verbose = options['verbosity'] > 1

        try:
            site = Site.objects.get(id=options['site']) if options['site'] else Site.objects.get_current()
        except Site.DoesNotExist:
            self.stderr.write('Pass a valid site ID for -s/--site.')
            sys.exit(1)

        if site is None:
            self.stderr.write('Pass -s/--site to set a site ID.')
            sys.exit(1)

        prefix = options['prefix'] or f'{protocol}://{site.domain}/{subdirectory}/'
        if not prefix.endswith('/'):
            self.stderr.write('-P/--prefix needs to end with a / or bad things will happen.')
            sys.exit(1)

        maps = []
        maps_dir = directory / subdirectory
        maps_dir.mkdir(parents=True, exist_ok=True)

        map_template = get_template('sitemap.xml')
        index_template = get_template('sitemap_index.xml')

        for name, sitemap in sitemaps.items():
            if callable(sitemap):
                sitemap = sitemap()

            for page in range(1, sitemap.paginator.num_pages + 1):
                file = f'sitemap-{name}-{page}.xml'
                if verbose:
                    self.stdout.write(f'Rendering sitemap {file}...\n')

                urls = sitemap.get_urls(page=page, site=site, protocol=protocol)
                with open(maps_dir / file, 'w', encoding='utf-8') as f:
                    f.write(map_template.render({'urlset': urls}))
                maps.append(file)

        if verbose:
            self.stdout.write('Rendering sitemap index file...')

        with open(directory / 'sitemap.xml', 'w', encoding='utf-8') as f:
            f.write(index_template.render({'sitemaps': [urljoin(prefix, file) for file in maps]}))
