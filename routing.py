from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from core import consumers

application = ProtocolTypeRouter({
    'websocket': URLRouter([
        path('ws/orders/', consumers.OrderConsumer.as_asgi()),
    ]),
})
