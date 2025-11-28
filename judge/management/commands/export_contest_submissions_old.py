"""
Management command to export all in‑contest submissions for a DMOJ
contest into a single ZIP archive.

This command iterates through every `ContestSubmission` associated
with the specified contest and writes each submission's source code
into a hierarchical archive grouped by username.  The resulting ZIP
contains files named ``<username>/<problem_code>-<submission_id>.txt``
containing the exact text of the submission.  Use this to collect
student solutions for grading or archival purposes.

By default, only non‑disqualified and live participations are
included.  You can override this behaviour with ``--include-disqualified``
and ``--include-virtual`` flags.

Important details from the DMOJ codebase:

* In the `Submission` model, the field ``contest_object`` links a
  submission back to the contest it was made in【730176819382120†L101-L104】.  The
  `ContestSubmission` model further connects the submission to the
  corresponding `ContestProblem` and `ContestParticipation`【187889208654152†L802-L814】.
* The actual source code lives in the `SubmissionSource` model as
  ``submission.source.source``【730176819382120†L291-L297】.  Retrieving this field
  yields the full program text.

Place this file in your project's ``judge/management/commands`` directory and
run it via ``manage.py`` like so:

    python manage.py export_contest_submissions <contest_key> <output_zip>
        [--include-disqualified] [--include-virtual]

The command will report how many submissions were archived and
create the specified ZIP file on disk.
"""

import os
import zipfile
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from judge.models.contest import (
    Contest,
    ContestSubmission,
    ContestParticipation,
)


class Command(BaseCommand):
    help = (
        "Export the source code of all submissions in a contest into a ZIP archive. "
        "Only live, non‑disqualified participations are exported by default."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "contest_key",
            type=str,
            help="Contest key (the short slug identifying the contest)",
        )
        parser.add_argument(
            "archive_path",
            type=str,
            help="Path of the output ZIP archive to create",
        )
        parser.add_argument(
            "--include-disqualified",
            action="store_true",
            help="Include submissions from disqualified participations",
        )
        parser.add_argument(
            "--include-virtual",
            action="store_true",
            help="Include submissions from virtual/spectate participations",
        )

    def handle(self, *args, **opts):
        contest_key: str = opts["contest_key"]
        archive_path = Path(opts["archive_path"]).expanduser().resolve()
        include_disqualified: bool = opts["include_disqualified"]
        include_virtual: bool = opts["include_virtual"]

        # Look up the contest.
        try:
            contest = Contest.objects.get(key=contest_key)
        except Contest.DoesNotExist:
            raise CommandError(f"Contest with key '{contest_key}' does not exist.")

        # Build a queryset of contest submissions for this contest.
        qs = ContestSubmission.objects.filter(problem__contest=contest)

        # Filter out disqualified/virtual participations unless requested.
        if not include_disqualified:
            qs = qs.filter(participation__is_disqualified=False)
        if not include_virtual:
            qs = qs.filter(participation__virtual=ContestParticipation.LIVE)

        # Optimise database access by selecting related objects in one query.
        qs = qs.select_related(
            "submission",
            "submission__source",
            "submission__user__user",
            "problem__problem",
            "participation__user__user",
        ).order_by("participation__user__user__username", "submission__id")

        # Ensure the parent directory exists.
        archive_path.parent.mkdir(parents=True, exist_ok=True)

        count = 0
        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for cs in qs:
                submission = cs.submission
                # Resolve associated user and problem.
                profile = submission.user  # judge.Profile
                user_obj = profile.user  # django.contrib.auth.models.User
                username = user_obj.username or "anonymous"
                problem_code = cs.problem.problem.code
                submission_id = submission.id

                # Try to get the source code.  Some submissions (e.g. interactive
                # judges) may not have a source; skip these gracefully.
                try:
                    source_text = submission.source.source
                except Exception:
                    # If the source cannot be accessed, skip and warn.
                    self.stderr.write(
                        self.style.WARNING(
                            f"Submission {submission_id} by {username} has no source; skipping."
                        )
                    )
                    continue

                # Compose the archive member name.  Use .txt extension; if you
                # prefer language extensions, you may derive it from
                # submission.language.extension, but that is optional.
                member_name = f"{username}/{problem_code}-{submission_id}.java"

                # Write into the archive.
                zf.writestr(member_name, source_text)
                count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Exported {count} submissions to archive {archive_path}"
            )
        )