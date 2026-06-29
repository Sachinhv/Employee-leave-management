from django.urls import path
from . import views

urlpatterns = [

    # Root → redirects to role-based dashboard
    path('', views.dashboard, name='dashboard'),

    # ── EMPLOYEE URLS ─────────────────────────────────────────
    path('employee/dashboard/',            views.employee_dashboard, name='employee_dashboard'),
    path('employee/apply/',                views.employee_apply,     name='employee_apply'),
    path('employee/my-leaves/',            views.employee_my_leaves, name='employee_my_leaves'),
    path('employee/cancel/<int:leave_id>/',views.employee_cancel,    name='employee_cancel'),

    # ── MANAGER URLS ──────────────────────────────────────────
    # Manager dashboard → shows ONLY employee leaves
    path('manager/dashboard/',             views.manager_dashboard,  name='manager_dashboard'),
    path('manager/pending/',               views.manager_pending,    name='manager_pending'),
    path('manager/review/<int:leave_id>/', views.manager_review,     name='manager_review'),
    path('manager/team-leaves/',           views.manager_team_leaves,name='manager_team_leaves'),
    # Manager's own leave (separate from dashboard)
    path('manager/my-apply/',              views.manager_apply,      name='manager_apply'),
    path('manager/my-leaves/',             views.manager_my_leaves,  name='manager_my_leaves'),
    path('manager/my-cancel/<int:leave_id>/', views.manager_cancel,  name='manager_cancel'),

    # ── ADMIN URLS ────────────────────────────────────────────
    # Admin dashboard → shows ONLY manager leaves
    path('admin-panel/dashboard/',              views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/pending/',                views.admin_pending,   name='admin_pending'),
    path('admin-panel/review/<int:leave_id>/',  views.admin_review,    name='admin_review'),
    path('admin-panel/all-leaves/',             views.admin_all_leaves,name='admin_all_leaves'),

    # ── SHARED ────────────────────────────────────────────────
    path('leave/<int:leave_id>/',          views.leave_detail,       name='leave_detail'),
]
