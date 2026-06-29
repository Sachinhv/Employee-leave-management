"""
=============================================================
COMPLETE PERMISSION RULES
=============================================================
ROLE        APPLY LEAVE?   WHO APPROVES?   DASHBOARD SHOWS
─────────────────────────────────────────────────────────────
Employee    YES            Manager         Own leave history
                                           + balance card
Manager     YES (own)      Admin           ONLY employee
                                           leaves (dept)
                                           NO apply form here
Admin       NO             —               manager and employee
                                           leaves
                                           NO apply form here
─────────────────────────────────────────────────────────────
KEY RULES:
  1. Employee CANNOT approve any leave (blocked in views)
  2. Manager CANNOT approve their own or other manager leaves
  3. Manager sees ONLY employee leaves on their dashboard
  4. Manager apply form is on a SEPARATE page (not dashboard)
  5. Admin sees manager and employee leaves on admin dashboard
  6. Admin has NO apply-leave form anywhere
  7. Employee leave form NEVER appears on manager/admin pages
=============================================================
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.http import HttpResponseForbidden
from .models import LeaveApplication, LeaveBalance
from .forms import LeaveApplicationForm, ReviewForm
from accounts.models import User
from datetime import datetime


# ═══════════════════════════════════════════════════════════
# DECORATORS — role guards
# ═══════════════════════════════════════════════════════════

def role_required(*allowed_roles):
    """Generic role guard decorator."""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles:
                messages.error(request, "You do not have permission to access that page.")
                return redirect('dashboard')
            return view_func(request, *args, **kwargs)
        wrapper.__name__ = view_func.__name__
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════
# ROOT DASHBOARD — redirects to role-specific dashboard
# ═══════════════════════════════════════════════════════════

@login_required
def dashboard(request):
    if request.user.role == 'employee':
        return redirect('employee_dashboard')
    elif request.user.role == 'manager':
        return redirect('manager_dashboard')
    elif request.user.role == 'admin':
        return redirect('admin_dashboard')
    return redirect('login')


# ═══════════════════════════════════════════════════════════
# EMPLOYEE SECTION
# ═══════════════════════════════════════════════════════════

@role_required('employee')
def employee_dashboard(request):
    """
    Shows:  Leave balance card + own leave history + stats
    No:     Approve buttons, manager leaves, admin controls
    """
    user = request.user
    lb, _ = LeaveBalance.objects.get_or_create(user=user, year=datetime.now().year)
    my_leaves = LeaveApplication.objects.filter(applicant=user)

    context = {
        'lb':             lb,
        'recent_leaves':  my_leaves[:6],
        'total':          my_leaves.count(),
        'pending_count':  my_leaves.filter(status='pending').count(),
        'approved_count': my_leaves.filter(status='approved').count(),
        'rejected_count': my_leaves.filter(status='rejected').count(),
        'casual_pct':     min((lb.casual_leave / 12) * 100, 100),
        'sick_pct':       min((lb.sick_leave   / 12) * 100, 100),
        'earned_pct':     min((lb.earned_leave / 15) * 100, 100),
    }
    return render(request, 'employee/dashboard.html', context)


@role_required('employee')
def employee_apply(request):
    """
    ONLY employees can access this page.
    Manager dashboard has NO link to this page.
    Admin has NO access to this page.
    """
    user  = request.user
    lb, _ = LeaveBalance.objects.get_or_create(user=user, year=datetime.now().year)

    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST)
        if form.is_valid():
            leave            = form.save(commit=False)
            leave.applicant  = user
            leave.total_days = leave.calculate_working_days()

            # Check balance
            available = lb.get_balance(leave.leave_type)
            if leave.total_days > available:
                messages.error(request,
                    f"Insufficient {leave.get_leave_type_display()}. "
                    f"Available: {available} day(s), Requested: {leave.total_days} day(s)."
                )
                return render(request, 'employee/apply.html', {'form': form, 'lb': lb})

            leave.save()
            messages.success(request,
                f"Leave application (LEAVE-{leave.leave_id}) submitted for "
                f"{leave.total_days} day(s). Your manager will review it."
            )
            return redirect('employee_dashboard')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = LeaveApplicationForm()

    return render(request, 'employee/apply.html', {'form': form, 'lb': lb})


@role_required('employee')
def employee_my_leaves(request):
    """Employee views own complete leave history."""
    user  = request.user
    lb, _ = LeaveBalance.objects.get_or_create(user=user, year=datetime.now().year)
    leaves = LeaveApplication.objects.filter(applicant=user)
    sf     = request.GET.get('status', '')
    if sf:
        leaves = leaves.filter(status=sf)

    context = {
        'leaves':         leaves,
        'lb':             lb,
        'status_filter':  sf,
        'total':          LeaveApplication.objects.filter(applicant=user).count(),
        'pending_count':  LeaveApplication.objects.filter(applicant=user, status='pending').count(),
        'approved_count': LeaveApplication.objects.filter(applicant=user, status='approved').count(),
        'rejected_count': LeaveApplication.objects.filter(applicant=user, status='rejected').count(),
    }
    return render(request, 'employee/my_leaves.html', context)


@role_required('employee')
def employee_cancel(request, leave_id):
    """Employee cancels their OWN pending leave only."""
    leave = get_object_or_404(LeaveApplication, leave_id=leave_id, applicant=request.user)

    if leave.status != 'pending':
        messages.error(request, "Only pending applications can be cancelled.")
        return redirect('employee_my_leaves')

    if request.method == 'POST':
        ref = leave.leave_id
        leave.delete()
        messages.success(request, f"Leave application LEAVE-{ref} cancelled successfully.")
        return redirect('employee_my_leaves')

    return render(request, 'employee/cancel.html', {'leave': leave})


# ═══════════════════════════════════════════════════════════
# MANAGER SECTION
# ═══════════════════════════════════════════════════════════

@role_required('manager')
def manager_dashboard(request):
    """
    Shows:  ONLY employee leaves from manager's department
    No:     Apply-leave form, manager's own leaves, admin data
    No:     Employee cannot access this page
    """
    dept       = request.user.department
    emp_leaves = LeaveApplication.objects.filter(
        applicant__role='employee',
        applicant__department=dept
    ).select_related('applicant')

    context = {
        'recent_leaves':  emp_leaves[:8],
        'pending_count':  emp_leaves.filter(status='pending').count(),
        'approved_count': emp_leaves.filter(status='approved').count(),
        'rejected_count': emp_leaves.filter(status='rejected').count(),
        'total_count':    emp_leaves.count(),
        'dept':           dept,
        'pending_list':   emp_leaves.filter(status='pending')[:5],
    }
    return render(request, 'manager/dashboard.html', context)


@role_required('manager')
def manager_pending(request):
    """
    Manager sees ALL pending employee leaves in their department.
    Manager CANNOT see or approve manager leaves here.
    """
    pending = LeaveApplication.objects.filter(
        applicant__role='employee',
        applicant__department=request.user.department,
        status='pending'
    ).select_related('applicant').order_by('-applied_date')

    return render(request, 'manager/pending.html', {'pending_leaves': pending})


@role_required('manager')
def manager_review(request, leave_id):
    """
    Manager approves/rejects employee leave.
    BLOCKED if: applicant is not an employee, or wrong department.
    Employee CANNOT access this view (role_required('manager') blocks it).
    """
    leave = get_object_or_404(LeaveApplication, leave_id=leave_id)

    # ── RULE 1: Only employee leaves ──────────────────────────
    if leave.applicant.role != 'employee':
        messages.error(request, "You can only review employee leave applications.")
        return redirect('manager_dashboard')

    # ── RULE 2: Only same department ──────────────────────────
    if leave.applicant.department != request.user.department:
        messages.error(request, "You can only review leaves from your own department.")
        return redirect('manager_dashboard')

    # ── RULE 3: Must be pending ────────────────────────────────
    if leave.status != 'pending':
        messages.warning(request, f"LEAVE-{leave.leave_id} has already been {leave.status}.")
        return redirect('manager_pending')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            comment  = form.cleaned_data['comment']

            if decision == 'approve':
                # Deduct balance
                lb, _ = LeaveBalance.objects.get_or_create(
                    user=leave.applicant, year=datetime.now().year
                )
                if leave.leave_type == 'casual':
                    lb.casual_leave = max(0, lb.casual_leave - leave.total_days)
                elif leave.leave_type == 'sick':
                    lb.sick_leave   = max(0, lb.sick_leave - leave.total_days)
                elif leave.leave_type == 'earned':
                    lb.earned_leave = max(0, lb.earned_leave - leave.total_days)
                lb.save()
                leave.status = 'approved'
                messages.success(request, f"LEAVE-{leave.leave_id} APPROVED for {leave.applicant.username}.")
            else:
                leave.status = 'rejected'
                messages.success(request, f"LEAVE-{leave.leave_id} REJECTED for {leave.applicant.username}.")

            leave.reviewed_by    = request.user
            leave.review_comment = comment
            leave.review_date    = datetime.now()
            leave.save()

            _send_email_notification(leave, request.user)
            return redirect('manager_pending')
    else:
        form = ReviewForm()

    return render(request, 'manager/review.html', {'leave': leave, 'form': form})


@role_required('manager')
def manager_team_leaves(request):
    """Manager views all employee leaves in their department with filters."""
    dept   = request.user.department
    leaves = LeaveApplication.objects.filter(
        applicant__role='employee',
        applicant__department=dept
    ).select_related('applicant')

    sf = request.GET.get('status', '')
    if sf:
        leaves = leaves.filter(status=sf)

    return render(request, 'manager/team_leaves.html', {'leaves': leaves, 'status_filter': sf, 'dept': dept})


@role_required('manager')
def manager_apply(request):
    """
    Manager applies for their OWN leave.
    This page is SEPARATE from manager dashboard.
    Manager dashboard does NOT show this form.
    This leave goes to ADMIN for approval.
    """
    user  = request.user
    lb, _ = LeaveBalance.objects.get_or_create(user=user, year=datetime.now().year)

    if request.method == 'POST':
        form = LeaveApplicationForm(request.POST)
        if form.is_valid():
            leave            = form.save(commit=False)
            leave.applicant  = user
            leave.total_days = leave.calculate_working_days()

            available = lb.get_balance(leave.leave_type)
            if leave.total_days > available:
                messages.error(request,
                    f"Insufficient {leave.get_leave_type_display()}. "
                    f"Available: {available} day(s), Requested: {leave.total_days} day(s)."
                )
                return render(request, 'manager/apply.html', {'form': form, 'lb': lb})

            leave.save()
            messages.success(request,
                f"Leave application (LEAVE-{leave.leave_id}) submitted for "
                f"{leave.total_days} day(s). Admin will review it."
            )
            return redirect('manager_my_leaves')
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = LeaveApplicationForm()

    return render(request, 'manager/apply.html', {'form': form, 'lb': lb})


@role_required('manager')
def manager_my_leaves(request):
    """Manager views only their own personal leave applications."""
    user  = request.user
    lb, _ = LeaveBalance.objects.get_or_create(user=user, year=datetime.now().year)
    leaves = LeaveApplication.objects.filter(applicant=user)
    sf     = request.GET.get('status', '')
    if sf:
        leaves = leaves.filter(status=sf)

    context = {
        'leaves':         leaves,
        'lb':             lb,
        'status_filter':  sf,
        'total':          LeaveApplication.objects.filter(applicant=user).count(),
        'pending_count':  LeaveApplication.objects.filter(applicant=user, status='pending').count(),
        'approved_count': LeaveApplication.objects.filter(applicant=user, status='approved').count(),
        'rejected_count': LeaveApplication.objects.filter(applicant=user, status='rejected').count(),
    }
    return render(request, 'manager/my_leaves.html', context)


@role_required('manager')
def manager_cancel(request, leave_id):
    """Manager cancels their OWN pending leave only."""
    leave = get_object_or_404(LeaveApplication, leave_id=leave_id, applicant=request.user)

    if leave.status != 'pending':
        messages.error(request, "Only pending applications can be cancelled.")
        return redirect('manager_my_leaves')

    if request.method == 'POST':
        ref = leave.leave_id
        leave.delete()
        messages.success(request, f"Leave application LEAVE-{ref} cancelled.")
        return redirect('manager_my_leaves')

    return render(request, 'manager/cancel.html', {'leave': leave})


# ═══════════════════════════════════════════════════════════
# ADMIN SECTION
# ═══════════════════════════════════════════════════════════

@role_required('admin')
def admin_dashboard(request):
    """
    Shows:  manager and employee leave applications
    No:     Employee leaves, apply-leave form, leave balance
    Admin CANNOT apply for leave through this system.
    """
    all_leaves = LeaveApplication.objects.all().select_related('applicant')


    # All managers list for sidebar info
    managers = User.objects.filter(role='manager').order_by('department', 'username')

    context = {
        'recent_leaves':  all_leaves[:8],
        'pending_count':  all_leaves.filter(status='pending').count(),
        'approved_count': all_leaves.filter(status='approved').count(),
        'rejected_count': all_leaves.filter(status='rejected').count(),
        'total_count':    all_leaves.count(),
        'pending_list':   all_leaves.filter(status='pending')[:5],
        'managers':       managers,
    }
    return render(request, 'admin/dashboard.html', context)


@role_required('admin')
def admin_pending(request):
    """
    Admin sees ALL pending leaves (manager + employee).
    """
    pending = LeaveApplication.objects.filter(
        status='pending'
    ).select_related('applicant').order_by('-applied_date')

    return render(request, 'admin/pending.html', {'pending_leaves': pending})



@role_required('admin')
def admin_review(request, leave_id):
    """
    Admin approves/rejects ANY pending leave.
    """

    leave = get_object_or_404(LeaveApplication, leave_id=leave_id)

    # Must be pending
    if leave.status != 'pending':
        messages.warning(
            request,
            f"LEAVE-{leave.leave_id} has already been {leave.status}."
        )
        return redirect('admin_pending')

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data['decision']
            comment  = form.cleaned_data['comment']

            if decision == 'approve':
                lb, _ = LeaveBalance.objects.get_or_create(
                    user=leave.applicant,
                    year=datetime.now().year
                )

                if leave.leave_type == 'casual':
                    lb.casual_leave = max(0, lb.casual_leave - leave.total_days)
                elif leave.leave_type == 'sick':
                    lb.sick_leave = max(0, lb.sick_leave - leave.total_days)
                elif leave.leave_type == 'earned':
                    lb.earned_leave = max(0, lb.earned_leave - leave.total_days)

                lb.save()
                leave.status = 'approved'
                messages.success(
                    request,
                    f"LEAVE-{leave.leave_id} APPROVED for {leave.applicant.username}."
                )
            else:
                leave.status = 'rejected'
                messages.success(
                    request,
                    f"LEAVE-{leave.leave_id} REJECTED for {leave.applicant.username}."
                )

            leave.reviewed_by = request.user
            leave.review_comment = comment
            leave.review_date = datetime.now()
            leave.save()

            _send_email_notification(leave, request.user)
            return redirect('admin_pending')
    else:
        form = ReviewForm()

    return render(request, 'admin/review.html', {
        'leave': leave,
        'form': form
    })

@role_required('admin')
def admin_all_leaves(request):
    """
    Admin views ALL leave applications with filters.
    """
    leaves = LeaveApplication.objects.all().select_related('applicant')

    sf = request.GET.get('status', '')
    if sf:
        leaves = leaves.filter(status=sf)

    return render(request, 'admin/all_leaves.html', {
        'leaves': leaves,
        'status_filter': sf
    })

# ═══════════════════════════════════════════════════════════
# SHARED: Leave detail (read-only, permission-checked)
# ═══════════════════════════════════════════════════════════
@login_required
def leave_detail(request, leave_id):
    leave = get_object_or_404(LeaveApplication, leave_id=leave_id)
    user = request.user

    # Employee: only own leaves
    if user.role == 'employee' and leave.applicant != user:
        messages.error(request, "You can only view your own leave applications.")
        return redirect('employee_my_leaves')

    # Manager: only employee leaves from their department
    if user.role == 'manager':
        if leave.applicant.role != 'employee' or leave.applicant.department != user.department:
            messages.error(request, "You can only view employee leaves from your department.")
            return redirect('manager_dashboard')

    # Admin: can view ALL leave applications
    return render(request, 'shared/leave_detail.html', {'leave': leave})

# ═══════════════════════════════════════════════════════════
# HELPER: Email notification
# ═══════════════════════════════════════════════════════════

def _send_email_notification(leave, reviewer):
    """Sends email to applicant. In dev mode prints to terminal."""
    try:
        send_mail(
            subject=f'[LeaveMS] Leave Application {leave.status.upper()} — LEAVE-{leave.leave_id}',
            message=(
                f"Dear {leave.applicant.get_full_name() or leave.applicant.username},\n\n"
                f"Your {leave.get_leave_type_display()} application (LEAVE-{leave.leave_id}) "
                f"from {leave.start_date} to {leave.end_date} "
                f"({leave.total_days} working day(s)) has been {leave.status.upper()}.\n\n"
                f"Reviewed by : {reviewer.get_full_name() or reviewer.username} [{reviewer.get_role_display()}]\n"
                f"Comment     : {leave.review_comment or 'No comment provided.'}\n"
                f"Review Date : {leave.review_date.strftime('%d %b %Y, %I:%M %p') if leave.review_date else 'N/A'}\n\n"
                f"Regards,\nLeave Management System"
            ),
            from_email='noreply@leavems.com',
            recipient_list=[leave.applicant.email],
            fail_silently=True,
        )
    except Exception:
        pass
