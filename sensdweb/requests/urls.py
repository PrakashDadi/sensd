from django.urls import path
from django.views.decorators.csrf import csrf_exempt
from . import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
      path('user_requests/', views.user_requests, name='user_requests'),
      path('upload_excel/', views.uploadexcel, name='upload_excel'),
      path('upload_excel/view_exceldata', views.viewexceldata, name='view_exceldata'),
      path('upload_excel/optimize_model', views.optimize_model, name='optimize_model'),
      path('new_request/<str:requestid>/generate_excel', views.generate_excel, name='generate_excel'),
      path('new_request', views.newRequest, name='new_request'),
      path('new_request/<str:requestid>/AllNodes', views.allNodes, name='AllNodes'), 
      path('new_request/<str:requestid>/InitialNodes', views.initialNodes, name='InitialNodes'), 
      path('new_request/<str:requestid>/FinishedGoods', views.finishedGoods, name='FinishedGoods'), 
      path('new_request/<str:requestid>/ARCForm', views.arcform, name='ARCForm'), 
      path('new_request/<str:requestid>/PTMForm', views.pathtestmethodform, name='PTMForm'), 
      path('new_request/<str:requestid>/PTMFNodesForm', views.pathtestmethodFnodesform, name='PTMFNodesForm'), 
      path('node/<int:pk>/<str:requestid>/edit/', views.edit_allnode, name='edit_allnode'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
