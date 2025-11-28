"""
Management command to export all in-contest submissions for a DMOJ contest
into a ZIP archive, with an option to keep only the latest submission
per (user, problem).

Usage:
    python manage.py export_contest_submissions <contest_key> output.zip
        [--include-disqualified] [--include-virtual] [--latest-only]

Details:
- Submissions are gathered via judge.models.contest.ContestSubmission which links
  (Submission, ContestProblem, ContestParticipation):contentReference[oaicite:0]{index=0}.
- Source code comes from judge.models.submission.SubmissionSource.source:contentReference[oaicite:1]{index=1}.
- Files are written as: <username>/<problem_code>-<submission_id>.txt
"""

import io
import zipfile
from pathlib import Path
from typing import Dict, Tuple, Set

from django.core.management.base import BaseCommand, CommandError
from django.db.models import Prefetch

from judge.models.contest import Contest, ContestParticipation, ContestSubmission
from judge.models.submission import Submission, SubmissionSource


class Command(BaseCommand):
    help = (
        "Export contest submissions into a ZIP archive. By default includes all "
        "in-contest submissions from live, non-disqualified participations. "
        "Use --latest-only to keep only the most recent submission per user+problem."
    )

    def add_arguments(self, parser):
        parser.add_argument("contest_key", type=str, help="Contest key (slug).")
        parser.add_argument("zip_path", type=str, help="Output ZIP path.")
        parser.add_argument(
            "--include-disqualified",
            action="store_true",
            help="Include disqualified participations.",
        )
        parser.add_argument(
            "--include-virtual",
            action="store_true",
            help="Include virtual/spectator participations.",
        )
        parser.add_argument(
            "--latest-only",
            action="store_true",
            help="Export only the latest submission per (user, problem).",
        )

    def handle(self, *args, **opts):
        contest_key = opts["contest_key"]
        zip_path = Path(opts["zip_path"]).expanduser().resolve()
        include_disqualified = opts["include_disqualified"]
        include_virtual = opts["include_virtual"]
        latest_only = opts["latest_only"]

        # 1) Load contest
        try:
            contest = Contest.objects.get(key=contest_key)
        except Contest.DoesNotExist:
            raise CommandError(f"Contest with key '{contest_key}' does not exist.")

        # 2) Base queryset: contest submissions
        qs = ContestSubmission.objects.filter(participation__contest=contest)

        # Apply participation filters to mirror scoreboard defaults
        if not include_disqualified:
            qs = qs.filter(participation__is_disqualified=False)
        if not include_virtual:
            qs = qs.filter(participation__virtual=ContestParticipation.LIVE)

        # Avoid N+1: pull username, problem code, and source
        qs = qs.select_related(
            "participation__user__user",   # -> auth.User for names/usernames
            "submission__user__user",      # redundant but safe
            "submission__problem",         # problem.code
            "problem__problem",            # contest problem -> problem
            "submission__language",        # optional if you want to use lang
        ).prefetch_related(
            Prefetch("submission__source", queryset=SubmissionSource.objects.all())
        )

        # 3) If exporting only latest per (user, problem), sort newest-first and keep first seen.
        #    Otherwise, export all (just sort by username, problem, then submission id).
        if latest_only:
            qs = qs.order_by(
                "submission__user_id",
                "submission__problem_id",
                "-submission__date",
                "-submission__id",
            )
        else:
            qs = qs.order_by(
                "submission__user__user__username",
                "submission__problem__code",
                "submission__id",
            )

        written = 0
        skipped_no_source = 0
        seen_pairs: Set[Tuple[int, int]] = set()  # (user_id, problem_id)

        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for cs in qs.iterator():
                sub: Submission = cs.submission
                prof_user = sub.user.user
                username = prof_user.username or f"user{prof_user.id}"
                problem_code = (sub.problem.code
                                or cs.problem.problem.code
                                or f"prob{cs.problem_id}")

                # latest-only: keep newest per (user, problem)
                if latest_only:
                    key = (sub.user_id, sub.problem_id)
                    if key in seen_pairs:
                        continue
                    seen_pairs.add(key)

                # pull source (may be missing depending on visibility or data)
                try:
                    source_obj = sub.source
                except SubmissionSource.DoesNotExist:
                    source_obj = None
                if not source_obj or not source_obj.source:
                    skipped_no_source += 1
                    continue

                # Build archive path: username/problem-subid.txt
                fname = f"{username}/{problem_code}-{sub.id}.txt"
                data = source_obj.source

                # Write as UTF-8 text file
                zf.writestr(fname, data)
                written += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Created '{zip_path}': wrote {written} file(s)"
                + (f", skipped {skipped_no_source} lacking source." if skipped_no_source else ".")
            )
        )

