from django.urls import path
from . import views

urlpatterns = [
    path("isdrequests/", views.home, name="isdrequests_home"),
    path("isdrequests/preview/", views.preview_excel, name="preview_excel"),
    path("isdrequests/save/", views.save_excel, name="save_excel"),
    path("isdrequests/optimize/", views.run_optimization, name="run_isdoptimization"),
    path("isdrequests/requests/", views.requests_list, name="requests_list"),
    # path("/isdrequests/requests/<int:req_id>/", views.request_detail, name="request_detail"),
    # path("/isdrequests/requests/<int:req_id>/delete/", views.delete_request, name="delete_request"),
    # path("/isdrequests/requests/<int:req_id>/edit/", views.edit_request, name="edit_request"),
    path("isdrequests/results/<int:req_id>/", views.results_view, name="results_view"),
    # urls.py
    path("requests/<int:req_id>/results/download/", views.results_download_excel, name="results_download_excel"),

]
