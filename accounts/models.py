from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    ROLES:
      employee → applies leave → manager approves
      manager  → applies leave → admin approves
      admin    → approves manager leaves only
    """
    ROLE_CHOICES = (
        ('employee', 'Employee'),
        ('manager',  'Manager'),
        ('admin',    'Admin'),
    )

    # Primary key: id (auto, from AbstractUser)
    role        = models.CharField(max_length=10, choices=ROLE_CHOICES, default='employee')
    department  = models.CharField(max_length=100, blank=True)
    phone       = models.CharField(max_length=15, blank=True)
    employee_id = models.CharField(max_length=20, blank=True, null=True, unique=True)

    def __str__(self):
        name = self.get_full_name() or self.username
        return f"{name} [{self.get_role_display()}] — {self.department}"

    # Convenience checks
    @property
    def is_employee(self):   return self.role == 'employee'
    @property
    def is_manager(self):    return self.role == 'manager'
    @property
    def is_admin_user(self): return self.role == 'admin'
