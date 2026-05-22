import re
import requests
from datetime import datetime
from bson import ObjectId
from langchain_core.prompts import PromptTemplate

from config import (
    timelines_collection,
    branches_collection,
    simulations_collection,
    ai_summaries_collection,
    HF_TOKEN,
    MODEL_NAME
)

def emit_websocket_event(timeline_id: str, payload: dict):
    """
    Issues a synchronous HTTP POST request to Django's WebSocket broadcast bridge
    to relay AI events to the React client in real-time.
    """
    url = "http://localhost:8000/api/timelines/broadcast/"
    try:
        response = requests.post(
            url,
            json={
                "timeline_id": timeline_id,
                "payload": payload
            },
            timeout=2.0
        )
        if response.status_code != 200:
            print(f"[WS AI EMITTER WARNING] Django broadcast returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"[WS AI EMITTER ERROR] Failed to emit WebSocket event: {e}")

def get_fallback_summary(decision: str, divergence_score: float, depth_level: int, branch_name: str) -> str:
    """
    Generates a high-precision, futuristic fallback summary when the external Hugging Face LLM is unavailable.
    """
    decision_clean = decision.strip() if decision else ""
    
    # Financial decisions
    if any(keyword in decision_clean.lower() for keyword in ["budget", "hire", "capital", "fund", "financial", "salary", "cost"]):
        return (
            f"Strategic resource allocation for '{decision_clean[:50]}...' projects a localized velocity increase "
            f"across this branch, but capital overhead escalates baseline operational risk to {round(divergence_score * 0.9, 2)}."
        )
    
    # Tech/Architecture/Infrastructure decisions
    if any(keyword in decision_clean.lower() for keyword in ["code", "refactor", "database", "infra", "docker", "server", "api", "pipeline", "network"]):
        return (
            f"Systemic integration of '{decision_clean[:50]}...' optimizes core architecture efficiency at depth {depth_level}. "
            f"However, alternate timeline simulation warns of potential branch divergence due to legacy dependency conflicts."
        )

    # Expansion/Marketing decisions
    if any(keyword in decision_clean.lower() for keyword in ["expand", "market", "international", "growth", "scale", "launch", "marketing"]):
        return (
            f"Accelerated branch evolution in scenario '{branch_name}' indicates aggressive scaling and market penetration. "
            f"Operational complexity limits timeline convergence, introducing systemic instability across alternate nodes."
        )

    # General decisions
    return (
        f"Timeline branch '{branch_name}' initialized via decision: '{decision_clean}'. "
        f"Alternate scenario projection predicts a structural divergence of {divergence_score}, stabilizing with moderate confidence "
        f"as depth levels progress."
    )

def clean_llm_output(output_text: str, prompt: str) -> str:
    """
    Clean raw text returned from Hugging Face Inference API.
    """
    # Remove prompt echo if present
    if prompt in output_text:
        output_text = output_text.replace(prompt, "")
        
    # Standard instruction-following cleanup
    if "Output:" in output_text:
        output_text = output_text.split("Output:")[-1]
    if "Instruct:" in output_text:
        output_text = output_text.split("Instruct:")[0]

    # Clean redundant whitespaces
    output_text = output_text.strip()
    output_text = re.sub(r'\s+', ' ', output_text)
    
    # Extract only first 2 sentences for visual elegance
    sentences = re.split(r'(?<=[.!?])\s+', output_text)
    clean_sentences = [s.strip() for s in sentences if s.strip()]
    
    final_text = " ".join(clean_sentences[:2])
    
    # If empty or too short, return fallback indicator
    if len(final_text) < 15:
        return ""
        
    return final_text

def generate_timeline_summary(timeline_id: str, branch_id: str, simulation_id: str) -> dict:
    """
    Orchestrates the ChronoShift AI summary generation flow:
    1. Retrieves contextual timeline and branch details from MongoDB Atlas (RAG).
    2. Calculates heuristic quant-grade risk and confidence scores.
    3. Assembles structured prompt using LangChain templates.
    4. Calls the external Hugging Face serverless API using microsoft/phi-2.
    5. Falls back seamlessly to template-based heuristics on API rate limits or failures.
    6. Persists the final outcome to MongoDB Atlas under `ai_summaries` collection.
    """
    print(f"\n[AI START] Triggered summary generation for branch {branch_id}")

    # Validate IDs
    try:
        t_id_obj = ObjectId(timeline_id)
    except Exception as e:
        print(f"[AI ERROR] Invalid timeline ObjectId format: {e}")
        raise ValueError("Invalid timeline_id format")

    b_id_obj = None
    if branch_id != 'root':
        try:
            b_id_obj = ObjectId(branch_id)
        except Exception as e:
            print(f"[AI ERROR] Invalid branch ObjectId format: {e}")
            raise ValueError("Invalid branch_id format")

    s_id_obj = None
    if simulation_id and simulation_id != 'default':
        try:
            s_id_obj = ObjectId(simulation_id)
        except Exception as e:
            print(f"[AI ERROR] Invalid simulation ObjectId format: {e}")
            # We don't raise here, we will just treat simulation as missing / default
            pass

    # Fetch context documents
    timeline = timelines_collection.find_one({"_id": t_id_obj})
    
    if branch_id == 'root':
        branch = {
            "branch_name": "Main Root Core",
            "decision_trigger": "Initial timeline setup parameters.",
            "divergence_score": 0.0,
            "depth_level": 1,
            "parent_branch_id": None
        }
    else:
        branch = branches_collection.find_one({"_id": b_id_obj})

    if s_id_obj:
        simulation = simulations_collection.find_one({"_id": s_id_obj})
    else:
        simulation = None

    if not timeline:
        raise FileNotFoundError(f"Timeline not found: {timeline_id}")
    if not branch:
        raise FileNotFoundError(f"Branch not found: {branch_id}")

    # Extract dynamic inputs
    timeline_title = timeline.get("title", "Unnamed Timeline")
    timeline_desc = timeline.get("description", "No description")
    branch_name = branch.get("branch_name", "Alternative Scenario")
    decision = branch.get("decision_trigger", "Initial state transition")
    divergence_score = float(branch.get("divergence_score", 0.5))
    depth_level = int(branch.get("depth_level", 1))

    # Fetch parent branch context if available
    parent_decision = "Root node launch configuration"
    parent_id_str = branch.get("parent_branch_id")
    if parent_id_str:
        try:
            parent_branch = branches_collection.find_one({"_id": ObjectId(parent_id_str)})
            if parent_branch:
                parent_decision = parent_branch.get("decision_trigger", "Parent baseline")
        except Exception:
            pass

    # Fetch prior AI summaries within the timeline to maintain narrative continuity (RAG memory)
    prior_context_str = ""
    try:
        prior_summaries = list(ai_summaries_collection.find({"timeline_id": timeline_id}).sort("generated_at", -1).limit(2))
        if prior_summaries:
            priors = [f"- {s.get('summary')}" for s in prior_summaries if s.get("summary")]
            prior_context_str = "\n".join(priors)
    except Exception as e:
        print(f"[AI WARNING] Could not retrieve prior summaries: {e}")

    # HEURISTIC CALCULATIONS

    # Risk climbs with divergence score and timeline branch depth
    risk_score = round(min(1.0, max(0.0, (divergence_score * 0.7) + (depth_level * 0.05))), 2)
    # Confidence drops with higher divergence and higher depth (uncertainty escalates)
    confidence_score = round(min(1.0, max(0.0, 1.0 - (divergence_score * 0.4) - (depth_level * 0.03))), 2)

    # LANGCHAIN PROMPT ORCHESTRATION
    template = """Instruct: You are ChronoShift's narrative intelligence explanation system.
Analyze the following parallel timeline data and generate a strategic, analytical 1-to-2 sentence future state summary.
Do not use conversational filler. Do not repeat the prompt. Avoid generic introductions.

Timeline Base Context:
- Title: {timeline_title}
- Focus: {timeline_desc}

Parent State Decision: {parent_decision}
Current Alternate Branch Name: {branch_name}
Current Injected Decision: {decision}
Divergence Magnitude: {divergence_score}
Timeline Depth Level: {depth_level}

Prior Timeline Progress (Context Continuity):
{prior_context}

Output: """

    prompt_template = PromptTemplate(
        input_variables=[
            "timeline_title",
            "timeline_desc",
            "parent_decision",
            "branch_name",
            "decision",
            "divergence_score",
            "depth_level",
            "prior_context"
        ],
        template=template
    )

    prompt = prompt_template.format(
        timeline_title=timeline_title,
        timeline_desc=timeline_desc,
        parent_decision=parent_decision,
        branch_name=branch_name,
        decision=decision,
        divergence_score=divergence_score,
        depth_level=depth_level,
        prior_context=prior_context_str if prior_context_str else "No prior summaries generated yet."
    )

    # ==========================================================
    # HUGGING FACE INFERENCE CALL (WITH RESILIENT FALLBACK)
    # ==========================================================
    summary_text = ""
    api_success = False

    if HF_TOKEN and MODEL_NAME:
        url = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 80,
                "temperature": 0.5,
                "return_full_text": False
            }
        }
        
        try:
            print(f"[AI] Querying Hugging Face Serverless API ({MODEL_NAME})...")
            response = requests.post(url, json=payload, headers=headers, timeout=5.0)
            
            if response.status_code == 200:
                res_data = response.json()
                if isinstance(res_data, list) and len(res_data) > 0:
                    raw_text = res_data[0].get("generated_text", "")
                    cleaned = clean_llm_output(raw_text, prompt)
                    if cleaned:
                        summary_text = cleaned
                        api_success = True
                        print("[AI SUCCESS] Summary successfully generated via HF API.")
            else:
                print(f"[AI WARNING] Hugging Face API returned status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as err:
            print(f"[AI WARNING] Hugging Face API connection failed: {err}")

    # Trigger heuristic-driven template fallback if API fails
    if not api_success:
        print("[AI FALLBACK] Activating resilient local narrative builder...")
        summary_text = get_fallback_summary(decision, divergence_score, depth_level, branch_name)
        print(f"[AI FALLBACK RESULT] Generated fallback: '{summary_text}'")

    # ==========================================================
    # MONGO PERSISTENCE LAYER
    # ==========================================================
    existing_summary = ai_summaries_collection.find_one({"branch_id": branch_id})

    if existing_summary:
        ai_summaries_collection.update_one(
            {"_id": existing_summary["_id"]},
            {"$set": {
                "risk_score": risk_score,
                "confidence_score": confidence_score,
                "summary": summary_text,
                "generated_at": datetime.utcnow()
            }}
        )
        summary_id = str(existing_summary["_id"])
        print(f"[DATABASE] Updated existing AI summary document: '{summary_id}'")
    else:
        summary_doc = {
            "timeline_id": timeline_id,
            "branch_id": branch_id,
            "simulation_id": simulation_id,
            "risk_score": risk_score,
            "confidence_score": confidence_score,
            "summary": summary_text,
            "generated_at": datetime.utcnow()
        }
        res = ai_summaries_collection.insert_one(summary_doc)
        summary_id = str(res.inserted_id)
        print(f"[DATABASE] Persisted new AI summary document: '{summary_id}'")

    # Emit ai_summary_ready event to timeline WebSocket group
    emit_websocket_event(timeline_id, {
        "event": "ai_summary_ready",
        "summary_id": summary_id,
        "branch_id": branch_id,
        "risk_score": risk_score,
        "confidence_score": confidence_score
    })

    return {
        "summary_id": summary_id,
        "timeline_id": timeline_id,
        "branch_id": branch_id,
        "simulation_id": simulation_id,
        "risk_score": risk_score,
        "confidence_score": confidence_score,
        "summary": summary_text
    }
