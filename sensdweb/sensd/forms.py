from django import forms
from .models import UserDetails

class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = UserDetails
        fields = ['firstname', 'lastname', 'email', 'phonenumber', 'address', 'city', 'state', 'pincode']
