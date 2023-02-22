import json
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.generic.websocket import WebsocketConsumer
from .models import Order

class OrderConsumer(WebsocketConsumer):
    def connect(self):
        self.room_name = 'orders'
        self.room_group_name = 'orders'
        async_to_sync(self.channel_layer.group_add)(
            self.room_group_name,
            self.channel_name
        )
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)(
            self.room_group_name,
            self.channel_name
        )

    def receive(self, text_data):
        await self.send_latest_orders()

    def order_created(self, event):
        orders = await database_sync_to_async(Order.objects.order_by('-ordered_date')[:10])()
        message = [{
            'type': 'order_created',
            'id': order.id,
            'user':{
                'first_name': order.user.first_name,
                'last_name': order.user.last_name,
            },
            'items': [item.item_name for item in order.items.all()],
            'start_date': order.start_date.strftime('%Y-%m-%d %H:%M:%S'),
            'ordered_date': order.ordered_date.strftime('%Y-%m-%d %H:%M:%S') if order.ordered_date else '',
            'ordered': order.ordered,
            'checkout_address': {
                'street': order.checkout_address.street_address,
                'apartment': order.checkout_address.apartment_address,
                'country': order.checkout_address.country,
                'zip': order.checkout_address.zip,
                'phone': order.checkout_address.phone,
            } if order.checkout_address else '',
            'payment': {
                'transaction_id': order.payment.transaction_id,
                'amount': order.payment.amount,
            } if order.payment else '',
        } for order in orders]
        await self.send(text_data=json.dumps(message))
