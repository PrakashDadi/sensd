from django.db import models
from django.contrib.auth.models import User

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
