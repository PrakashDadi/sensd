from django.urls import path

from . import admin_views


urlpatterns = [
    path('', admin_views.dashboard, name='account_admin_dashboard'),
    path('users/new/', admin_views.create_user, name='account_admin_create'),
    path('users/<int:user_id>/edit/', admin_views.edit_user, name='account_admin_edit'),
    path('users/<int:user_id>/toggle/', admin_views.toggle_user, name='account_admin_toggle'),
    path('users/<int:user_id>/delete/', admin_views.delete_user, name='account_admin_delete'),
]
