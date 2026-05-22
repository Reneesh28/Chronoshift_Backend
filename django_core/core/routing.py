from django.urls import re_path
from timelines.consumers import TimelineConsumer

websocket_urlpatterns = [
    re_path(r'^ws/timeline/(?P<timeline_id>[^/]+)/?$', TimelineConsumer.as_asgi()),
]
