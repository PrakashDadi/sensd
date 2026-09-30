from django import forms
from django.core.exceptions import ValidationError
from .models import UserDetails, UserProfile

class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = UserDetails
        fields = ['firstname', 'lastname', 'email', 'phonenumber', 'address', 'city', 'state', 'pincode']


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['first_name', 'last_name', 'phone', 'address', 'city', 'state', 'postal_code', 'photo_data_url']
        widgets = {
            'address': forms.TextInput(),
            'photo_data_url': forms.HiddenInput(),
        }

    def clean_photo_data_url(self):
        value = self.cleaned_data.get('photo_data_url') or ''
        if not value:
            return ''
        allowed = ('data:image/jpeg;base64,', 'data:image/png;base64,', 'data:image/webp;base64,')
        if not value.startswith(allowed):
            raise ValidationError('Choose a JPG, PNG, or WebP image.')
        if len(value) > 2_800_000:
            raise ValidationError('Choose an image smaller than 2 MB.')
        return value
