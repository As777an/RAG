from datetime import datetime
import json

from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from blog.models import RoomMessage

from users.models import User

# Create a consumer class
class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.customer = self.scope['url_route']['kwargs']['customer_id']
        self.specialist = self.scope['url_route']['kwargs']['specialist_id']
        self.room_group_name = f'chat_{self.customer}_{self.specialist}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        data = json.loads(text_data)
        message = data['message']
        username = data['username']
        created_at = datetime.now().strftime('%d.%m.%Y %H:%M')
        room_id = data['room_id']

        await self.save_message(username, room_id, message)

        # Send message to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message': message,
                'username': username,
                'created_at': created_at
            }
        )

    @sync_to_async
    def save_message(self, username, room_id, message):
        author = User.objects.get(username=username)
        RoomMessage.objects.create(author=author, room_id=room_id, body=message)

    # Receive message from room group
    async def chat_message(self, event):
        message = event['message']
        username = event['username']
        created_at = event['created_at']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'username': username,
            'created_at': created_at
        }))