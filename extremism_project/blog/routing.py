from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path('ws/<int:customer_id>/<int:specialist_id>/', consumers.ChatConsumer.as_asgi()),
]