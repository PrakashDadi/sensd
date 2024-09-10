from django.shortcuts import render, redirect , get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import cache_control
from django.views import View
import json
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.contrib import messages
from .models import UserDetails
from .forms import UserDetailsForm

from django.utils.encoding import force_bytes , DjangoUnicodeDecodeError , force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.urls import reverse

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
    return render(request, 'dashboard/index.html')

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

