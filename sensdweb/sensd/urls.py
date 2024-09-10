
from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('sensd/', views.home, name='sensd'),
    path('addusers/', views.add_user, name='adduser'), 
    path('sensdadmin/', views.adminindex, name='sensdadmin'), 
    path('authentication/', include('authentication.urls')),
    path('sensd/new_request', views.add_user_request, name="new_user_request"),
    path('sensd/request_history', views.request_history, name="request_list_history"),
    path('sensd/profile', views.profile, name="profile"),
    path('sensd/profile/<str:encoded_email>/', views.profile_details, name="profile_details"),
    path('sensd/profile/create_profile/<str:encoded_email>/', views.create_user_profile, name="create_profile"),
    path('sensd/profile/edit_profile/<int:pk>/', views.edit_user_profile, name="edit_profile"),
    path('sensd/profile/redirect_edit_profile/<int:pk>/', views.redirect_edit, name="edit_profile_redirect")
]
