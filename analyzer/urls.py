from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    
    # Authentication
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    
    # Blood Report Flow
    path('upload/', views.upload_report, name='upload_report'),
    path('allergy/<int:report_id>/', views.allergy_info, name='allergy_info'),
    path('recommendations/<int:report_id>/', views.generate_recommendations, name='generate_recommendations'),
    path('reports/', views.report_list, name='report_list'),

    # Progress Tracker
    path('progress/<int:report_id>/', views.progress_tracker, name='progress_tracker'),
    path('progress/history/<int:report_id>/', views.progress_history, name='progress_history'),

    # PDF Download
    path('download-pdf/<int:report_id>/', views.download_pdf_report, name='download_pdf_report'),
]
