from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_http_methods, require_POST

from .admin_forms import UserCreateForm, UserDeleteForm, UserEditForm
from .models import CustomUser, UserAdministrationAudit
from .user_management import (
    create_encrypted_user, decrypt_identity, role_for, update_encrypted_user,
)


def _is_administrator(user):
    return user.is_authenticated and user.is_active and user.is_superuser


admin_required = user_passes_test(_is_administrator, login_url='login')


def _admin_count():
    return CustomUser.objects.filter(is_active=True, is_superuser=True).count()


@login_required
@admin_required
@cache_control(no_cache=True, no_store=True, must_revalidate=True)
def dashboard(request):
    users = []
    for user in CustomUser.objects.prefetch_related('groups').order_by('id'):
        username, email = decrypt_identity(user)
        users.append({'user': user, 'username': username, 'email': email, 'role': role_for(user)})
    return render(request, 'account_admin/dashboard.html', {
        'users': users,
        'active_count': sum(item['user'].is_active for item in users),
        'admin_count': sum(item['role'] == 'Administrator' for item in users),
        'audit_rows': UserAdministrationAudit.objects.select_related('actor', 'target')[:20],
    })


@login_required
@admin_required
@require_http_methods(['GET', 'POST'])
def create_user(request):
    form = UserCreateForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            user = create_encrypted_user(actor=request.user, **{
                key: form.cleaned_data[key]
                for key in ('username', 'email', 'password', 'role', 'is_active')
            })
        except ValueError as exc:
            form.add_error(None, str(exc))
        else:
            messages.success(request, f"User {form.cleaned_data['username']} was created.")
            return redirect('account_admin_edit', user_id=user.pk)
    return render(request, 'account_admin/user_form.html', {'form': form, 'mode': 'Create'})


@login_required
@admin_required
@require_http_methods(['GET', 'POST'])
def edit_user(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    username, email = decrypt_identity(user)
    initial = {'username': username, 'email': email, 'role': role_for(user), 'is_active': user.is_active}
    form = UserEditForm(request.POST or None, initial=initial)
    if request.method == 'POST' and form.is_valid():
        new_role, is_active = form.cleaned_data['role'], form.cleaned_data['is_active']
        if user == request.user and (new_role != 'Administrator' or not is_active):
            form.add_error(None, 'You cannot remove your own active Administrator access.')
        elif role_for(user) == 'Administrator' and (new_role != 'Administrator' or not is_active) and _admin_count() <= 1:
            form.add_error(None, 'The system must retain at least one active Administrator.')
        else:
            try:
                update_encrypted_user(
                    user=user, actor=request.user,
                    username=form.cleaned_data['username'], email=form.cleaned_data['email'],
                    role=new_role, is_active=is_active,
                    new_password=form.cleaned_data['new_password'],
                )
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"User {form.cleaned_data['username']} was updated.")
                return redirect('account_admin_dashboard')
    return render(request, 'account_admin/user_form.html', {
        'form': form, 'mode': 'Edit', 'managed_user': user, 'display_username': username,
    })


@login_required
@admin_required
@require_POST
def toggle_user(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    if user == request.user:
        return HttpResponseForbidden('You cannot deactivate your own account.')
    if user.is_superuser and user.is_active and _admin_count() <= 1:
        return HttpResponseForbidden('The last active Administrator cannot be deactivated.')
    user.is_active = not user.is_active
    user.save(update_fields=['is_active'])
    UserAdministrationAudit.objects.create(
        actor=request.user, target=user,
        action='activated' if user.is_active else 'deactivated', details={},
    )
    messages.success(request, 'The account status was updated.')
    return redirect('account_admin_dashboard')


@login_required
@admin_required
@require_http_methods(['GET', 'POST'])
def delete_user(request, user_id):
    user = get_object_or_404(CustomUser, pk=user_id)
    username, email = decrypt_identity(user)
    form = UserDeleteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if user == request.user:
            form.add_error(None, 'You cannot permanently delete your own account.')
        elif user.is_superuser and user.is_active and _admin_count() <= 1:
            form.add_error(None, 'The last active Administrator cannot be deleted.')
        elif not request.user.check_password(form.cleaned_data['admin_password']):
            form.add_error('admin_password', 'Your administrator password is incorrect.')
        else:
            target_id = user.pk
            with transaction.atomic():
                UserAdministrationAudit.objects.create(
                    actor=request.user, target=None, action='deleted',
                    details={'target_id': target_id, 'role': role_for(user)},
                )
                user.delete()
            messages.success(request, f'User {username} was permanently deleted.')
            return redirect('account_admin_dashboard')
    return render(request, 'account_admin/delete_confirm.html', {
        'form': form, 'managed_user': user, 'display_username': username, 'display_email': email,
    })
