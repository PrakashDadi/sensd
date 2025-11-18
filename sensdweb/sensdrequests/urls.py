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
      path('new_request/<str:requestid>/DynamicParameterForm', views.dynamicparametersform, name='DynamicParameterForm'),
      path('allNode/<int:pk>/<str:requestid>/edit/', views.edit_allnode, name='edit_allnode'),
      path('initialNode/<int:pk>/<str:requestid>/edit_initialnode/', views.edit_initialNodes, name='edit_initialnode'),
      path('finishedGoods/<int:pk>/<str:requestid>/edit_finishedGoods/', views.edit_finishedGoods, name='edit_finishedgood'),
      path('arcs/<int:pk>/<str:requestid>/edit_arcs/', views.edit_arcform, name='edit_arc'),
      path('ptmform/<int:pk>/<str:requestid>/edit_ptmform/', views.edit_pathtestmethodform, name='edit_ptmform'),
      path('ptmfnodesform/<int:pk>/<str:requestid>/edit_ptmfn' , views.edit_pathtestmethodFnodesform, name='edit_ptmfnodesform'),
      path('delete_request/<str:requestid>/', views.delete_request, name='delete_request'),
      path('results/<str:result_id>/', views.view_results, name='view_results'),
      path('save-excel-data/', views.save_excel_data, name='save_excel_data'),
      path('requests/optimize_db/<str:requestid>/', views.run_optimization_from_db, name='run_optimization_from_db'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
