from datetime import datetime
from bson import ObjectId
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils.mongo import replays_collection, events_collection
from .serializers import ReplayStartSerializer

@api_view(["GET"])
def health_check(request):
    return Response({
        "service": "replay",
        "status": "running"
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def start_replay(request):
    serializer = ReplayStartSerializer(data=request.data)
    if serializer.is_valid():
        timeline_id = serializer.validated_data["timeline_id"]
        branch_id = serializer.validated_data["branch_id"]

        # Gather all events associated with this timeline and branch to build the step sequence
        events = list(events_collection.find({
            "timeline_id": timeline_id,
            "branch_id": branch_id
        }).sort("timestamp", 1))

        event_sequence = [str(ev["_id"]) for ev in events]

        # Create replay session record
        replay_data = {
            "timeline_id": timeline_id,
            "branch_id": branch_id,
            "event_sequence": event_sequence,
            "current_step": 0,
            "status": "playing",
            "started_at": datetime.utcnow()
        }

        result = replays_collection.insert_one(replay_data)
        replay_id_str = str(result.inserted_id)

        # Serialize resolved events to return immediately
        resolved_events = []
        for ev in events:
            ev["_id"] = str(ev["_id"])
            if ev.get("timestamp") and isinstance(ev["timestamp"], datetime):
                ev["timestamp"] = ev["timestamp"].isoformat()
            resolved_events.append(ev)

        return Response({
            "replay_id": replay_id_str,
            "status": "replay_started",
            "event_count": len(event_sequence),
            "events": resolved_events
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_replay_status(request, replay_id):
    try:
        replay = replays_collection.find_one({"_id": ObjectId(replay_id)})
        if not replay:
            return Response({"error": "Replay session not found"}, status=status.HTTP_404_NOT_FOUND)

        current_step = replay.get("current_step", 0)
        event_sequence = replay.get("event_sequence", [])
        status_val = replay.get("status", "playing")

        # Dynamic simulation: if the status is "playing", increment current_step on each status check
        # to show real-time playback progression to the UI!
        if status_val == "playing" and len(event_sequence) > 0:
            if current_step < len(event_sequence):
                current_step += 1
                new_status = "playing"
                if current_step >= len(event_sequence):
                    new_status = "completed"
                
                replays_collection.update_one(
                    {"_id": ObjectId(replay_id)},
                    {"$set": {"current_step": current_step, "status": new_status}}
                )
                status_val = new_status

        return Response({
            "replay_id": replay_id,
            "status": status_val,
            "current_step": current_step,
            "total_steps": len(event_sequence)
        })
    except Exception:
        return Response({"error": "Invalid replay_id format"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_replay_details(request, replay_id):
    try:
        replay = replays_collection.find_one({"_id": ObjectId(replay_id)})
        if not replay:
            return Response({"error": "Replay session not found"}, status=status.HTTP_404_NOT_FOUND)

        event_ids = replay.get("event_sequence", [])
        resolved_events = []
        for ev_id in event_ids:
            try:
                ev = events_collection.find_one({"_id": ObjectId(ev_id)})
                if ev:
                    ev["_id"] = str(ev["_id"])
                    if ev.get("timestamp") and isinstance(ev["timestamp"], datetime):
                        ev["timestamp"] = ev["timestamp"].isoformat()
                    resolved_events.append(ev)
            except Exception:
                continue

        replay["_id"] = str(replay["_id"])
        if replay.get("started_at") and isinstance(replay["started_at"], datetime):
            replay["started_at"] = replay["started_at"].isoformat()
        
        replay["events"] = resolved_events
        return Response(replay)
    except Exception:
        return Response({"error": "Invalid replay_id format"}, status=status.HTTP_400_BAD_REQUEST)