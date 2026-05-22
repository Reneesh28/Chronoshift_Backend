from bson import ObjectId

from rest_framework.decorators import (
    api_view,
    permission_classes,
)

from rest_framework.permissions import (
    IsAuthenticated,
)

from rest_framework.response import Response
from rest_framework import status
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .serializers import TimelineSerializer

from utils.mongo import timelines_collection


# --------------------------------------------------
# HEALTH CHECK
# --------------------------------------------------

@api_view(["GET"])
def health_check(request):

    return Response({
        "service": "timelines",
        "status": "running"
    })


# --------------------------------------------------
# CREATE TIMELINE
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_timeline(request):

    serializer = TimelineSerializer(data=request.data)

    if serializer.is_valid():

        timeline_data = {
            "user_id": request.user.id,
            "title": serializer.validated_data["title"],
            "description": serializer.validated_data["description"],
        }

        result = timelines_collection.insert_one(timeline_data)

        timeline_data["_id"] = str(result.inserted_id)

        return Response({
            "message": "Timeline created successfully",
            "timeline": timeline_data
        }, status=status.HTTP_201_CREATED)

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


# --------------------------------------------------
# LIST USER TIMELINES
# --------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_timelines(request):

    timelines = list(
        timelines_collection.find({
            "user_id": request.user.id
        })
    )

    for timeline in timelines:
        timeline["_id"] = str(timeline["_id"])

    return Response({
        "timelines": timelines
    })


# --------------------------------------------------
# TIMELINE DETAIL
# --------------------------------------------------

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def timeline_detail(request, timeline_id):

    timeline = timelines_collection.find_one({
        "_id": ObjectId(timeline_id),
        "user_id": request.user.id,
    })

    if not timeline:

        return Response({
            "error": "Timeline not found"
        }, status=status.HTTP_404_NOT_FOUND)

    timeline["_id"] = str(timeline["_id"])

    return Response({
        "timeline": timeline
    })

# --------------------------------------------------
# UPDATE TIMELINE
# --------------------------------------------------

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_timeline(request, timeline_id):

    serializer = TimelineSerializer(data=request.data)

    if serializer.is_valid():

        updated_data = {
            "title": serializer.validated_data["title"],
            "description": serializer.validated_data["description"],
        }

        result = timelines_collection.update_one(
            {
                "_id": ObjectId(timeline_id),
                "user_id": request.user.id,
            },
            {
                "$set": updated_data
            }
        )

        if result.matched_count == 0:

            return Response({
                "error": "Timeline not found"
            }, status=status.HTTP_404_NOT_FOUND)

        timeline = timelines_collection.find_one({
            "_id": ObjectId(timeline_id)
        })

        timeline["_id"] = str(timeline["_id"])

        return Response({
            "message": "Timeline updated successfully",
            "timeline": timeline
        })

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )

# --------------------------------------------------
# DELETE TIMELINE
# --------------------------------------------------

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_timeline(request, timeline_id):

    result = timelines_collection.delete_one({
        "_id": ObjectId(timeline_id),
        "user_id": request.user.id,
    })

    if result.deleted_count == 0:

        return Response({
            "error": "Timeline not found"
        }, status=status.HTTP_404_NOT_FOUND)

    return Response({
        "message": "Timeline deleted successfully"
    })


# --------------------------------------------------
# INTERNAL WEBSOCKET BROADCAST BRIDGE
# --------------------------------------------------

@api_view(["POST"])
@permission_classes([])  # Open to internal microservices
def broadcast_event_view(request):
    """
    Internal REST bridge allowing external microservice processes (FastAPI, Flask)
    to broadcast JSON payloads to timeline WebSocket channels.
    """
    data = request.data or {}
    timeline_id = data.get("timeline_id")
    
    if not timeline_id:
        return Response({
            "error": True,
            "message": "Missing 'timeline_id' parameter.",
            "code": "MISSING_TIMELINE_ID"
        }, status=status.HTTP_400_BAD_REQUEST)
        
    payload = data.get("payload", {})
    if not payload:
        return Response({
            "error": True,
            "message": "Missing 'payload' parameter.",
            "code": "MISSING_PAYLOAD"
        }, status=status.HTTP_400_BAD_REQUEST)

    # Resolve channel layer
    channel_layer = get_channel_layer()
    if not channel_layer:
        return Response({
            "error": True,
            "message": "WebSocket channel layer is not configured.",
            "code": "CHANNELS_UNCONFIGURED"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    group_name = f"timeline_{timeline_id}"
    
    # Send message to the consumer group asynchronously in a synchronous environment
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "timeline.message",
            "data": payload
        }
    )

    print(f"[BROADCAST API] Dispatched event '{payload.get('event')}' to group '{group_name}'")

    return Response({
        "status": "broadcasted",
        "timeline_id": timeline_id,
        "payload": payload
    }, status=status.HTTP_200_OK)