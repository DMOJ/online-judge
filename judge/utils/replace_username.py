import re

import judge.models.profile

USERNAME_MENTION_RE = re.compile(r'\[(r?user):([\w-]+)\]')


def replace_username_with_id(body_text):
    username_matches = [match[1] for match in USERNAME_MENTION_RE.findall(body_text)]
    username_to_id = dict(judge.models.profile.Profile.objects.filter(
        user__username__in=username_matches).
        values_list('user__username', 'snowflake_id'),
    )

    def replacement(match):
        username = match.group(2)
        user_id = username_to_id.get(username)
        if user_id is not None:
            return '[user:%s]' % (user_id)
        return match.group(0)
    return USERNAME_MENTION_RE.sub(replacement, body_text)
