from django.contrib.auth.tokens import PasswordResetTokenGenerator
from six import text_type
import base64
import json

from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import os


class AppTokenGenerator(PasswordResetTokenGenerator):
    def _make_hash_value(self, user, timestamp):
        return (text_type(user.is_active) + text_type(user.pk) + text_type(timestamp))


token_generator = AppTokenGenerator()


def encode_email(email):
    return urlsafe_base64_encode(email.encode()).decode()


def decode_email(encoded_email):
    return urlsafe_base64_decode(encoded_email.encode()).decode()


def encrypt_data(public_key_pem, plaintext):
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode('utf-8'), backend=default_backend()
    )

    ephemeral_private_key = ec.generate_private_key(ec.SECP256R1())
    shared_key = ephemeral_private_key.exchange(ec.ECDH(), public_key)

    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
        backend=default_backend()
    ).derive(shared_key)

    iv = os.urandom(12)
    cipher = Cipher(algorithms.AES(derived_key), modes.GCM(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(plaintext.encode('utf-8')) + encryptor.finalize()

    ephemeral_public_key_bytes = ephemeral_private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    encrypted_package = {
        'ciphertext': base64.b64encode(ciphertext).decode('utf-8'),
        'iv': base64.b64encode(iv).decode('utf-8'),
        'tag': base64.b64encode(encryptor.tag).decode('utf-8'),
        'ephemeral_public_key': base64.b64encode(ephemeral_public_key_bytes).decode('utf-8')
    }

    return encrypted_package


def decrypt_data(private_key_pem, encrypted_data):
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode('utf-8'), password=None, backend=default_backend()
    )

    ciphertext = base64.b64decode(encrypted_data['ciphertext'])
    iv = base64.b64decode(encrypted_data['iv'])
    tag = base64.b64decode(encrypted_data['tag'])
    ephemeral_public_key_bytes = base64.b64decode(encrypted_data['ephemeral_public_key'])

    ephemeral_public_key = serialization.load_pem_public_key(
        ephemeral_public_key_bytes, backend=default_backend()
    )

    shared_key = private_key.exchange(ec.ECDH(), ephemeral_public_key)

    derived_key = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,
        info=b'handshake data',
        backend=default_backend()
    ).derive(shared_key)

    cipher = Cipher(algorithms.AES(derived_key), modes.GCM(iv, tag), backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ciphertext) + decryptor.finalize()

    return plaintext.decode('utf-8')
