import json
from channels.generic.websocket import AsyncJsonWebsocketConsumer

class TimelineConsumer(AsyncJsonWebsocketConsumer):
    """
    Handles live client WebSocket connections on '/ws/timeline/{timeline_id}'
    and broadcasts timeline-specific events in real-time.
    """

    async def connect(self):
        self.timeline_id = self.scope['url_route']['kwargs']['timeline_id']
        self.timeline_group = f"timeline_{self.timeline_id}"

        print(f"[WS CONNECT] Timeline socket connecting for timeline_id: {self.timeline_id}")

        # Join timeline group
        await self.channel_layer.group_add(
            self.timeline_group,
            self.channel_name
        )

        await self.accept()
        print(f"[WS CONNECT] Connection accepted for timeline_id: {self.timeline_id}")

    async def disconnect(self, close_code):
        print(f"[WS DISCONNECT] Socket disconnected for timeline_id: {self.timeline_id} (code: {close_code})")

        # Leave timeline group
        await self.channel_layer.group_discard(
            self.timeline_group,
            self.channel_name
        )

    async def receive_json(self, content):
        """
        Receives messages from client (e.g., keep-alive or ping).
        """
        print(f"[WS MESSAGE] Received packet from client on timeline {self.timeline_id}: {content}")
        # Dynamic client keep-alive support
        if content.get("type") == "ping":
            await self.send_json({"type": "pong"})

    async def timeline_message(self, event):
        """
        Relays broadcasted events from the in-memory channel layer group
        directly to the WebSocket client as JSON.
        """
        payload = event.get("data", {})
        print(f"[WS BROADCAST] Relaying event '{payload.get('event')}' to timeline '{self.timeline_id}' client")
        await self.send_json(payload)
