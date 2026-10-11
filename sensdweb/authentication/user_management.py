import json
import uuid

from django.contrib.auth.models import Group
from django.db import transaction

from .admin_forms import ROLE_CHOICES
from .models import CustomUser, UserAdministrationAudit, UserKey
from .utils import decrypt_data, encrypt_data


ROLE_NAMES = tuple(value for value, _ in ROLE_CHOICES)


def decrypt_identity(user):
    try:
        key = UserKey.objects.get(user=user)
        return (
            decrypt_data(key.private_key, json.loads(user.username)),
            decrypt_data(key.private_key, json.loads(user.email)),
        )
    except (UserKey.DoesNotExist, TypeError, ValueError, json.JSONDecodeError, KeyError):
        return str(user.username or ''), str(user.email or '')


def find_identity_conflict(username, email, exclude_user=None):
    username, email = username.casefold(), email.casefold()
    for candidate in CustomUser.objects.all():
        if exclude_user and candidate.pk == exclude_user.pk:
            continue
        candidate_username, candidate_email = decrypt_identity(candidate)
        if candidate_username.casefold() == username:
            return 'username'
        if candidate_email.casefold() == email:
            return 'email'
    return None


def ensure_roles():
    return {name: Group.objects.get_or_create(name=name)[0] for name in ROLE_NAMES}


def role_for(user):
    if user.is_superuser:
        return 'Administrator'
    role = user.groups.filter(name__in=ROLE_NAMES).values_list('name', flat=True).first()
    return role or ('Manager' if user.is_staff else 'Viewer')


def assign_role(user, role):
    groups = ensure_roles()
    user.groups.remove(*groups.values())
    user.groups.add(groups[role])
    user.is_superuser = role == 'Administrator'
    user.is_staff = role in {'Administrator', 'Manager'}
    user.save(update_fields=['is_superuser', 'is_staff'])


@transaction.atomic
def create_encrypted_user(*, username, email, password, role, is_active, actor):
    conflict = find_identity_conflict(username, email)
    if conflict:
        raise ValueError(f'A user with this {conflict} already exists.')
    token = uuid.uuid4().hex
    user = CustomUser.objects.create_user(
        username=f'pending-{token}', email=f'{token}@pending.invalid', password=password,
        is_active=is_active,
    )
    public_key, private_key = UserKey.generate_key_pair()
    UserKey.objects.create(user=user, public_key=public_key, private_key=private_key)
    user.username = json.dumps(encrypt_data(public_key, username))
    user.email = json.dumps(encrypt_data(public_key, email))
    user.save(update_fields=['username', 'email'])
    assign_role(user, role)
    UserAdministrationAudit.objects.create(actor=actor, target=user, action='created', details={'role': role})
    return user


@transaction.atomic
def update_encrypted_user(*, user, username, email, role, is_active, new_password, actor):
    conflict = find_identity_conflict(username, email, exclude_user=user)
    if conflict:
        raise ValueError(f'A user with this {conflict} already exists.')
    key = UserKey.objects.get(user=user)
    user.username = json.dumps(encrypt_data(key.public_key, username))
    user.email = json.dumps(encrypt_data(key.public_key, email))
    user.is_active = is_active
    if new_password:
        user.set_password(new_password)
    user.save()
    assign_role(user, role)
    UserAdministrationAudit.objects.create(
        actor=actor, target=user, action='updated', details={'role': role, 'is_active': is_active},
    )
