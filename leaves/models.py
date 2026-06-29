from django.db import models
from django.conf import settings
from datetime import datetime, timedelta


class LeaveBalance(models.Model):
    """
    Each user gets one LeaveBalance per year (auto-created on register).
    Primary key: id (AutoField)
    """
    id           = models.AutoField(primary_key=True)
    user         = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='leave_balances'
    )
    year         = models.IntegerField(default=datetime.now().year)
    casual_leave = models.IntegerField(default=12)
    sick_leave   = models.IntegerField(default=12)
    earned_leave = models.IntegerField(default=15)

    class Meta:
        unique_together = ['user', 'year']
        verbose_name    = 'Leave Balance'

    def __str__(self):
        return f"[ID:{self.id}] {self.user.username} — {self.year}"

    def total_available(self):
        return self.casual_leave + self.sick_leave + self.earned_leave

    def get_balance(self, leave_type):
        return {
            'casual': self.casual_leave,
            'sick':   self.sick_leave,
            'earned': self.earned_leave,
        }.get(leave_type, 0)


class LeaveApplication(models.Model):
    """
    PERMISSION RULES (enforced in views.py):
    ─────────────────────────────────────────────────────────────
    Applicant Role │ Who Approves │ Visible On
    ───────────────┼──────────────┼───────────────────────────
    Employee       │ Manager      │ Manager Dashboard ONLY
    Manager        │ Admin        │ Admin Dashboard ONLY
    ─────────────────────────────────────────────────────────────
    Employee CANNOT approve any leave.
    Manager CAN approve ONLY employee leaves (same department).
    Admin CAN approve ONLY manager leaves.
    Manager leave form NOT on manager dashboard.
    Admin leave form NOT on admin dashboard.
    ─────────────────────────────────────────────────────────────

    Primary key: leave_id (explicit, visible in tables & URLs)
    """
    LEAVE_TYPE_CHOICES = (
        ('casual', 'Casual Leave'),
        ('sick',   'Sick Leave'),
        ('earned', 'Earned Leave'),
    )
    STATUS_CHOICES = (
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )

    # Explicit primary key shown in UI
    leave_id         = models.AutoField(primary_key=True)

    # Who applied
    applicant        = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='submitted_leaves'
    )

    # Leave details
    leave_type       = models.CharField(max_length=10, choices=LEAVE_TYPE_CHOICES)
    start_date       = models.DateField()
    end_date         = models.DateField()
    total_days       = models.IntegerField(default=0)
    reason           = models.TextField()

    # Workflow
    status           = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    applied_date     = models.DateTimeField(auto_now_add=True)

    # Who approved/rejected
    reviewed_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='reviewed_leaves'
    )
    review_comment   = models.TextField(blank=True, null=True)
    review_date      = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering    = ['-applied_date']
        verbose_name = 'Leave Application'

    def __str__(self):
        return (f"[LEAVE-{self.leave_id}] {self.applicant.username} "
                f"— {self.get_leave_type_display()} [{self.get_status_display()}]")

    def calculate_working_days(self):
        """Count Mon–Fri days between start_date and end_date."""
        if not self.start_date or not self.end_date:
            return 0
        count   = 0
        current = self.start_date
        while current <= self.end_date:
            if current.weekday() < 5:   # 0=Mon … 4=Fri
                count += 1
            current += timedelta(days=1)
        return max(count, 1)

    def save(self, *args, **kwargs):
        if not self.total_days:
            self.total_days = self.calculate_working_days()
        super().save(*args, **kwargs)

    # ── Status helpers ─────────────────────────────────────────
    def is_pending(self):   return self.status == 'pending'
    def is_approved(self):  return self.status == 'approved'
    def is_rejected(self):  return self.status == 'rejected'

    def status_badge(self):
        return {
            'pending':  'warning',
            'approved': 'success',
            'rejected': 'danger',
        }.get(self.status, 'secondary')

    def applicant_role(self):
        return self.applicant.role
