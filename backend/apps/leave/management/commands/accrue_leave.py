"""Top up monthly-accruing leave balances for the current year.

Idempotent — intended to run on a schedule (e.g. a monthly Celery beat
task). For leave types using monthly accrual it recomputes ``entitled_days``
prorated to the current month; lump-sum / no-accrual types are untouched.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.leave.enums import AccrualMethod
from apps.leave.models import LeaveBalance
from apps.leave.services import _entitlement_for


class Command(BaseCommand):
    help = "Accrue monthly leave entitlement onto current-year balances."

    def add_arguments(self, parser):
        parser.add_argument(
            "--year",
            type=int,
            default=None,
            help="Year to accrue (defaults to the current year).",
        )

    def handle(self, *args, **options):
        year = options["year"] or timezone.now().year
        balances = LeaveBalance.objects.filter(
            year=year, leave_type__accrual_method=AccrualMethod.MONTHLY
        ).select_related("leave_type")

        updated = 0
        for balance in balances:
            target = _entitlement_for(balance.leave_type, year)
            if target != balance.entitled_days:
                balance.entitled_days = target
                balance.save(update_fields=["entitled_days", "updated_at"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Accrual for {year}: {updated} balance(s) updated "
                f"({balances.count()} monthly-accrual balances checked)."
            )
        )
