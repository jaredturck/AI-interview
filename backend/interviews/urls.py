''' Map candidate authentication, jobs, applications, interviews, status and review API paths to Django views. '''

from django.urls import path

from interviews import views

urlpatterns = [
    path('auth/status/', views.auth_status, name='auth_status'),
    path('auth/signup/', views.signup, name='signup'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('account/', views.account, name='account'),
    path('bootstrap/', views.bootstrap, name='bootstrap'),
    path('jobs/', views.jobs, name='jobs'),
    path('jobs/<uuid:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<uuid:job_id>/apply/', views.apply_job, name='apply_job'),
    path('applications/<uuid:application_id>/', views.application_detail, name='application_detail'),
    path('applications/<uuid:application_id>/interview/start/', views.start_application_interview, name='start_application_interview'),
    path('interviews/<uuid:interview_id>/status/', views.interview_status, name='interview_status'),
    path('interviews/<uuid:interview_id>/review/', views.request_review, name='request_review')
]
