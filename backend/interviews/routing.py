''' Interview WebSocket routes. '''

from django.urls import re_path

from interviews.consumers import InterviewConsumer

websocket_urlpatterns = [
    re_path(r'ws/interviews/(?P<interview_id>[0-9a-f-]+)/$', InterviewConsumer.as_asgi())
]
