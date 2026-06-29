from django.contrib import admin
from .models import LeaveBalance, LeaveApplication


@admin.register(LeaveBalance)
class LeaveBalanceAdmin(admin.ModelAdmin):
    list_display   = ['id', 'user', 'year', 'casual_leave', 'sick_leave', 'earned_leave']
    list_filter    = ['year', 'user__role']
    search_fields  = ['user__username', 'user__employee_id']


@admin.register(LeaveApplication)
class LeaveApplicationAdmin(admin.ModelAdmin):
    list_display    = ['leave_id', 'applicant', 'applicant_role_display', 'leave_type', 'start_date', 'end_date', 'total_days', 'status', 'reviewed_by', 'applied_date']
    list_filter     = ['status', 'leave_type', 'applicant__role', 'applicant__department']
    search_fields   = ['applicant__username', 'applicant__employee_id', 'applicant__department']
    readonly_fields = ['leave_id', 'applied_date', 'review_date', 'total_days']
    date_hierarchy  = 'applied_date'

    def applicant_role_display(self, obj):
        return obj.applicant.get_role_display()
    applicant_role_display.short_description = 'Applicant Role'
