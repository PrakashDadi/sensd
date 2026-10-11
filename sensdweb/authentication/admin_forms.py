from django import forms


ROLE_CHOICES = (
    ('Administrator', 'Administrator'),
    ('Manager', 'Manager'),
    ('Analyst', 'Analyst'),
    ('Viewer', 'Viewer'),
)


class StyledFormMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            css_class = 'form-check-input' if isinstance(field.widget, forms.CheckboxInput) else 'form-control'
            field.widget.attrs.setdefault('class', css_class)


class UserCreateForm(StyledFormMixin, forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(min_length=8, widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    is_active = forms.BooleanField(required=False, initial=True)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get('password') != cleaned.get('password_confirm'):
            self.add_error('password_confirm', 'Passwords do not match.')
        return cleaned


class UserEditForm(StyledFormMixin, forms.Form):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    role = forms.ChoiceField(choices=ROLE_CHOICES)
    is_active = forms.BooleanField(required=False)
    new_password = forms.CharField(required=False, min_length=8, widget=forms.PasswordInput)


class UserDeleteForm(StyledFormMixin, forms.Form):
    confirmation = forms.CharField(help_text='Type DELETE to confirm.')
    admin_password = forms.CharField(widget=forms.PasswordInput)

    def clean_confirmation(self):
        value = self.cleaned_data['confirmation'].strip()
        if value != 'DELETE':
            raise forms.ValidationError('Type DELETE exactly to confirm permanent deletion.')
        return value
