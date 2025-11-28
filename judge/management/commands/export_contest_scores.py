"""
Management command to export DMOJ contest scores to a CSV file.

This command queries all participations for a given contest and writes a
simple CSV containing each participant’s first and last name along with
their final score.  Scores are taken from the ``ContestParticipation.score``
field, which is populated by the contest format’s ``update_participation``
method.  For the default contest format, this method sums the highest
points achieved for each problem and rounds to the contest’s
configured precision【858124253306306†L24-L45】.  The ``score`` field is defined on
``ContestParticipation`` and stored alongside the participation record【187889208654152†L660-L683】.

Key features:

* Excludes disqualified and virtual/spectator participations by default,
  mirroring the public scoreboard.  Flags are provided to include
  disqualified or virtual entries if desired.
* Accepts the contest key (slug) and output path as required positional
  arguments.
* Writes a header row followed by ``first_name,last_name,score`` for each
  participant.  Names are pulled from the ``auth.User`` model attached to
  each profile.

Usage:

```
python manage.py export_contest_scores <contest_key> <output_csv> [--include-disqualified] [--include-virtual]
```

To install this command, place this file inside your site project’s
``judge/management/commands`` directory.  You can then invoke it via
``manage.py`` like any other Django management command.
"""

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from judge.models.contest import Contest, ContestParticipation


class Command(BaseCommand):
    help = (
        "Export contest participant scores to a CSV file. "
        "By default only live, non‑disqualified participations are exported."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "contest_key",
            type=str,
            help="Contest key (the short slug used in URLs).",
        )
        parser.add_argument(
            "csv_path",
            type=str,
            help="Path to write the resulting CSV file.",
        )
        parser.add_argument(
            "--include-disqualified",
            action="store_true",
            help="Include disqualified participations in the export.",
        )
        parser.add_argument(
            "--include-virtual",
            action="store_true",
            help="Include virtual and spectate participations in the export.",
        )

    def handle(self, *args, **opts):
        contest_key = opts["contest_key"]
        csv_path = Path(opts["csv_path"]).expanduser().resolve()
        include_disqualified = opts["include_disqualified"]
        include_virtual = opts["include_virtual"]

        try:
            contest = Contest.objects.get(key=contest_key)
        except Contest.DoesNotExist:
            raise CommandError(f"Contest with key '{contest_key}' does not exist.")

        # Build a queryset of participations.  We avoid N+1 queries on names by
        # selecting the related Profile and the underlying auth.User.
        qs = ContestParticipation.objects.filter(contest=contest)
        if not include_disqualified:
            qs = qs.filter(is_disqualified=False)
        if not include_virtual:
            qs = qs.filter(virtual=ContestParticipation.LIVE)

        qs = qs.select_related("user__user").order_by("-score", "cumtime", "user__user__username")

        # Open CSV for writing.  Use utf‑8 and newline='' to avoid blank lines.
        count = 0
        with csv_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["NetID", "first_name", "last_name", "score"])
            for participation in qs:
                # The auth.User instance is accessible via participation.user.user
                user = participation.user.user
                netid = user.username or ""
                first_name = user.first_name or ""
                last_name = user.last_name or ""
                score = participation.score
                writer.writerow([netid, first_name, last_name, score])
                count += 1

        self.stdout.write(self.style.SUCCESS(f"Exported {count} participations to {csv_path}"))
