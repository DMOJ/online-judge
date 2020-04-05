import json
import os

from ua_parser import user_agent_parser

with open(os.path.join(os.path.dirname(__file__), '..', '..', 'resources', 'caniuse.json')) as f:
    _SUPPORT_DATA = json.loads(f.read())['data']

SUPPORT = 'y'
PARTIAL_SUPPORT = 'a'
UNSUPPORTED = 'n'
POLYFILL = 'p'
UNKNOWN = 'u'
PREFIX = 'x'
DISABLED = 'd'


def safe_int(string):
    try:
        return int(string)
    except (ValueError, TypeError):
        return 0


class BrowserFamily(object):
    def __init__(self, data):
        self._data = data
        self._ranges = ranges = []
        self._versions = versions = {}
        max_version = ()
        max_support = UNKNOWN

        for version, support in data.items():
            if version == 'all':
                self.max_support = support
            elif '-' in version:
                start, end = version.split('-')
                start = tuple(map(int, start.split('.')))
                end = tuple(map(int, end.split('.'))) + (1e3000,)
                ranges.append((start, end, support))
                if end > max_version:
                    max_version = end
                    max_support = support
            else:
                try:
                    version = tuple(map(int, version.split('.')))
                except ValueError:
                    pass
                else:
                    if version > max_version:
                        max_version = version
                        max_support = support
                versions[version] = support

        self.max_version = max_version
        self.max_support = max_support

    def check(self, major, minor, patch):
        int_major, int_minor, int_patch = map(safe_int, (major, minor, patch))

        version = (int_major, int_minor, int_patch)
        if version > self.max_version:
            return self.max_support

        for key in ((int_major, int_minor, int_patch), (int_major, int_minor), (int_major,), major):
            try:
                return self._versions[key]
            except KeyError:
                pass

        for start, end, support in self._ranges:
            if start <= version < end:
                return support

        return UNKNOWN


class Feat(object):
    def __init__(self, data):
        self._data = data
        self._family = {name: BrowserFamily(data) for name, data in data['stats'].items()}

    def __getitem__(self, item):
        return self._family[item]


class Database(object):
    def __init__(self, data):
        self._data = data
        self._feats = {feat: Feat(data) for feat, data in data.items()}

    def __getitem__(self, item):
        return self._feats[item]


database = Database(_SUPPORT_DATA)


class CanIUse(object):
    def __init__(self, ua):
        self._agent = user_agent_parser.Parse(ua)

        os_family = self._agent['os']['family']
        browser_family = self._agent['user_agent']['family']

        family = None

        if os_family == 'Android':
            if 'Firefox' in browser_family:
                family = 'and_ff'
            elif 'Chrome' in browser_family:
                family = 'and_chr'
            elif 'Android' in browser_family:
                family = 'android'
        else:
            if 'Edge' in browser_family:
                family = 'edge'
            elif 'Firefox' in browser_family:
                family = 'firefox'
            elif 'Chrome' in browser_family:
                family = 'chrome'
            elif 'IE' in browser_family:
                family = 'ie'
            elif 'Opera' in browser_family:
                family = 'opera'
            elif 'Safari' in browser_family:
                family = 'safari'

        self._family = family

    def _check_feat(self, feat):
        if not self._family:
            return UNKNOWN

        try:
            stats = feat[self._family]
        except KeyError:
            return UNKNOWN
        else:
            ua = self._agent['user_agent']
            return stats.check(ua['major'], ua['minor'], ua['patch'])[0]

    def __getattr__(self, attr):
        try:
            feat = database[attr.replace('_', '-')]
        except KeyError:
            raise AttributeError(attr)
        else:
            result = self._check_feat(feat)
            setattr(self, attr, result)
            return result
