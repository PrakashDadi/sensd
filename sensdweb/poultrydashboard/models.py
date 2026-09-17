from django.conf import settings
from django.db import models
from encrypted_fields.fields import EncryptedCharField, EncryptedEmailField, EncryptedTextField

from .fields import EncryptedJSONField


class OwnedModel(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        abstract = True


class PoultryProfile(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="poultry_profile",
    )
    first_name = EncryptedCharField(max_length=120, blank=True, null=True)
    last_name = EncryptedCharField(max_length=120, blank=True, null=True)
    email = EncryptedEmailField(blank=True, null=True)
    photo_data_url = EncryptedTextField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Poultry profile {self.pk}"


class PoultryCredential(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="poultry_credential",
    )
    username = EncryptedCharField(max_length=255)
    password = EncryptedTextField()
    is_demo = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"BluConsole credential {self.pk}"


class Note(OwnedModel):
    title = EncryptedCharField(max_length=200)
    body = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)


class UploadDataset(OwnedModel):
    name = EncryptedCharField(max_length=255)
    headers = EncryptedJSONField(default=list)
    rows = EncryptedJSONField(default=list)
    row_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class ChatSession(OwnedModel):
    title = EncryptedCharField(max_length=200, default="New chat")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20)
    content = EncryptedTextField()
    created_at = models.DateTimeField(auto_now_add=True)


class ChatAttachment(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="attachments")
    name = EncryptedCharField(max_length=255)
    mime = EncryptedCharField(max_length=120, blank=True)
    summary = EncryptedJSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
