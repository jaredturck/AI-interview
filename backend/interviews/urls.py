''' Interview HTTP routes. '''

from django.urls import path

from interviews import views

urlpatterns = [
    path('bootstrap/', views.bootstrap, name='bootstrap'),
    path('interviews/start/', views.start_interview, name='start_interview'),
    path('interviews/<uuid:interview_id>/status/', views.interview_status, name='interview_status'),
    path('interviews/<uuid:interview_id>/review/', views.request_review, name='request_review')
]
