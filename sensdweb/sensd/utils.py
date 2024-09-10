import base64
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode

def encode_email(email):
    return urlsafe_base64_encode(email.encode()).decode()

def decode_email(encoded_email):
    return urlsafe_base64_decode(encoded_email.encode()).decode()