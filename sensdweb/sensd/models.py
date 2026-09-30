from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from encrypted_fields.fields import EncryptedCharField, EncryptedTextField


class UserDetails(models.Model):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User'),
        ('guest', 'Guest'),
        # Add more roles as needed
    )
    # user = models.OneToOneField(User, on_delete=models.CASCADE)
    firstname = models.CharField(max_length=30)
    lastname = models.CharField(max_length=30)
    fullname = models.CharField(max_length=60)
    email = models.EmailField(unique=True)
    phonenumber = models.CharField(max_length=15)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)

    def save(self, *args, **kwargs):
        self.fullname = f"{self.firstname} {self.lastname}"
        self.role = 'User'
        super(UserDetails, self).save(*args, **kwargs)

    def __str__(self):
        return self.fullname


class UserProfile(models.Model):
    """The single application-wide profile for an authenticated SENSD user."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    first_name = EncryptedCharField(max_length=150, blank=True, null=True)
    last_name = EncryptedCharField(max_length=150, blank=True, null=True)
    phone = EncryptedCharField(max_length=30, blank=True, null=True)
    address = EncryptedCharField(max_length=255, blank=True, null=True)
    city = EncryptedCharField(max_length=100, blank=True, null=True)
    state = EncryptedCharField(max_length=100, blank=True, null=True)
    postal_code = EncryptedCharField(max_length=20, blank=True, null=True)
    photo_data_url = EncryptedTextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile for {self.user}"
