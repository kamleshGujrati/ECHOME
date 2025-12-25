from django.urls import path, include
from ECHOME import views

urlpatterns = [

    path('', views.homepage, name="homepage"),
    path('form/', views.formpage, name="formpage"),
    path('accounts/', include('accounts.urls')),
    path("process_secure_upload/", views.process_secure_upload, name="process_secure_upload"),
    path("delete_time_capsule/<int:id>/", views.delete_time_capsule, name="delete_time_capsule"),
    path("dashboard/", views.dashboard, name="dashboard"),
    # path("time_capsules", views.total_capsules_api, name="time_capsule_detail"),
]
