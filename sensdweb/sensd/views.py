from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages

from requests.models import Request as RequestModel , ResultModel


from .models import UserDetails
from .forms import UserDetailsForm


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


@cache_control(no_cache=True, must_revalidate=True, no_store=True)
@login_required(login_url='/authentication/login')

def index(request):
    uservalues = request.session.get('uservalues', None)
    print("Session uservalues retrieved:", uservalues)
    return render(request, 'authentication/login.html', {'uservalues': uservalues})

def adminindex(request):  
    uservalues = request.session.get('uservalues', None)
    print("Session uservalues retrieved:", uservalues)
    return render(request, 'dashboard/adminindex.html', {'uservalues': uservalues})

def home(request):
    uservalues =  request.session.get('uservalues', None)
    if uservalues is None:
        messages.error(request, 'Session expired or invalid.')
        return redirect('login')
    
    user_key = UserKey.objects.get(user_id=uservalues['pk'])
    private_key = user_key.private_key

    all_requests = RequestModel.objects.all()
    user_requests = []

    all_results = ResultModel.objects.all()
    user_results = []
    for req in all_requests:
        try:
            decrypted_created_by = decrypt_data(private_key, json.loads(req.created_by))
            if decrypted_created_by == uservalues['email']:
                req.created_by = decrypted_created_by  # Optional: for display
                user_requests.append(req)
        except Exception as e:
            print("Decryption failed for a request:", e)

    for res in all_results:
        try:
            decrypted_created_by = decrypt_data(private_key, json.loads(res.created_by))
            if decrypted_created_by == uservalues['email']:
                res.created_by = decrypted_created_by  # Optional: for display
                user_results.append(res)
        except Exception as e:
            print("Decryption failed for a result:", e)

    # requestlists = RequestModel.objects.filter(created_by = uservalues['email'])
    # resultlists = ResultModel.objects.filter(created_by = uservalues['email'])

    return render(request, 'dashboard/index.html',{
        'uservalues': uservalues,
        'requests': user_requests,
        'results': user_results
    })

def add_user(request):
    return render(request, 'dashboard/add_users.html')

#user actions
def add_user_request(request):
    return render(request, 'userrequests/new_user_request.html')

def request_history(request):
    return render(request, 'userrequests/requests_list_history.html')

def create_user_profile(request, encoded_email):
    print(request.method)
    if request.method == "POST":
        form = UserDetailsForm(request.POST)
        # decoded_email = force_str(urlsafe_base64_decode(encoded_email))
        # print("decoded email",decoded_email)
        # print("form email",form['email'].value())   
        print(f"Raw POST data: {request.POST}")  
        if form.is_valid():
            form.save()
            # return redirect('success_page')
            # print("its here")             
            return render(request, 'userprofile/userprofile.html', {'user': form, 'encoded_email': encoded_email})
        else:
            print(" its in else")
            logger.error(f"Form errors: {form.errors}")
            # Alternatively, you can use print to output errors to the console
            print(f"Form errors: {form.errors}")
            form = UserDetailsForm()
            messages.error(request, 'In Valid Information')
            return render(request, 'userprofile/editUserprofile.html', {'form': form, 'user': form, 'encoded_email': encoded_email})
    messages.error(request, 'In Valid Information')
    return render(request, 'userprofile/editUserprofile.html', {'form': form, 'user': form, 'encoded_email': encoded_email})

def redirect_edit(request, pk):    
    return render(request, 'userprofile/editUserprofile.html' , {'pk': pk})

def edit_user_profile(request, pk):
    user = get_object_or_404(UserDetails, pk=pk)
    if request.method == "POST":
        form = UserDetailsForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            encoded_email = urlsafe_base64_encode(force_bytes(form.cleaned_data.get('email')))
            return render(request, 'userprofile/userprofile.html', {'user': form, 'encoded_email' : encoded_email})
    else:
        form = UserDetailsForm(instance=user)
        logger.error(f"Form errors: {form.errors}")
        # Alternatively, you can use print to output errors to the console
        print(f"Form errors: {form.errors}")
        form = UserDetailsForm()
        messages.error(request, 'In Valid Information')
        return render(request, 'userprofile/editUserprofile.html', {'form': form , 'user': form})
    messages.error(request, 'In Valid Information')
    return render(request, 'userprofile/editUserprofile.html', {'form': form, 'user': form})

def profiles_list(request):
    users = UserDetails.objects.all()
    return render(request, 'profile_list.html', {'users': users})



def profile_details(request, encoded_email):
       print(encoded_email)
       email = force_str(urlsafe_base64_decode(encoded_email))
       if UserDetails.objects.filter(email = email).exists():
           print("its here")
           user = UserDetails.objects.get(email = email)
           return render(request, 'userprofile/userprofile.html', {'user': user})
       else:
           print("it is correct place")
           user = None
           print(user)
           return render(request, 'userprofile/editUserprofile.html', {'user_details': user, 'encoded_email': encoded_email})

def profile(request):
    uservalues =  request.session.get('uservalues', None)
    email = uservalues['email']
    encoded_email = urlsafe_base64_encode(force_bytes(email))
    return redirect(reverse('profile_details', kwargs={'encoded_email': encoded_email}))

