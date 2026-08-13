''' Map authenticated interview WebSockets to the Django Channels consumer. '''

from django.urls import path

from interviews.consumers import InterviewConsumer

websocket_urlpatterns = [
    path('ws/interviews/<uuid:interview_id>/', InterviewConsumer.as_asgi())
]
