import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ai_interviewer.settings")

django_asgi_app = get_asgi_application()

from ai_interviewer.runtime_config import RUNTIME
from interviews.routing import websocket_urlpatterns
from interviews.services.runtime import model_runtime

if RUNTIME["models"]["mode"] == "real":
    model_runtime.suite.load_live()

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(URLRouter(websocket_urlpatterns)),
})
