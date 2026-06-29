from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as Base
from .models import User


@admin.register(User)
class UserAdmin(Base):
    list_display   = ['id', 'username', 'first_name', 'last_name', 'employee_id', 'role', 'department', 'email', 'is_active']
    list_filter    = ['role', 'department', 'is_active']
    search_fields  = ['username', 'email', 'employee_id', 'first_name', 'last_name', 'department']
    ordering       = ['role', 'department', 'username']
    fieldsets      = Base.fieldsets + (
        ('Employee Info', {'fields': ('role', 'department', 'phone', 'employee_id')}),
    )
    add_fieldsets  = Base.add_fieldsets + (
        ('Employee Info', {'fields': ('role', 'department', 'phone', 'employee_id')}),
    )
