#creating Userprofile for Individual 

from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20)
    address = models.TextField()
    role = models.CharField(max_length=20, choices=[
        ('admin', 'Admin'),
        ('moderator', 'Moderator'),
        ('user', 'User')
    ])

    def __str__(self):
        return f"{self.first_name} {self.last_name}"