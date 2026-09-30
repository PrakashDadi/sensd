from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages

from sensdrequests.models import Request as RequestModel, ResultModel
from isdrequests.models import Request as DistributionRequest


from .models import UserDetails, UserProfile
from .forms import UserDetailsForm, UserProfileForm


from django.utils.encoding import force_bytes , DjangoUnicodeDecodeError , force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.urls import reverse

from authentication.models import UserKey
from authentication.utils import encrypt_data, decrypt_data

from django.contrib.auth import get_user_model
User = get_user_model()

import logging

# Set up logging
logger = logging.getLogger(__name__)
# Create your views here.


def index(request):
    return render(request, 'dashboard/platform_home.html')

def adminindex(request):  
    uservalues = request.session.get('uservalues', None)
    print("Session uservalues retrieved:", uservalues)
    return render(request, 'dashboard/adminindex.html', {'uservalues': uservalues})

def home(request):
    uservalues =  request.session.get('uservalues', None)
    print("Session uservalues at home retrieved:", uservalues)
    if uservalues is None:
        messages.error(request, 'Session expired or invalid.')
        return redirect('login')
    
    user_key = UserKey.objects.get(user_id=uservalues['pk'])
    private_key = user_key.private_key

    all_requests = RequestModel.objects.all()
    print("This are all requests", all_requests)
    user_requests = []

    all_results = ResultModel.objects.all()
    user_results = []
    for req in all_requests:
        print("Encrypted created_by:", req.created_by)
        try:
            decrypted_created_by = decrypt_data(private_key, json.loads(req.created_by))
            print("Decrypted created_by:", decrypted_created_by)
            print("Decrypted created_by:", decrypted_created_by)
            if decrypted_created_by == uservalues['email']:
                req.created_by = decrypted_created_by  # Optional: for display
                user_requests.append(req)
        except Exception as e:
            print("Decryption failed for a request:", e)

    for res in all_results:
        try:
            decrypted_created_by = decrypt_data(private_key, json.loads(res.created_by))
            print("Decrypted results created_by:", decrypted_created_by)
            print("Decrypted results created_by:", decrypted_created_by)
            if decrypted_created_by == uservalues['email']:
                res.created_by = decrypted_created_by  # Optional: for display
                user_results.append(res)
        except Exception as e:
            print("Decryption failed for a result:", e)

    # requestlists = RequestModel.objects.filter(created_by = uservalues['email'])
    # resultlists = ResultModel.objects.filter(created_by = uservalues['email'])

    distribution_requests = DistributionRequest.objects.order_by('-created_at')
    if request.user.is_authenticated:
        owned_distribution_requests = distribution_requests.filter(requested_by=request.user)
        if owned_distribution_requests.exists():
            distribution_requests = owned_distribution_requests

    return render(request, 'dashboard/index.html',{
        'uservalues': uservalues,
        'requests': user_requests,
        'results': user_results,
        'distribution_requests': distribution_requests[:6],
        'sensor_request_count': len(user_requests),
        'sensor_result_count': len(user_results),
        'distribution_request_count': distribution_requests.count(),
        'distribution_result_count': distribution_requests.filter(status='DONE').count(),
    })
def add_user(request):
    return render(request, 'dashboard/add_users.html')

#user actions
def add_user_request(request):
    return render(request, 'userrequests/new_user_request.html')

def request_history(request):
    return render(request, 'userrequests/requests_list_history.html')

def _account_identity(request):
    """Return the decrypted login identity without changing authentication storage."""
    session_identity = request.session.get('uservalues') or {}
    username = session_identity.get('username')
    email = session_identity.get('email')
    if username and email:
        return username, email

    try:
        user_key = UserKey.objects.get(user=request.user)
        username = decrypt_data(user_key.private_key, json.loads(request.user.username))
        email = decrypt_data(user_key.private_key, json.loads(request.user.email))
        return username, email
    except (UserKey.DoesNotExist, TypeError, ValueError, json.JSONDecodeError, KeyError):
        # Tests and conventionally-created accounts may contain ordinary text.
        return str(request.user.username or ''), str(request.user.email or '')


def _profile_for_user(user, account_email):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    changed = False
    legacy = UserDetails.objects.filter(email__iexact=account_email).first() if account_email else None
    if legacy:
        for field, value in (
            ('first_name', legacy.firstname), ('last_name', legacy.lastname),
            ('phone', legacy.phonenumber), ('address', legacy.address),
            ('city', legacy.city), ('state', legacy.state),
            ('postal_code', legacy.pincode),
        ):
            if not getattr(profile, field) and value:
                setattr(profile, field, value)
                changed = True
    poultry = getattr(user, 'poultry_profile', None)
    if poultry:
        for field, value in (
            ('first_name', poultry.first_name), ('last_name', poultry.last_name),
            ('photo_data_url', poultry.photo_data_url),
        ):
            if not getattr(profile, field) and value:
                setattr(profile, field, value)
                changed = True
    if changed:
        profile.save()
    return profile


def _sync_existing_poultry_profile(user, profile, account_email):
    poultry = getattr(user, 'poultry_profile', None)
    if poultry:
        poultry.first_name = profile.first_name
        poultry.last_name = profile.last_name
        poultry.email = account_email
        poultry.photo_data_url = profile.photo_data_url or ''
        poultry.save()


@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def profile(request):
    account_username, account_email = _account_identity(request)
    user_profile = _profile_for_user(request.user, account_email)
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user_profile)
        if form.is_valid():
            user_profile = form.save()
            _sync_existing_poultry_profile(request.user, user_profile, account_email)
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=user_profile)
    display_name = ' '.join(filter(None, [user_profile.first_name, user_profile.last_name]))
    return render(request, 'userprofile/userprofile.html', {
        'form': form,
        'profile': user_profile,
        'account_email': account_email,
        'account_username': account_username,
        'display_name': display_name or account_username or 'Your profile',
        'profile_initials': ((user_profile.first_name or account_username or '?')[:1]
                             + (user_profile.last_name or '')[:1]).upper(),
    })


@login_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def create_user_profile(request, encoded_email):
    return redirect('profile')


@login_required
def redirect_edit(request, pk):
    return redirect('profile')


@login_required
def edit_user_profile(request, pk):
    return redirect('profile')

def profiles_list(request):
    users = UserDetails.objects.all()
    return render(request, 'profile_list.html', {'users': users})



@login_required
def profile_details(request, encoded_email):
    return redirect('profile')

