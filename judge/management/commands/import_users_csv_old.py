# judge/management/commands/import_users_csv.py
import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, IntegrityError
from django.contrib.auth.models import User

# DMOJ models
from judge.models import Profile

class DryRunRollback(Exception):
    """Internal sentinel to trigger atomic() rollback without counting as an error."""
    pass

class Command(BaseCommand):
    help = (
        "Import users from a CSV (username,first_name,last_name,email). "
        "Default password is 123456; can be overridden. "
        "Optionally add users to a single Organization."
    )

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to the CSV file.")
        parser.add_argument(
            "--password",
            default="123456",
            help="Default password for all created users (default: 123456).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Parse and validate, but do not write anything."
        )
        parser.add_argument(
            "--update-existing",
            action="store_true",
            help="If a username already exists, update first/last/email but DO NOT change password."
        )
        parser.add_argument(
            "--activate",
            action="store_true",
            help="Force is_active=True on created/updated users."
        )

        # Organization options (choose one of slug or name)
        parser.add_argument(
            "--org-slug",
            help="Organization slug to attach all users to (preferred)."
        )
        parser.add_argument(
            "--org-name",
            help="Organization name to attach all users to (used if slug not given)."
        )
        parser.add_argument(
            "--create-org-if-missing",
            action="store_true",
            help="Create the organization if it is not found (needs --org-slug or --org-name)."
        )

    def handle(self, *args, **opts):
        csv_path = Path(opts["csv_path"]).expanduser().resolve()
        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        # Resolve the target organization once (if provided)
        org = None
        if opts.get("org_slug") or opts.get("org_name"):
            org = self._resolve_organization(
                slug=opts.get("org_slug"),
                name=opts.get("org_name"),
                create_if_missing=opts.get("create_org_if_missing")
            )
            if org is None:
                raise CommandError(
                    "Organization not found. Provide a valid --org-slug/--org-name "
                    "or use --create-org-if-missing."
                )

        rows = self._read_csv(csv_path)
        if not rows:
            self.stdout.write(self.style.WARNING("No rows found in CSV. Nothing to do."))
            return

        created, updated, skipped, org_linked = 0, 0, 0, 0
        errors = 0

        self.stdout.write(self.style.NOTICE(
            f"Importing {len(rows)} users from {csv_path} "
            f"(dry-run={opts['dry_run']}, update-existing={opts['update_existing']})"
        ))
        if org:
            self.stdout.write(self.style.NOTICE(
                f"Target organization: {getattr(org, 'slug', None) or getattr(org, 'name', None)}"
            ))

        for i, row in enumerate(rows, start=1):
            try:
                with transaction.atomic():
                    result, user = self._upsert_user(row, opts)

                    if result == "created":
                        created += 1
                    elif result == "updated":
                        updated += 1
                    elif result == "skipped":
                        skipped += 1

                    if org and user:
                        if self._add_user_to_org(user, org):
                            org_linked += 1

                    if opts["dry_run"]:
                        raise DryRunRollback()

            except DryRunRollback:
                pass
            except Exception as e:
                errors += 1
                self.stderr.write(self.style.ERROR(
                    f"[Row {i}] Error processing username='{row.get('username','')}' : {e}"
                ))

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(
            f"Done. Created: {created}, Updated: {updated}, Skipped: {skipped}, "
            f"Org-linked: {org_linked}, Errors: {errors}"
        ))

    # ---- helpers ----

    def _read_csv(self, path: Path):
        rows = []
        with path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            required = {"username", "first_name", "last_name", "email"}
            missing = required - set([h.strip() for h in (reader.fieldnames or [])])
            if missing:
                raise CommandError(f"CSV missing required headers: {', '.join(sorted(missing))}")

            for raw in reader:
                row = {k.strip(): (v or "").strip() for k, v in raw.items()}
                if not row["username"]:
                    continue
                rows.append(row)
        return rows

    def _ensure_profile(self, user: User):
        profile, _ = Profile.objects.get_or_create(user=user)
        # Optionally set a default language if your instance requires it:
        if getattr(profile, "language_id", None) is None:
            try:
                from judge.models import Language
                lang = None
                if hasattr(Language, "get_python3"):
                    lang = Language.get_python3()
                elif hasattr(Language, "get_default"):
                    lang = Language.get_default()
                elif hasattr(Language, "get_python2"):
                    lang = Language.get_python2()
                if lang is not None:
                    profile.language = lang
                    profile.save(update_fields=["language"])
            except Exception:
                pass
        return profile

    def _upsert_user(self, row, opts):
        username = row["username"]
        first_name = row.get("first_name", "")
        last_name  = row.get("last_name", "")
        email      = row.get("email", "")
        default_pw = opts["password"]

        try:
            user = User.objects.get(username=username)
            if opts["update_existing"]:
                changed = False
                if first_name and user.first_name != first_name:
                    user.first_name = first_name; changed = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name; changed = True
                if email and user.email != email:
                    user.email = email; changed = True
                if opts["activate"] and not user.is_active:
                    user.is_active = True; changed = True
                if changed:
                    user.save()
                self._ensure_profile(user)
                return "updated", user
            else:
                return "skipped", user

        except User.DoesNotExist:
            pass

        try:
            user = User.objects.create_user(
                username=username,
                email=email or "",
                password=default_pw,
            )
            user.first_name = first_name or ""
            user.last_name  = last_name or ""
            if opts["activate"]:
                user.is_active = True
            user.save()

            self._ensure_profile(user)
            self.stdout.write(self.style.SUCCESS(f"Created user '{username}'"))
            return "created", user

        except IntegrityError as e:
            raise CommandError(f"IntegrityError for '{username}': {e}")

    # ---- organization helpers ----

    def _resolve_organization(self, slug=None, name=None, create_if_missing=False):
        """
        Try to import Organization model and find by slug or name.
        If create_if_missing, attempt to create with the provided info.
        """
        try:
            from judge.models import Organization
        except Exception:
            self.stderr.write(self.style.WARNING(
                "Organization model not found in judge.models. "
                "Skipping organization linking."
            ))
            return None

        qs = Organization.objects.all()
        org = None
        if slug:
            try:
                org = qs.get(slug=slug)
            except Organization.DoesNotExist:
                org = None
        if org is None and name:
            try:
                org = qs.get(name=name)
            except Organization.DoesNotExist:
                org = None

        if org is None and create_if_missing:
            # Create with whichever identifiers provided
            create_kwargs = {}
            if name:
                create_kwargs["name"] = name
            if slug:
                create_kwargs["slug"] = slug
            # some DMOJ setups require short_name or hidden; set reasonable defaults if fields exist
            if "short_name" in [f.name for f in Organization._meta.get_fields()]:
                create_kwargs.setdefault("short_name", (slug or name or "org")[:16])
            if "hidden" in [f.name for f in Organization._meta.get_fields()]:
                create_kwargs.setdefault("hidden", False)
            org = Organization.objects.create(**create_kwargs)
            self.stdout.write(self.style.SUCCESS(
                f"Created organization '{getattr(org, 'slug', None) or getattr(org, 'name', None)}'"
            ))
        return org

    def _add_user_to_org(self, user: User, org) -> bool:
        """
        Attach user to organization, handling common DMOJ variants:

        1) Profile has FK: profile.organization = org
        2) Dedicated membership model: OrganizationMember/OrganizationMembership
        3) M2M: org.members.add(user)

        Returns True if a link was created/ensured, False otherwise.
        """
        linked = False

        # 1) Profile FK
        try:
            profile = user.profile  # via OneToOne
        except Exception:
            profile = Profile.objects.filter(user=user).first()
        if profile is not None and hasattr(profile, "organization"):
            if getattr(profile, "organization_id", None) != getattr(org, "id", None):
                profile.organization = org
                profile.save(update_fields=["organization"])
            linked = True

        # 2) Membership join model
        if not linked:
            for model_name in ("OrganizationMember", "OrganizationMembership", "OrganizationUser"):
                try:
                    from judge.models import Organization as _OrgModel  # noqa: F401 (ensure judge.models is importable)
                    MemberModel = getattr(__import__("judge.models", fromlist=[model_name]), model_name)
                except Exception:
                    MemberModel = None
                if MemberModel:
                    # Try common field names
                    possible_org_fields = [f.name for f in MemberModel._meta.get_fields()]
                    org_field = "organization" if "organization" in possible_org_fields else (
                        "org" if "org" in possible_org_fields else None
                    )
                    user_field = "user" if "user" in possible_org_fields else (
                        "profile" if "profile" in possible_org_fields else None
                    )
                    if org_field and user_field:
                        filters = {org_field: org}
                        if user_field == "user":
                            filters[user_field] = user
                        else:
                            filters[user_field] = Profile.objects.get(user=user)
                        MemberModel.objects.get_or_create(**filters)
                        linked = True
                        break  # done

        # 3) M2M from Organization to User
        if not linked:
            # org.members (User or Profile), org.users, etc.
            for attr in ("members", "users", "profiles"):
                if hasattr(org, attr):
                    rel = getattr(org, attr)
                    try:
                        # Try adding user
                        rel.add(user)
                        linked = True
                        break
                    except Exception:
                        # Try adding profile
                        try:
                            rel.add(Profile.objects.get(user=user))
                            linked = True
                            break
                        except Exception:
                            pass

        if not linked:
            self.stderr.write(self.style.WARNING(
                f"Could not determine how to link user '{user.username}' to organization; "
                "please adjust _add_user_to_org to your schema."
            ))
        return linked

