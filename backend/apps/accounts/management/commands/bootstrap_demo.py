"""Bootstrap a working demo: platform admin + a demo tenant with users.

Idempotent. Intended for local development and first-run setup. Reads
optional credentials from the environment; falls back to documented
defaults (see .env.example / README).
"""
import os
from datetime import date

from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Role, User
from apps.employees.enums import EmploymentStatus
from apps.employees.models import Employee
from apps.leave.enums import AccrualMethod, GenderEligibility, LeaveCategory
from apps.leave.models import LeaveType
from apps.leave import services as leave_services
from apps.documents.models import DocumentCategory
from apps.notifications.default_templates import DEFAULT_TEMPLATES
from apps.notifications.models import NotificationTemplate
from apps.workflows.enums import ApproverType, WorkflowEntity
from apps.workflows.models import Workflow, WorkflowStage
from apps.education_assistance.enums import (
    AcademicPeriodType,
    ClaimDocumentType,
    EducationLevel,
)
from apps.education_assistance.models import EducationBenefitRule
from apps.payroll.enums import ComponentType
from apps.payroll.models import PayComponent
from apps.benefits.enums import BenefitCategory, ContributionBasis
from apps.benefits.models import BenefitType
from apps.recruitment.enums import PostingStatus, RecruitmentStage, RequisitionStatus
from apps.recruitment.models import Candidate, JobPosting, JobRequisition
from apps.onboarding.enums import ProgrammeType, TaskOwnerRole
from apps.onboarding.models import ChecklistTaskTemplate, ChecklistTemplate
from apps.performance.enums import ReviewCycleStatus
from apps.performance.models import ReviewCycle
from apps.learning.enums import CourseCategory, DeliveryMode
from apps.learning.models import TrainingCourse
from apps.assets.models import AssetCategory
from apps.helpdesk.models import CaseCategory
from apps.attendance.models import Shift
from apps.policies.enums import PolicyCategory
from apps.policies.models import Policy, PolicyVersion
from apps.policies import services as policy_services
from apps.settings import services as settings_services
from apps.organisation.models import (
    CostCentre,
    Department,
    Grade,
    JobTitle,
    Location,
    Position,
)
from apps.tenants.models import (
    Tenant,
    TenantDomain,
    TenantSettings,
    TenantUserMembership,
)


class Command(BaseCommand):
    help = "Create a platform admin and a seeded demo organisation."

    @transaction.atomic
    def handle(self, *args, **options):
        # Ensure the RBAC catalogue exists first.
        call_command("seed_rbac")

        # --- Platform super administrator ---------------------------------
        admin_email = os.environ.get("PLATFORM_ADMIN_EMAIL", "admin@bunchly.local")
        admin_password = os.environ.get("PLATFORM_ADMIN_PASSWORD", "Bunchly!Admin1")
        admin, created = User.objects.get_or_create(
            email=admin_email,
            defaults={
                "first_name": "Platform",
                "last_name": "Admin",
                "is_staff": True,
                "is_superuser": True,
                "is_platform_admin": True,
                "is_email_verified": True,
            },
        )
        if created:
            admin.set_password(admin_password)
            admin.save()
        self.stdout.write(self.style.SUCCESS(f"Platform admin: {admin_email}"))

        # --- Demo tenant --------------------------------------------------
        tenant, _ = Tenant.objects.get_or_create(
            slug="acme",
            defaults={
                "name": "Acme Corporation",
                "legal_name": "Acme Corporation Ltd",
                "country": "United Kingdom",
                "onboarded_at": timezone.now(),
            },
        )
        TenantSettings.objects.get_or_create(tenant=tenant)
        TenantDomain.objects.get_or_create(
            domain="acme", tenant=tenant, defaults={"is_primary": True}
        )

        # Copy system role templates into the tenant.
        for system_role in Role.objects.filter(tenant=None):
            tenant_role, _ = Role.objects.get_or_create(
                tenant=tenant,
                name=system_role.name,
                defaults={
                    "description": system_role.description,
                    "is_system": True,
                },
            )
            tenant_role.permissions.set(system_role.permissions.all())

        roles = {r.name: r for r in Role.objects.filter(tenant=tenant)}

        # --- Demo users ---------------------------------------------------
        # One per role so every persona in the RBAC catalogue is reachable
        # from the login screen. A real org would mix-and-match roles per
        # user; here each user holds exactly one for testing clarity.
        demo_users = [
            ("owner@acme.test", "Olivia", "Owner", "Organisation Administrator", True),
            ("hr@acme.test", "Henry", "Hughes", "HR Administrator", False),
            ("manager@acme.test", "Mary", "Manning", "Line Manager", False),
            ("employee@acme.test", "Evan", "Edwards", "Employee", False),
            ("finance@acme.test", "Fiona", "Finch", "Accounts / Finance Officer", False),
            ("recruiter@acme.test", "Riley", "Reeves", "Recruiter", False),
            ("payroll@acme.test", "Patrick", "Park", "Payroll Officer", False),
            ("auditor@acme.test", "Aisha", "Akande", "Auditor", False),
            ("exec@acme.test", "Eleanor", "Eaton", "Executive / Head of HR", False),
        ]
        for email, first, last, role_name, is_owner in demo_users:
            user, was_created = User.objects.get_or_create(
                email=email,
                defaults={
                    "first_name": first,
                    "last_name": last,
                    "is_email_verified": True,
                },
            )
            if was_created:
                user.set_password("Bunchly!Demo1")
                user.save()
            membership, _ = TenantUserMembership.objects.get_or_create(
                tenant=tenant,
                user=user,
                defaults={"is_default": True, "joined_at": timezone.now()},
            )
            membership.is_owner = is_owner
            membership.save()
            if role_name in roles:
                membership.roles.set([roles[role_name]])

        # --- Organisation structure ---------------------------------------
        hq, _ = Location.objects.get_or_create(
            tenant=tenant,
            code="HQ",
            defaults={
                "name": "London HQ",
                "city": "London",
                "country": "United Kingdom",
            },
        )
        cost_centre, _ = CostCentre.objects.get_or_create(
            tenant=tenant, code="CC-OPS", defaults={"name": "Operations"}
        )
        grades = {}
        for code, gname, level in [
            ("G1", "Associate", 1),
            ("G2", "Senior", 2),
            ("G3", "Lead", 3),
            ("G4", "Director", 4),
        ]:
            grades[code], _ = Grade.objects.get_or_create(
                tenant=tenant, code=code, defaults={"name": gname, "level": level}
            )
        departments = {}
        for code, dname in [
            ("ENG", "Engineering"),
            ("PEOPLE", "People Operations"),
            ("FIN", "Finance"),
        ]:
            departments[code], _ = Department.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": dname,
                    "location": hq,
                    "cost_centre": cost_centre,
                },
            )
        job_titles = {}
        for code, jname in [
            ("SWE", "Software Engineer"),
            ("HRBP", "HR Business Partner"),
            ("ACC", "Accountant"),
            ("CHRO", "Chief People Officer"),
            ("RECRUITER", "Talent Acquisition Partner"),
            ("PAYROLL", "Payroll Specialist"),
            ("AUDITOR", "Internal Auditor"),
        ]:
            job_titles[code], _ = JobTitle.objects.get_or_create(
                tenant=tenant, code=code, defaults={"name": jname}
            )
        for jt_code, dept_code, grade_code in [
            ("SWE", "ENG", "G2"),
            ("HRBP", "PEOPLE", "G3"),
            ("ACC", "FIN", "G2"),
            ("CHRO", "PEOPLE", "G4"),
            ("RECRUITER", "PEOPLE", "G2"),
            ("PAYROLL", "FIN", "G2"),
            ("AUDITOR", "FIN", "G3"),
        ]:
            Position.objects.get_or_create(
                tenant=tenant,
                job_title=job_titles[jt_code],
                department=departments[dept_code],
                defaults={"grade": grades[grade_code], "location": hq},
            )

        # --- Employee records ---------------------------------------------
        # (email, number, department, job title, grade, status, manager email)
        employee_seed = [
            ("owner@acme.test", "EMP-001", "PEOPLE", "HRBP", "G4", EmploymentStatus.ACTIVE, None),
            ("hr@acme.test", "EMP-002", "PEOPLE", "HRBP", "G3", EmploymentStatus.ACTIVE, "owner@acme.test"),
            ("manager@acme.test", "EMP-003", "ENG", "SWE", "G3", EmploymentStatus.ACTIVE, "owner@acme.test"),
            ("employee@acme.test", "EMP-004", "ENG", "SWE", "G1", EmploymentStatus.PROBATION, "manager@acme.test"),
            ("finance@acme.test", "EMP-005", "FIN", "ACC", "G2", EmploymentStatus.ACTIVE, "owner@acme.test"),
            ("recruiter@acme.test", "EMP-006", "PEOPLE", "RECRUITER", "G2", EmploymentStatus.ACTIVE, "hr@acme.test"),
            ("payroll@acme.test", "EMP-007", "FIN", "PAYROLL", "G2", EmploymentStatus.ACTIVE, "finance@acme.test"),
            ("auditor@acme.test", "EMP-008", "FIN", "AUDITOR", "G3", EmploymentStatus.ACTIVE, "owner@acme.test"),
            ("exec@acme.test", "EMP-009", "PEOPLE", "CHRO", "G4", EmploymentStatus.ACTIVE, "owner@acme.test"),
        ]
        created_emps: dict[str, Employee] = {}
        for email, number, dept_code, jt_code, grade_code, status, _mgr in employee_seed:
            seed_user = User.objects.get(email=email)
            employee, _ = Employee.objects.get_or_create(
                tenant=tenant,
                employee_number=number,
                defaults={
                    "user": seed_user,
                    "first_name": seed_user.first_name,
                    "last_name": seed_user.last_name,
                    "work_email": email,
                    "department": departments[dept_code],
                    "job_title": job_titles[jt_code],
                    "grade": grades[grade_code],
                    "work_location": hq,
                    "cost_centre": cost_centre,
                    "employment_status": status,
                    "start_date": date(2023, 1, 15),
                },
            )
            created_emps[email] = employee

        # Second pass: reporting lines.
        for email, _n, _d, _j, _g, _s, mgr_email in employee_seed:
            if mgr_email:
                employee = created_emps[email]
                employee.line_manager = created_emps[mgr_email]
                employee.save(update_fields=["line_manager", "updated_at"])

        # Department heads.
        for dept_code, head_email in [
            ("PEOPLE", "hr@acme.test"),
            ("ENG", "manager@acme.test"),
            ("FIN", "finance@acme.test"),
        ]:
            departments[dept_code].head = created_emps[head_email]
            departments[dept_code].save(update_fields=["head", "updated_at"])

        # --- Leave configuration ------------------------------------------
        # Route the optional finance notice to the configured recipient —
        # never hard-coded in business logic.
        settings_row = tenant.settings
        recipients = dict(settings_row.notification_recipients or {})
        recipients.setdefault("leave_finance_notice", ["finance@acme.test"])
        settings_row.notification_recipients = recipients
        settings_row.save(update_fields=["notification_recipients", "updated_at"])

        # (code, name, category, paid, annual days, accrual, carry-fwd,
        #  max carry, hr confirm, extra stage, requires doc, gender, notify fin)
        leave_type_seed = [
            ("ANNUAL", "Annual Leave", LeaveCategory.ANNUAL, True, 25,
             AccrualMethod.MONTHLY, True, 5, True, False, False,
             GenderEligibility.ANY, False),
            ("SICK", "Sick Leave", LeaveCategory.SICK, True, 10,
             AccrualMethod.ANNUAL_LUMP, False, 0, True, False, True,
             GenderEligibility.ANY, False),
            ("MAT", "Maternity Leave", LeaveCategory.MATERNITY, True, 90,
             AccrualMethod.ANNUAL_LUMP, False, 0, True, True, True,
             GenderEligibility.FEMALE, True),
            ("UNPAID", "Unpaid Leave", LeaveCategory.UNPAID, False, 0,
             AccrualMethod.NONE, False, 0, True, False, False,
             GenderEligibility.ANY, True),
        ]
        leave_types = {}
        for (code, name, category, paid, days, accrual, carry, max_carry,
             hr, extra, doc, gender, notify_fin) in leave_type_seed:
            leave_types[code], _ = LeaveType.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "is_paid": paid,
                    "default_annual_days": days,
                    "accrual_method": accrual,
                    "allow_carry_forward": carry,
                    "max_carry_forward_days": max_carry,
                    "requires_hr_confirmation": hr,
                    "extra_approval_stage": extra,
                    "extra_approval_label": "Finance approval" if extra else "",
                    "requires_documentation": doc,
                    "gender_eligibility": gender,
                    "notify_finance": notify_fin,
                    "min_notice_days": 2 if code == "ANNUAL" else 0,
                },
            )

        # Open a current-year balance for every employee on Annual + Sick.
        current_year = date.today().year
        for employee in created_emps.values():
            for code in ("ANNUAL", "SICK"):
                leave_services.get_or_create_balance(
                    employee, leave_types[code], current_year
                )

        # --- Document categories ------------------------------------------
        # (code, name, required, requires_approval, sensitive, tracks_expiry)
        document_category_seed = [
            ("IDPASS", "National ID / Passport", True, False, True, True),
            ("ACAD", "Academic Certificates", False, False, False, False),
            ("PROF", "Professional Certifications", False, False, False, True),
            ("CV", "CV / Résumé", False, False, False, False),
            ("BANK", "Banking Details", False, True, True, False),
            ("CONTRACT", "Contract", True, True, False, False),
            ("ADDR", "Proof of Address", False, False, False, False),
            ("BIRTH", "Birth Certificate", False, False, True, False),
            ("MEDICAL", "Medical Certificates", False, True, True, False),
            ("OTHER", "Other", False, False, False, False),
        ]
        for code, name, required, approval, sensitive, expiry in document_category_seed:
            DocumentCategory.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "is_required": required,
                    "requires_approval": approval,
                    "is_sensitive": sensitive,
                    "tracks_expiry": expiry,
                },
            )

        # --- Notification templates ---------------------------------------
        # Copy the built-in catalogue into the tenant so an admin can edit
        # or disable each notification.
        for event_key, cfg in DEFAULT_TEMPLATES.items():
            NotificationTemplate.objects.get_or_create(
                tenant=tenant,
                event_key=event_key,
                defaults={
                    "name": cfg["name"],
                    "channel": cfg["channel"],
                    "subject": cfg["subject"],
                    "body": cfg["body"],
                },
            )

        # --- Demo approval workflow ---------------------------------------
        # A two-stage leave workflow: line manager -> HR confirmation.
        leave_workflow, wf_created = Workflow.objects.get_or_create(
            tenant=tenant,
            code="WF-LEAVE",
            defaults={
                "name": "Standard Leave Approval",
                "description": "Line manager approval, then HR confirmation.",
                "entity_type": WorkflowEntity.LEAVE_REQUEST,
                "is_default": True,
            },
        )
        if wf_created:
            WorkflowStage.objects.create(
                tenant=tenant, workflow=leave_workflow,
                name="Line manager approval", sequence=1,
                approver_type=ApproverType.LINE_MANAGER, sla_days=3,
            )
            WorkflowStage.objects.create(
                tenant=tenant, workflow=leave_workflow,
                name="HR confirmation", sequence=2,
                approver_type=ApproverType.ROLE,
                approver_role=roles.get("HR Administrator"), sla_days=2,
            )

        # --- Education assistance rule ------------------------------------
        EducationBenefitRule.objects.get_or_create(
            tenant=tenant,
            name="Education Assistance Policy",
            defaults={
                "max_children": 2,
                "covered_levels": [
                    EducationLevel.PRIMARY,
                    EducationLevel.SECONDARY,
                    EducationLevel.TERTIARY,
                ],
                "max_amount_per_child": 2500,
                "currency": "GBP",
                "frequency": AcademicPeriodType.TERM,
                "eligible_employment_statuses": [
                    EmploymentStatus.ACTIVE,
                    EmploymentStatus.PROBATION,
                ],
                "require_probation_passed": True,
                "max_child_age": 25,
                "max_claims_per_period": 1,
                "required_documents": [
                    ClaimDocumentType.INVOICE,
                    ClaimDocumentType.PROOF_OF_REGISTRATION,
                ],
            },
        )

        # --- Payroll components -------------------------------------------
        # (code, name, type, taxable, default amount)
        pay_component_seed = [
            ("HOUSING", "Housing allowance", ComponentType.ALLOWANCE, True, 500),
            ("TRANSPORT", "Transport allowance", ComponentType.ALLOWANCE, True, 150),
            ("PENSION", "Pension contribution", ComponentType.DEDUCTION, False, 0),
            ("TAX", "Income tax (PAYE)", ComponentType.DEDUCTION, False, 0),
        ]
        pay_components = {}
        for code, name, ctype, taxable, amount in pay_component_seed:
            pay_components[code], _ = PayComponent.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "component_type": ctype,
                    "is_taxable": taxable,
                    "default_amount": amount,
                },
            )

        # --- Benefit types ------------------------------------------------
        # (code, name, category, basis, employee %, employer %, pay component)
        benefit_type_seed = [
            ("PMI", "Private Medical Insurance", BenefitCategory.HEALTH,
             ContributionBasis.FIXED, 80, 160, None),
            ("PENSION", "Workplace Pension", BenefitCategory.PENSION,
             ContributionBasis.PERCENTAGE, 5, 3, "PENSION"),
            ("LIFE", "Life Assurance", BenefitCategory.LIFE_INSURANCE,
             ContributionBasis.FIXED, 0, 25, None),
        ]
        for code, name, category, basis, emp, empr, pc_code in benefit_type_seed:
            BenefitType.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "contribution_basis": basis,
                    "employee_contribution": emp,
                    "employer_contribution": empr,
                    "eligibility_min_months": 3,
                    "pay_component": pay_components.get(pc_code),
                },
            )

        # --- Recruitment --------------------------------------------------
        requisition, _ = JobRequisition.objects.get_or_create(
            tenant=tenant,
            reference="REQ-00001",
            defaults={
                "title": "Software Engineer",
                "department": departments["ENG"],
                "job_title": job_titles["SWE"],
                "grade": grades["G2"],
                "headcount": 2,
                "status": RequisitionStatus.APPROVED,
                "reason": "Team expansion.",
            },
        )
        posting, posting_created = JobPosting.objects.get_or_create(
            tenant=tenant,
            requisition=requisition,
            title="Software Engineer",
            defaults={
                "description": "Join the Acme engineering team.",
                "location": hq,
                "status": PostingStatus.OPEN,
                "posted_date": date.today(),
            },
        )
        if posting_created:
            for first, last, email, stage in [
                ("Carol", "Candidate", "carol.candidate@example.com",
                 RecruitmentStage.SCREENING),
                ("Dan", "Applicant", "dan.applicant@example.com",
                 RecruitmentStage.APPLIED),
            ]:
                Candidate.objects.create(
                    tenant=tenant,
                    posting=posting,
                    first_name=first,
                    last_name=last,
                    email=email,
                    stage=stage,
                    applied_at=date.today(),
                )

        # --- Onboarding checklist template --------------------------------
        onboarding_template, tmpl_created = ChecklistTemplate.objects.get_or_create(
            tenant=tenant,
            name="Standard Onboarding",
            programme_type=ProgrammeType.ONBOARDING,
            defaults={
                "description": "Default new-joiner checklist.",
                "is_default": True,
            },
        )
        if tmpl_created:
            # (sequence, title, owner role, due offset days)
            onboarding_tasks = [
                (1, "Send welcome email", TaskOwnerRole.HR, 0),
                (2, "Prepare workstation & accounts", TaskOwnerRole.IT, 1),
                (3, "Collect bank & tax details", TaskOwnerRole.FINANCE, 3),
                (4, "Policy acknowledgement", TaskOwnerRole.EMPLOYEE, 5),
                (5, "First-week check-in", TaskOwnerRole.MANAGER, 7),
            ]
            for sequence, title, owner, offset in onboarding_tasks:
                ChecklistTaskTemplate.objects.create(
                    tenant=tenant,
                    template=onboarding_template,
                    title=title,
                    owner_role=owner,
                    sequence=sequence,
                    due_offset_days=offset,
                )

        # --- Performance review cycle -------------------------------------
        current_year = date.today().year
        ReviewCycle.objects.get_or_create(
            tenant=tenant,
            name=f"{current_year} Annual Review",
            defaults={
                "description": f"Annual performance review for {current_year}.",
                "period_start": date(current_year, 1, 1),
                "period_end": date(current_year, 12, 31),
                "status": ReviewCycleStatus.ACTIVE,
            },
        )

        # --- Training courses ---------------------------------------------
        # (code, name, category, mode, compliance, certifies, validity months)
        course_seed = [
            ("INFOSEC", "Information Security Awareness", CourseCategory.COMPLIANCE,
             DeliveryMode.ONLINE, True, True, 12),
            ("FIRSTAID", "First Aid at Work", CourseCategory.SAFETY,
             DeliveryMode.IN_PERSON, False, True, 36),
            ("LEAD101", "Foundations of Leadership", CourseCategory.LEADERSHIP,
             DeliveryMode.BLENDED, False, False, 0),
        ]
        for code, name, category, mode, compliance, certifies, validity in course_seed:
            TrainingCourse.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "category": category,
                    "delivery_mode": mode,
                    "is_compliance": compliance,
                    "provides_certification": certifies,
                    "certification_validity_months": validity,
                },
            )

        # --- Asset categories ---------------------------------------------
        for code, name in [
            ("LAPTOP", "Laptop"),
            ("PHONE", "Mobile phone"),
            ("IDCARD", "ID card"),
            ("KEYS", "Keys / access"),
            ("UNIFORM", "Uniform"),
            ("TOOLS", "Tools"),
        ]:
            AssetCategory.objects.get_or_create(
                tenant=tenant, code=code, defaults={"name": name}
            )

        # --- HR helpdesk case categories ----------------------------------
        # (code, name, default SLA hours)
        case_category_seed = [
            ("LEAVE", "Leave", 48),
            ("PAYROLL", "Payroll", 48),
            ("BENEFITS", "Benefits", 72),
            ("DOCUMENTS", "Documents", 72),
            ("CONTRACT", "Contract", 72),
            ("EDUCATION", "Education assistance", 72),
            ("PERFORMANCE", "Performance", 72),
            ("GENERAL", "General HR", 72),
        ]
        for code, name, sla in case_category_seed:
            CaseCategory.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={"name": name, "default_sla_hours": sla},
            )

        # --- Work shifts --------------------------------------------------
        # (code, name, start, end, break minutes, grace-in minutes)
        from datetime import time

        shift_seed = [
            ("DAY", "Standard Day", time(9, 0), time(17, 30), 60, 10),
            ("EARLY", "Early Shift", time(6, 0), time(14, 0), 30, 10),
            ("NIGHT", "Night Shift", time(22, 0), time(6, 0), 45, 15),
        ]
        for code, name, start, end, brk, grace in shift_seed:
            Shift.objects.get_or_create(
                tenant=tenant,
                code=code,
                defaults={
                    "name": name,
                    "start_time": start,
                    "end_time": end,
                    "break_minutes": brk,
                    "grace_in_minutes": grace,
                    "grace_out_minutes": grace,
                },
            )

        # --- Demo policies + assignments ----------------------------------
        # (code, title, category)
        policy_seed = [
            ("COC", "Code of Conduct", PolicyCategory.CODE_OF_CONDUCT),
            ("AUP", "Acceptable IT Use Policy", PolicyCategory.IT_ACCEPTABLE_USE),
        ]
        for code, title, category in policy_seed:
            policy, created = Policy.objects.get_or_create(
                tenant=tenant, code=code,
                defaults={
                    "title": title,
                    "category": category,
                    "description": f"Default seed for the {title.lower()}.",
                    "requires_acknowledgement": True,
                },
            )
            if created or policy.current_version is None:
                version = PolicyVersion.objects.create(
                    tenant=tenant, policy=policy, version="1.0",
                    change_summary="Initial publication.",
                )
                policy_services.publish_version(version)
                # Assign every active demo employee.
                policy_services.bulk_assign(
                    tenant=tenant, policy=policy,
                    employees=list(created_emps.values()),
                )

        # --- System settings ----------------------------------------------
        settings_services.seed_defaults(tenant)

        self.stdout.write(
            self.style.SUCCESS(
                "Demo tenant 'Acme Corporation' ready. Users (all password "
                "Bunchly!Demo1): owner / hr / manager / employee / finance / "
                "recruiter / payroll / auditor / exec @acme.test"
            )
        )
