#userprofile view

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import UserProfile
from .forms import UserProfileForm

@login_required
def user_profile_view(request):
    user_profile = UserProfile.objects.get(user=request.user)
    return render(request, 'user_profile.html', {'user_profile': user_profile})

@login_required
def update_user_profile_view(request):
    user_profile = UserProfile.objects.get(user=request.user)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            form.save()
            return redirect('user_profile_view')
    else:
        form = UserProfileForm(instance=user_profile)
    return render(request, 'update_user_profile.html', {'form': form})

@login_required
def create_user_profile_view(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user_profile = form.save(commit=False)
            user_profile.user = request.user
            user_profile.save()
            return redirect('user_profile_view')
    else:
        form = UserProfileForm()
    return render(request, 'create_user_profile.html', {'form': form})

@login_required
def delete_user_profile_view(request):
    user_profile = UserProfile.objects.get(user=request.user)
    user_profile.delete()
    return redirect('login')