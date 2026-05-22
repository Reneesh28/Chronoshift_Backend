import random
from datetime import datetime
from bson import ObjectId
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from utils.mongo import (
    branches_collection,
    events_collection,
    simulations_collection,
    timelines_collection,
    ai_summaries_collection
)
from .serializers import (
    BranchCreateSerializer,
    EventInjectSerializer,
    CompareBranchesSerializer
)

@api_view(["GET"])
def health_check(request):
    return Response({
        "service": "branches",
        "status": "running"
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_branch(request):
    serializer = BranchCreateSerializer(data=request.data)
    if serializer.is_valid():
        timeline_id = serializer.validated_data["timeline_id"]
        parent_branch_id = serializer.validated_data.get("parent_branch_id")
        decision = serializer.validated_data.get("decision", "")
        branch_name = serializer.validated_data.get("branch_name", "")

        # Verify timeline exists
        try:
            timeline = timelines_collection.find_one({"_id": ObjectId(timeline_id)})
            if not timeline:
                return Response({"error": "Timeline not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Invalid timeline_id format"}, status=status.HTTP_400_BAD_REQUEST)

        # Determine depth level and base parent
        depth_level = 1
        parent_branch = None
        if parent_branch_id:
            try:
                parent_branch = branches_collection.find_one({"_id": ObjectId(parent_branch_id)})
                if not parent_branch:
                    return Response({"error": "Parent branch not found"}, status=status.HTTP_404_NOT_FOUND)
                depth_level = parent_branch.get("depth_level", 1) + 1
            except Exception:
                return Response({"error": "Invalid parent_branch_id format"}, status=status.HTTP_400_BAD_REQUEST)

        # Heuristic divergence score
        divergence_score = round(random.uniform(0.3, 0.9), 2)

        # Default branch name if not provided
        if not branch_name:
            if parent_branch:
                branch_name = f"Branch derived from {parent_branch.get('branch_name')}"
            else:
                branch_name = f"Root Branch for {timeline.get('title')}"

        branch_data = {
            "timeline_id": timeline_id,
            "parent_branch_id": parent_branch_id if parent_branch_id else None,
            "branch_name": branch_name,
            "decision_trigger": decision if decision else "Initial timeline launch",
            "divergence_score": divergence_score,
            "depth_level": depth_level,
            "status": "active",
            "created_at": datetime.utcnow()
        }

        result = branches_collection.insert_one(branch_data)
        branch_id_str = str(result.inserted_id)
        branch_data["_id"] = branch_id_str
        branch_data["created_at"] = branch_data["created_at"].isoformat()

        # Update root_branch_id of timeline if this is a root branch and timeline doesn't have one
        if not parent_branch_id and not timeline.get("root_branch_id"):
            timelines_collection.update_one(
                {"_id": ObjectId(timeline_id)},
                {"$set": {"root_branch_id": branch_id_str}}
            )

        return Response({
            "branch_id": branch_id_str,
            "status": "branch_created",
            "divergence_score": divergence_score,
            "branch": branch_data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_branch_details(request, branch_id):
    try:
        branch = branches_collection.find_one({"_id": ObjectId(branch_id)})
        if not branch:
            return Response({"error": "Branch not found"}, status=status.HTTP_404_NOT_FOUND)
        
        branch["_id"] = str(branch["_id"])
        if branch.get("created_at"):
            if isinstance(branch["created_at"], datetime):
                branch["created_at"] = branch["created_at"].isoformat()
        return Response(branch)
    except Exception:
        return Response({"error": "Invalid branch_id format"}, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def inject_decision_event(request):
    serializer = EventInjectSerializer(data=request.data)
    if serializer.is_valid():
        timeline_id = serializer.validated_data["timeline_id"]
        branch_id = serializer.validated_data["branch_id"]
        event_type = serializer.validated_data["event_type"]
        decision = serializer.validated_data["decision"]

        # Validate that timeline and branch exist
        try:
            timeline = timelines_collection.find_one({"_id": ObjectId(timeline_id)})
            if not timeline:
                return Response({"error": "Timeline not found"}, status=status.HTTP_404_NOT_FOUND)
            branch = branches_collection.find_one({"_id": ObjectId(branch_id)})
            if not branch:
                return Response({"error": "Branch not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Invalid timeline_id or branch_id format"}, status=status.HTTP_400_BAD_REQUEST)

        # Insert decision event
        event_data = {
            "timeline_id": timeline_id,
            "branch_id": branch_id,
            "event_type": event_type,
            "event_value": decision,
            "created_by": request.user.id,
            "timestamp": datetime.utcnow()
        }

        event_result = events_collection.insert_one(event_data)
        event_id_str = str(event_result.inserted_id)

        # Automatically insert simulation queued record (Phase 4 connection placeholder)
        sim_data = {
            "timeline_id": timeline_id,
            "source_branch_id": branch_id,
            "generated_branch_ids": [],
            "simulation_status": "queued",
            "divergence_results": {},
            "started_at": datetime.utcnow(),
            "completed_at": None
        }
        simulations_collection.insert_one(sim_data)

        return Response({
            "event_id": event_id_str,
            "status": "queued_for_simulation"
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def compare_branches(request):
    serializer = CompareBranchesSerializer(data=request.data)
    if serializer.is_valid():
        timeline_id = serializer.validated_data["timeline_id"]
        branch_ids = serializer.validated_data["branch_ids"]

        comparison_results = []
        for bid in branch_ids:
            try:
                branch = branches_collection.find_one({
                    "_id": ObjectId(bid),
                    "timeline_id": timeline_id
                })
                if not branch:
                    continue
                
                # Try to get corresponding risk, confidence, and narrative summary from AI summaries if any exists
                ai_summary = ai_summaries_collection.find_one({"branch_id": bid})
                risk_score = ai_summary.get("risk_score", 0.5) if ai_summary else 0.5
                confidence_score = ai_summary.get("confidence_score", 0.7) if ai_summary else 0.7
                summary = ai_summary.get("summary", "No AI summary calculated yet.") if ai_summary else "No AI summary calculated yet."

                comparison_results.append({
                    "branch_id": bid,
                    "branch_name": branch.get("branch_name", ""),
                    "branch_type": branch.get("branch_type") or (ai_summary.get("branch_type") if ai_summary else None),
                    "divergence_score": branch.get("divergence_score", 0.0),
                    "risk_score": risk_score,
                    "confidence_score": confidence_score,
                    "summary": summary,
                    "future_outlook": ai_summary.get("future_outlook") if ai_summary else None,
                    "risk_analysis": ai_summary.get("risk_analysis") if ai_summary else None,
                    "opportunity_analysis": ai_summary.get("opportunity_analysis") if ai_summary else None,
                    "timeline_stability": ai_summary.get("timeline_stability") if ai_summary else None,
                    "divergence_reason": ai_summary.get("divergence_reason") if ai_summary else None,
                    "strategic_outlook": ai_summary.get("strategic_outlook") if ai_summary else None,
                    "event_evolution": ai_summary.get("event_evolution", []) if ai_summary else [],
                })
            except Exception:
                continue

        return Response({
            "comparison": comparison_results
        })

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)