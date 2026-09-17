from django.contrib import admin

from .models import ChatAttachment, ChatMessage, ChatSession, Note, PoultryProfile, UploadDataset


admin.site.register([PoultryProfile, Note, UploadDataset, ChatSession, ChatMessage, ChatAttachment])
