from django.shortcuts import render
from django.shortcuts import redirect
from django.views import View
import json
from django.http import JsonResponse
# from django.contrib.auth.models import User

from .models import CustomUser as User
from validate_email import validate_email
from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.mail import send_mail



from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.urls import reverse
from django.utils.encoding import force_bytes , DjangoUnicodeDecodeError , force_str
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

from django.contrib import auth

from .utils import token_generator, encode_email , decode_email


from .models import UserKey
from .utils import encrypt_data, decrypt_data
from django.core.exceptions import FieldError

from django.contrib.auth import get_user_model
User = get_user_model()

import json

# Create your views here.

# ----------------------------
# Helpers to work with encrypted / legacy rows
# ----------------------------

def _norm(s):
    return (s or "").strip().casefold()

def _maybe_decrypt_field(user, field_name):
    """
    Returns a plaintext value for user.<field_name> handling three cases:
    1) Plain text (normal or django-cryptography auto-decrypted) -> return as-is
    2) Legacy JSON/ECC saved value -> decrypt via UserKey + decrypt_data
    3) Any error -> raise to caller
    """
    raw = getattr(user, field_name, None)

    # If django-cryptography field, simply accessing returns plaintext already.
    # If it *was* JSON/ECC previously saved, it likely looks like a JSON string.
    if isinstance(raw, str) and (raw.startswith('[') or raw.startswith('{')):
        # Legacy ECC JSON
        uk = UserKey.objects.filter(user=user).first()
        if not uk:
            raise ValueError("No keypair for legacy-encrypted row")
        return decrypt_data(uk.private_key, json.loads(raw))
    return raw

def _safe_exists(field_name: str, value: str) -> bool:
    """
    Try a DB lookup first; if the field is EncryptedTextField (FieldError),
    fall back to a decrypt-scan to avoid crashing.
    """
    try:
        return User.objects.filter(**{f"{field_name}__iexact": value}).exists()
    except FieldError:
        valn = _norm(value)
        # Only fetch columns we need; avoid loading other encrypted columns
        for u in User.objects.only("id", field_name).iterator():
            try:
                clear = _maybe_decrypt_field(u, field_name)
                if _norm(clear) == valn:
                    return True
            except Exception:
                continue
        return False

def _safe_get_by(field_name: str, value: str):
    """
    Get one user by field, with same fallback. Returns User or None.
    """
    try:
        return User.objects.get(**{f"{field_name}__iexact": value})
    except FieldError:
        valn = _norm(value)
        for u in User.objects.only("id", field_name, "password", "is_active").iterator():
            try:
                clear = _maybe_decrypt_field(u, field_name)
                if _norm(clear) == valn:
                    return u
            except Exception:
                continue
        return None
    except User.MultipleObjectsReturned:
        return User.objects.filter(**{f"{field_name}__iexact": value}).first()
    except User.DoesNotExist:
        return None

def _scheme(request):
    # Build links that work both locally and behind a proxy
    if request.is_secure():
        return "https://"
    # Respect proxy header if you set SECURE_PROXY_SSL_HEADER
    if request.META.get("HTTP_X_FORWARDED_PROTO") == "https":
        return "https://"
    return "http://"


# ----------------------------
# Username & Email Validators
# ----------------------------

class UsernameValidationView(View):  # this view is for validating usernames
    def post(self, request):
        data=json.loads(request.body)
        username= data['username']

        if not str(username).isalnum():
            return JsonResponse({'username_error':'Username should only contain alphanumeric characters'},status=400)
        # Using DB lookup not full Scan 
        if _safe_exists('username', username):
            messages.error(request, 'Email already exists, choose another one')
            return JsonResponse({'username_error': 'Username already exists, choose another one'}, status=409)
        
        return JsonResponse({'username_valid': True}, status=200)

class EmailValidationView(View):  # this view is for validating emails
    def post(self, request):
        data=json.loads(request.body)
        email = data['email']

        if not validate_email(email):
            return JsonResponse({'email_error':'Email is Invalid'},status=400)
        if _safe_exists('email', email):
            messages.error(request, 'Email already exists, choose another one')
            return JsonResponse({'email_error':'Email already exists, choose another one'},status=409)
        return JsonResponse({'email_valid': True})
    
class RegistrationView(View):
    def get(self, request):
        return render(request, 'authentication/register.html')

    def post(self, request):

        #Get User Data
        #validate 
        #create user account
        username = request.POST['username']
        email = request.POST['email']
        password = request.POST['password']
        print("User Registration Data:")
        print("Username:", username)
        print("Email:", email)
        print("Password:", password)
        context = {
            'feildValues' : request.POST
        }
        # Basic validations
        if not username or not email or not password:
            messages.error(request, 'All fields are required.')
            return render(request, 'authentication/register.html', context)

        if len(password) < 6:
            messages.error(request, 'Password too short (min 6).')
            return render(request, 'authentication/register.html', context)

        if _safe_exists('username', username):
            messages.error(request, 'Username already exists, choose another one')
            return render(request, 'authentication/register.html', context)

        if _safe_exists('email', email):
            messages.error(request, 'Email already exists, choose another one')
            return render(request, 'authentication/register.html', context)

        user = User.objects.create_user(username=username, email=email, password=password,
            is_active=False)
        user.save()

        # Generate key pair for the user
        if not UserKey.objects.filter(user=user).exists():
            # Generate ECC key pair
            public_key, private_key = UserKey.generate_key_pair()
            UserKey.objects.create(user=user, public_key=public_key, private_key=private_key)
        else:
            user_key = UserKey.objects.get(user=user)
            public_key = user_key.public_key
            private_key = user_key.private_key
        
       
        # encrypted_username = encrypt_data(public_key, user.username)
        # encrypted_email = encrypt_data(public_key, user.email)

        # user.username = json.dumps(encrypted_username)
        # user.email = json.dumps(encrypted_email)
    
        # user.save()

        encrypted_username = json.dumps(encrypt_data(public_key, username))
        encrypted_email = json.dumps(encrypt_data(public_key, email))
        encrypted_password = json.dumps(encrypt_data(public_key, password))

        user.username = encrypted_username
        user.email = encrypted_email
        user.password = encrypted_password
        user.save()
        #path_to_view
        # -getting domain we are on
        # -relative url to verification
        # -encode UID
        # -encode token
        uidb64 = urlsafe_base64_encode(force_bytes(user.pk))

        # Encrypt email before sending it in the email
        # encrypted_email = encrypt_data(public_key, email)

        domain = get_current_site(request).domain
        link = reverse('activate', kwargs={'uidb64': uidb64, 'token': token_generator.make_token(user)})

        email_contents = {
            'user': user,
            'domain': domain,
            'uid': urlsafe_base64_encode(force_bytes(user.pk)),
            'token': token_generator.make_token(user),
        }
        # code_username = decrypt_data(private_key, encrypted_username)
        # code_email = decrypt_data(private_key, encrypted_email)              
        link = reverse('activate', kwargs={'uidb64': email_contents['uid'], 'token': email_contents['token']})
        email_subject = "Activate your Account"
        activate_url = 'https://'+domain+link
        confirmation_mail = EmailMessage(
            email_subject,
            'Hi '+ username + ', Please the link below to activate your account \n'+activate_url,
            "noreply@example.com",
            [email],
        )
        confirmation_mail.send(fail_silently=False)
        messages.success(request, 'Account created successfully')

        return render(request, 'authentication/register.html', context)
    
# ----------------------------
# Verification View
# ----------------------------
        

class VerficationView(View):
    def get(self, request, uidb64, token):
        print("self", self)
        print("uidb64", uidb64)
        print("token", token)
        try:
            id = force_str(urlsafe_base64_decode(uidb64))
            print("id", id)
            user = User.objects.only('id', 'is_active').get(pk=id)
            
            if not token_generator.check_token(user, token):
                return redirect('login'+'?message='+'User already activated')
            if user.is_active:
                return redirect('login')
            user.is_active = True
            user.save()

            messages.success(request, 'Account activated succesfully')
            return redirect('login')
        except Exception as ex:
            print('Error in activation:', ex)
            print(ex)
            messages.error(request, 'Activation link is invalid or expired.')
            return redirect('login')
        
        


# class LoginView(View):
#     def get(self, request):
#         return render(request, 'authentication/login.html')
    
#     def post(self, request):
#         username = request.POST['username']
#         password = request.POST['password']

#         context = {
#             "uservalues" : request.POST
#         }

#         if not username or not password:
#             messages.error(request, 'Fill in both username and password.')
#             return render(request, 'authentication/login.html', context)
        
#         matched_user = None
#         decrypted_email = None

#         if username and password:
           
#            user=auth.authenticate(username=username, password=password)
#            if user:
#                # Retrieve the user's private key
#                 user_key = UserKey.objects.get(user=user)
#                 private_key = user_key.private_key

#                 # Decrypt email for validation
#                 decrypted_email = decrypt_data(private_key, user.email)
               
#                 if user.username == 'admin':
#                     request.session['uservalues'] = {
#                             'pk':user.pk,
#                             'username': user.username,
#                             'email': user.email,
#                             'isactive': user.is_active,
#                             # Add other user details you want to save
#                     }
#                     auth.login(request, user)
#                     messages.success(request, 'Welcome, ' + user.username + '!')
#                     return redirect('sensdadmin') 

#            if user:
#                if user.is_active:
#                    auth.login(request, user)
#                    request.session['uservalues'] = {
#                         'pk':user.pk,
#                         'username': user.username,
#                         'email': user.email,
#                         'isactive': user.is_active,
#                         # Add other user details you want to save
#                   }
#                    messages.success(request, 'Welcome, ' + user.username + '!')
#                    return redirect('sensd')
               
#                messages.error(request,'Account is not active, please check the mail')
#                return render(request, 'authentication/login.html')
           
#            messages.error(request, 'Invalid credentials, try again')
#            return render(request, 'authentication/login.html')

#         messages.error(request, 'Fill the login Details')
#         return render(request, 'authentication/login.html')

# ----------------------------
# Login / Logout
# ----------------------------

class LoginView(View):
    def get(self, request):
        return render(request, 'authentication/login.html')
    
    def post(self, request):
        input_username = request.POST.get('username')
        input_password = request.POST.get('password')

        print("input_username", input_username)
        print("input_password", input_password)

        context = {
            "uservalues": request.POST
        }

        if not input_username or not input_password:
            messages.error(request, 'Please fill in both username and password.')
            return render(request, 'authentication/login.html', context)

        matched_user = None
        decrypted_email = None

        for user in User.objects.all():
            try:
                user_key = UserKey.objects.get(user=user)
                clear_username = decrypt_data(user_key.private_key, json.loads(user.username))
                clear_password = decrypt_data(user_key.private_key, json.loads(user.password))
                if _norm(clear_username) == _norm(input_username) and clear_password == input_password:
                    matched_user = user
                    break
            except Exception:
                continue

        if matched_user is None:
            messages.error(request, 'Invalid credentials, try again.')
            return render(request, 'authentication/login.html', context)

        if not matched_user.is_active:
            messages.error(request, 'Account is not active, please check your email.')
            return render(request, 'authentication/login.html', context)

        auth.login(request, matched_user)
        # Decrypt email for session
        user_key = UserKey.objects.get(user=matched_user)
        clear_email = decrypt_data(user_key.private_key, json.loads(matched_user.email))
        request.session['uservalues'] = {
            'pk': matched_user.pk,
            'username': input_username,
            'email': clear_email,
            'isactive': matched_user.is_active,
        }

        messages.success(request, f'Welcome, {input_username}!')
        return redirect('sensdadmin' if input_username == 'admin' else 'gis-home')


class LogoutView(View):
    def get(self, request):
        auth.logout(request)
        messages.success(request, 'Logged out successfully')
        return redirect('login')
    def post(self, request):
        auth.logout(request)
        messages.success(request, 'Logged out successfully')
        return redirect('login')
    
class RequestPasswordResetEmail(View):

    def get(self, request):
        return render( request, 'authentication/reset-password.html') 
    
    def post(self, request):

        email = request.POST['email']

        context = {
            'values': request.POST
        }

        if not validate_email(email):
            messages.error(request, 'Email is not valid')
            return render(request, 'authentication/reset-password.html', context)
        
        
        domain = get_current_site(request).domain
                # link = reverse('activate', kwargs={'uidb64': uidb64, 'token': token_generator.make_token(user)})
        user = User.objects.filter(email = email)
        if user.exists():
            email_contents = {
            'user': user[0],
            'domain': domain,
            'uid': urlsafe_base64_encode(force_bytes(user[0].pk)),
            'token': PasswordResetTokenGenerator().make_token(user[0]),
            }

            link = reverse('reset-user-password', kwargs={'uidb64': email_contents['uid'], 'token': email_contents['token']})
            email_subject = "Password reset Instructions"
            reset_url = 'http://'+domain+link
            confirmation_mail = EmailMessage(
                email_subject,
                'Hi, Please click the link below to reset your password \n'+ reset_url,
                "noreply@semycolon.com",
                [email],
            )
            confirmation_mail.send(fail_silently=False) 
            messages.success(request, 'We have sent a email to' + email + 'to reset password')
           
            pass

        
        messages.info(request, 'You can reset your passowrd')
        
        return render( request, 'authentication/reset-password.html') 
    


class CompletePasswordReset(View):
    def get(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }
        return render(request, 'authentication/set-newpassword.html', context)
    
    def post(self, request, uidb64, token):
        context = {
            'uidb64': uidb64,
            'token': token
        }

        password = request.POST['password']
        password1 = request.POST['passwordrepeat']


        if password != password1:
            messages.error(request, 'Password does not match')
            return render(request, 'authentication/set-newpassword.html')
        
        if len(password) < 6:
            messages.error(request, 'Password must be at least 6 characters')
            return render(request, 'authentication/set-newpassword.html')
        
        try:
            user_id = force_str(urlsafe_base64_decode(uidb64))

            user = User.objects.get(pk=user_id)
            user.set_password(password)
            user.save()

            messages.success(request, 'Password changed Sucessfully!!')
            return redirect('login')
            pass
        except Exception as identifier:
            messages.error(request, 'Invalid link' + identifier)
            return render(request, 'authentication/set-newpassword.html')
            pass
            
    









