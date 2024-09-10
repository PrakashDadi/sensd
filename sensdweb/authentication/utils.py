from django.contrib.auth.tokens import PasswordResetTokenGenerator
from six import text_type
import base64
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode



class AppTokenGenerator(PasswordResetTokenGenerator):
      def _make_hash_value(self, user, timestamp):
            return (text_type(user.is_active)+text_type(user.pk)+text_type(timestamp))
      


token_generator = AppTokenGenerator()

def encode_email(email):
    return urlsafe_base64_encode(email.encode()).decode()

def decode_email(encoded_email):
    return urlsafe_base64_decode(encoded_email.encode()).decode()