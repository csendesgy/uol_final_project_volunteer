import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.shortcuts import get_object_or_404
from django.utils import timezone
from ossvolapp.models import EventChat, EventChatHistory, ProfilesOrg, ProfilesVolunteer

class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Capture the room_id from the URL (which is the primary key of the EventChat record)
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'

        # Retrieve the existing EventChat record (raise 404 if not found)
        self.chat_room = await database_sync_to_async(get_object_or_404)(EventChat, chat_id=self.room_id)

        # Add this channel to the group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg = data.get('msg')
        print("Received message:", repr(msg))
        timestamp = timezone.now()
        user = self.scope['user']
        await self.save_message(user, self.room_id, msg, timestamp)
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'msg': msg,
                'timestamp': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                'sender': await self.get_sender_name(user)
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'msg': event['msg'],
            'timestamp': event['timestamp'],
            'sender': event['sender']
        }))

    @database_sync_to_async
    def save_message(self, user, room_id, msg, timestamp):
        chat = get_object_or_404(EventChat, chat_id=room_id)
        # Ensure the message is a string.
        msg = str(msg) if msg is not None else ""
        if user.extension.is_org:
            profile = ProfilesOrg.objects.get(user=user)
            return EventChatHistory.objects.create(chat_id=chat, from_org_id=profile, msg=msg, sent_at=timestamp)
        else:
            profile = ProfilesVolunteer.objects.get(user=user)
            return EventChatHistory.objects.create(chat_id=chat, from_vol_id=profile, msg=msg, sent_at=timestamp)

    @database_sync_to_async
    def get_sender_name(self, user):
        if user.extension.is_org:
            try:
                profile = ProfilesOrg.objects.get(user=user)
                return profile.org_name
            except ProfilesOrg.DoesNotExist:
                return user.username
        else:
            try:
                profile = ProfilesVolunteer.objects.get(user=user)
                return f"{user.first_name} {user.last_name}"
            except ProfilesVolunteer.DoesNotExist:
                return user.username
