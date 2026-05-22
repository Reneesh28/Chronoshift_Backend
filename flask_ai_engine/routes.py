from flask import Blueprint, request, jsonify
from bson import ObjectId
from bson.errors import InvalidId

from config import ai_summaries_collection
from services import generate_timeline_summary

# 1. Initialize Flask blueprint
ai_blueprint = Blueprint("ai", __name__, url_prefix="/ai")

# HEALTH / SERVICE STATUS CHECK
@ai_blueprint.route("/health", methods=["GET"])
def health_check():
    """
    Returns a lightweight microservice health report.
    """
    return jsonify({
        "service": "flask_ai_engine",
        "status": "running"
    }), 200

# GENERATE SUMMARY ENDPOINT
@ai_blueprint.route("/generate-summary", methods=["POST"])
def post_generate_summary():
    """
    Triggers chronological parallel timeline narrative inference.
    Exposes: POST /ai/generate-summary
    """
    data = request.get_json() or {}
    
    timeline_id = data.get("timeline_id")
    branch_id = data.get("branch_id")
    simulation_id = data.get("simulation_id")

    # Validate presence of required properties
    if not all([timeline_id, branch_id, simulation_id]):
        return jsonify({
            "error": True,
            "message": "Missing required fields: 'timeline_id', 'branch_id', and 'simulation_id' are mandatory.",
            "code": "INVALID_REQUEST"
        }), 400

    try:
        # Trigger core LangChain & Inference pipelines
        result = generate_timeline_summary(
            timeline_id=timeline_id,
            branch_id=branch_id,
            simulation_id=simulation_id
        )
        
        # Format response to strictly match target API contract
        return jsonify({
            "summary_id": result["summary_id"],
            "risk_score": result["risk_score"],
            "summary": result["summary"],
            "confidence_score": result.get("confidence_score"),
            "branch_type": result.get("branch_type"),
            "future_outlook": result.get("future_outlook"),
            "risk_analysis": result.get("risk_analysis"),
            "opportunity_analysis": result.get("opportunity_analysis"),
            "timeline_stability": result.get("timeline_stability"),
            "divergence_reason": result.get("divergence_reason"),
            "strategic_outlook": result.get("strategic_outlook"),
            "event_evolution": result.get("event_evolution", [])
        }), 200

    except ValueError as err:
        return jsonify({
            "error": True,
            "message": str(err),
            "code": "INVALID_REQUEST"
        }), 400

    except FileNotFoundError as err:
        return jsonify({
            "error": True,
            "message": str(err),
            "code": "BRANCH_NOT_FOUND"
        }), 404

    except Exception as err:
        print(f"[CRITICAL API ERROR] Summary generation failed: {err}")
        return jsonify({
            "error": True,
            "message": f"Summary orchestration failed: {str(err)}",
            "code": "AI_ENGINE_ERROR"
        }), 500

# RETRIEVE SUMMARY BY SUMMARY ID
@ai_blueprint.route("/summary/<summary_id>", methods=["GET"])
def get_summary(summary_id):
    """
    Retrieves a pre-calculated AI summary narrative by its unique ID.
    Exposes: GET /ai/summary/{summary_id}
    """
    # 1. Search database using ObjectId format
    summary_doc = None
    try:
        summary_doc = ai_summaries_collection.find_one({"_id": ObjectId(summary_id)})
    except InvalidId:
        # Fallback to string-based ID match in case IDs are recorded as strings
        summary_doc = ai_summaries_collection.find_one({"_id": summary_id})

    if not summary_doc:
        return jsonify({
            "error": True,
            "message": "Target AI summary not found.",
            "code": "INVALID_REQUEST"
        }), 404

    # 2. Map payload structure to exact API Contract specification
    return jsonify(_serialize_summary(summary_doc)), 200


# RETRIEVE SUMMARY BY BRANCH ID
@ai_blueprint.route("/summary/branch/<branch_id>", methods=["GET"])
def get_summary_by_branch(branch_id):
    """
    Retrieves a pre-calculated AI summary narrative by the target branch ID.
    This allows the frontend to fetch cached reports when a user selects a node.
    Exposes: GET /ai/summary/branch/{branch_id}
    """
    summary_doc = ai_summaries_collection.find_one({"branch_id": branch_id})

    if not summary_doc:
        return jsonify({
            "error": True,
            "message": "No AI summary found for this branch.",
            "code": "SUMMARY_NOT_FOUND"
        }), 404

    return jsonify(_serialize_summary(summary_doc)), 200


def _serialize_summary(doc: dict) -> dict:
    """
    Transforms a MongoDB AI summary document into a clean JSON-serializable response dict.
    """
    return {
        "summary_id": str(doc["_id"]),
        "branch_id": doc.get("branch_id"),
        "risk_score": doc.get("risk_score"),
        "confidence_score": doc.get("confidence_score"),
        "summary": doc.get("summary"),
        "branch_type": doc.get("branch_type"),
        "future_outlook": doc.get("future_outlook"),
        "risk_analysis": doc.get("risk_analysis"),
        "opportunity_analysis": doc.get("opportunity_analysis"),
        "timeline_stability": doc.get("timeline_stability"),
        "divergence_reason": doc.get("divergence_reason"),
        "strategic_outlook": doc.get("strategic_outlook"),
        "event_evolution": doc.get("event_evolution", [])
    }
