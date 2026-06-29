from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm, ProfileForm
from leaves.models import LeaveBalance
from datetime import datetime


def register(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Auto-create leave balance for new user
            LeaveBalance.objects.get_or_create(user=user, year=datetime.now().year)
            messages.success(request, f'Account created for {user.username}! Please login.')
            return redirect('login')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = RegisterForm()
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)
    return render(request, 'accounts/profile.html', {'form': form})
