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