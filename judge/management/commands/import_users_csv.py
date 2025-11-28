"""
Management command to import users from a CSV file and optionally attach them
to a DMOJ organization by slug.  This command is designed to work with
the upstream DMOJ `online‑judge` repository.  It reads rows from a CSV
containing at minimum the columns `username`, `first_name`, `last_name` and
`email`, creates or updates the corresponding `auth.User` instances, ensures
each has a `judge.Profile`, and (optionally) adds the profile to a target
`Organization` by slug.

Key features:

* Update existing users’ names and emails without changing their passwords.
* Activate users if requested, since DMOJ accounts can be inactive by default.
* Dry‑run mode to parse and validate without committing changes.
* Optional creation of the target organization if it does not exist.

To install this command, place this file inside your site project’s
`judge/management/commands` directory, then run it with:

```
python manage.py import_users_csv path/to/users.csv --org-slug your‑org
```

The default password for newly created users is `123456`, but this can be
overridden with the `--password` flag.  See the argument parser below
for more flags.

This implementation relies on the actual schema of the DMOJ `Profile` model,
where membership is stored in the `organizations` many‑to‑many field and
exposed on `Organization` via the `members` reverse relation【940562129592725†L198-L207】.
"""

import csv
from pathlib import Path

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.utils import IntegrityError

from judge.models import Organization, Profile


class DryRunRollback(Exception):
    """Internal sentinel exception to trigger a rollback in dry‑run mode."""


class Command(BaseCommand):
    help = (
        'Import users from a CSV (username,first_name,last_name,email) and'
        ' optionally attach them to a single Organization by slug.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            'csv_path',
            type=str,
            help='Path to the CSV file containing user data.',
        )
        parser.add_argument(
            '--password',
            default='123456',
            help='Default password for newly created users (default: 123456).',
        )
        parser.add_argument(
            '--org-slug',
            help='Slug of the organization to add all users to.',
        )
        parser.add_argument(
            '--org-name',
            help='Name of the organization to add users to (used when creating).',
        )
        parser.add_argument(
            '--create-org-if-missing',
            action='store_true',
            help=(
                'Create the organization if it does not exist. If using this flag,'
                ' you should provide at least --org-slug and optionally --org-name.'
            ),
        )
        parser.add_argument(
            '--update-existing',
            action='store_true',
            help=(
                'If a username already exists, update the user’s first name, last name'
                ' and email. Passwords are never changed for existing users.'
            ),
        )
        parser.add_argument(
            '--activate',
            action='store_true',
            help='Force `is_active=True` on created/updated users.',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Parse and validate but do not commit any changes to the database.',
        )

    def handle(self, *args, **opts):
        csv_path = Path(opts['csv_path']).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f'CSV not found: {csv_path}')

        # Resolve (or create) the target organization once up front.
        org = None
        slug = opts.get('org_slug')
        if slug:
            org = self._resolve_organization(
                slug=slug,
                name=opts.get('org_name'),
                create_if_missing=opts.get('create_org_if_missing', False),
            )
            if org is None:
                raise CommandError(
                    'Organization not found. Provide a valid --org-slug/--org-name'
                    ' or use --create-org-if-missing.',
                )

        rows = self._read_csv(csv_path)
        if not rows:
            self.stdout.write(self.style.WARNING('No rows found in CSV. Nothing to do.'))
            return

        created = updated = skipped = errors = org_linked = 0

        self.stdout.write(
            self.style.NOTICE(
                f'Importing {len(rows)} users from {csv_path}'
                f" (dry-run={opts['dry_run']}, update-existing={opts['update_existing']})",
            ),
        )
        if org:
            self.stdout.write(
                self.style.NOTICE(
                    f'Target organization: {org.slug} ({org.name})',
                ),
            )

        for i, row in enumerate(rows, start=1):
            try:
                with transaction.atomic():
                    result, user = self._upsert_user(row, opts)
                    if result == 'created':
                        created += 1
                    elif result == 'updated':
                        updated += 1
                    elif result == 'skipped':
                        skipped += 1

                    if org and user:
                        # link user to org (no-op if already a member)
                        if self._add_user_to_org(user, org):
                            org_linked += 1

                    if opts['dry_run']:
                        # Trigger rollback for this iteration only; not counted as an error.
                        raise DryRunRollback()

            except DryRunRollback:
                pass
            except Exception as exc:
                errors += 1
                self.stderr.write(
                    self.style.ERROR(
                        f"[Row {i}] Error processing username='{row.get('username', '')}': {exc}",
                    ),
                )

        # Summary
        self.stdout.write('')
        self.stdout.write(
            self.style.SUCCESS(
                f'Done. Created: {created}, Updated: {updated}, '
                f'Skipped: {skipped}, Org-linked: {org_linked}, Errors: {errors}',
            ),
        )

    # --- helpers ---
    def _read_csv(self, path: Path):
        """Load CSV rows into a list of dictionaries and trim whitespace."""
        rows = []
        with path.open('r', newline='', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            required = {'username', 'first_name', 'last_name', 'email'}
            headers = {h.strip() for h in (reader.fieldnames or [])}
            missing = required - headers
            if missing:
                raise CommandError(
                    f"CSV missing required headers: {', '.join(sorted(missing))}",
                )
            for raw in reader:
                row = {k.strip(): (v or '').strip() for k, v in raw.items()}
                if not row.get('username'):
                    continue
                rows.append(row)
        return rows

    def _resolve_organization(self, slug: str, name: str = None, create_if_missing: bool = False):
        """
        Look up an Organization by slug.  If it does not exist and
        `create_if_missing` is true, create it using the provided slug and name.
        Otherwise return None if not found.
        """
        try:
            return Organization.objects.get(slug=slug)
        except Organization.DoesNotExist:
            if create_if_missing:
                # Provide fallbacks for fields required by the model: name and short_name.
                name = name or slug.replace('-', ' ').title()
                short_name = slug[:20]
                org = Organization.objects.create(
                    slug=slug,
                    name=name,
                    short_name=short_name,
                    about='',
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created organization '{org.slug}' ({org.name})",
                    ),
                )
                return org
            return None

    def _ensure_profile(self, user: User) -> Profile:
        """Ensure a Profile exists for the given user, creating one if necessary."""
        profile, _created = Profile.objects.get_or_create(user=user)
        return profile

    def _upsert_user(self, row: dict, opts):
        """Create or update a User based on CSV row data."""
        username = row.get('username')
        first_name = row.get('first_name', '')
        last_name = row.get('last_name', '')
        email = row.get('email', '')
        default_pw = opts.get('password')

        try:
            user = User.objects.get(username=username)
            # Optionally update existing user’s names and email
            if opts.get('update_existing'):
                updated_fields = []
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    updated_fields.append('first_name')
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    updated_fields.append('last_name')
                if email and user.email != email:
                    user.email = email
                    updated_fields.append('email')
                if opts.get('activate') and not user.is_active:
                    user.is_active = True
                    updated_fields.append('is_active')
                if updated_fields:
                    user.save(update_fields=updated_fields)
                # Ensure profile exists, even if nothing changed
                self._ensure_profile(user)
                return 'updated', user
            else:
                return 'skipped', user
        except User.DoesNotExist:
            pass

        # Create new user
        try:
            user = User.objects.create_user(
                username=username,
                email=email or '',
                password=default_pw,
            )
            # Set names after creation to avoid uniqueness issues on username
            user.first_name = first_name or ''
            user.last_name = last_name or ''
            if opts.get('activate'):
                user.is_active = True
            user.save()
            # Ensure profile exists
            self._ensure_profile(user)
            self.stdout.write(self.style.SUCCESS(f"Created user '{username}'"))
            return 'created', user
        except IntegrityError as exc:
            raise CommandError(f"IntegrityError for '{username}': {exc}")

    def _add_user_to_org(self, user: User, org: Organization) -> bool:
        """Attach the user’s profile to the given organization.  Returns True if
        a new membership link was created or ensured."""
        profile = self._ensure_profile(user)
        # Check if membership already exists
        if org.members.filter(id=profile.id).exists():
            return False
        # Add via the reverse M2M relation.  The forward relation
        # is `profile.organizations`, which would be equivalent.  We use the
        # reverse here for clarity.
        org.members.add(profile)
        return True
