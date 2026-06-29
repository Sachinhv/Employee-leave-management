from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('leaves.urls')),
    path('accounts/', include('accounts.urls')),
]

admin.site.site_header = 'Leave Management System'
admin.site.site_title  = 'LMS Admin'
admin.site.index_title = 'Admin Panel'
