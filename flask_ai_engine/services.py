import re
import random
import time
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
    MODEL_NAME,
    AI_REMOTE_ENABLED,
    DJANGO_URL
)

# ==========================================================
# EVENT EVOLUTION GENERATORS
# ==========================================================

# ==========================================================
# ANCESTRY TRAVERSAL & KEYWORD EXTRACTION HELPER FUNCTIONS
# ==========================================================

def _get_branch_ancestry(branch_id: str, timeline_id: str) -> dict:
    """
    Recursively traverses up the parent branch chain starting from branch_id
    to rebuild the entire chronological decision history, inherited risks,
    and semantic context.
    """
    if not branch_id or branch_id == 'root':
        return {
            "history": [],
            "event_progression": [],
            "inherited_risks": [],
            "history_summary_str": "Root baseline configuration.",
            "branch_types": []
        }

    history = []
    current_id = branch_id
    
    # Traverse up to 20 levels to prevent infinite loops
    for _ in range(20):
        if not current_id or current_id == 'root':
            break
        try:
            b_obj = ObjectId(current_id)
        except Exception:
            break
            
        branch_doc = branches_collection.find_one({"_id": b_obj})
        if not branch_doc:
            break
            
        history.append(branch_doc)
        current_id = branch_doc.get("parent_branch_id")
        
    # Reverse history so it runs chronologically (oldest ancestor -> current branch)
    history.reverse()
    
    event_progression = [b.get("decision_trigger", "") for b in history if b.get("decision_trigger")]
    branch_types = [b.get("branch_type") for b in history if b.get("branch_type")]
    
    # Inherit risk factors from prior branches
    inherited_risks = []
    for b in history[:-1]:  # Exclude current branch itself to identify inherited ancestral risks
        b_type = b.get("branch_type")
        b_name = b.get("branch_name", "Scenario")
        if b_type == "high_risk_growth":
            inherited_risks.append(f"Accelerated volatility from parent '{b_name}'")
        elif b_type == "systemic_collapse":
            inherited_risks.append(f"Subsystemic degradation from parent '{b_name}'")
            
    history_steps = []
    for idx, b in enumerate(history[:-1]):
        b_name = b.get("branch_name", "Scenario")
        dec = b.get("decision_trigger", "No decision trigger")
        history_steps.append(f"Step {idx+1} [{b_name}]: '{dec}'")
        
    history_summary_str = " -> ".join(history_steps) if history_steps else "Direct descendant of Root timeline."
    
    return {
        "history": history,
        "event_progression": event_progression,
        "inherited_risks": inherited_risks,
        "history_summary_str": history_summary_str,
        "branch_types": branch_types
    }


def _extract_keywords(text: str) -> list:
    """
    Extracts high-value active nouns, verbs, and domain-specific terms from a decision string,
    filtering out common stop words to drive semantic tokenization and timeline weave-ins.
    """
    if not text:
        return []
    cleaned = re.sub(r'[^\w\s]', '', text.lower())
    words = cleaned.split()
    
    stop_words = {
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'arent', 'as', 'at', 
        'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can', 'cant', 'cannot', 
        'could', 'couldnt', 'did', 'didnt', 'do', 'does', 'doesnt', 'doing', 'dont', 'down', 'during', 'each', 'few', 
        'for', 'from', 'further', 'had', 'hadnt', 'has', 'hasnt', 'have', 'havent', 'having', 'he', 'hed', 'hell', 
        'hes', 'her', 'here', 'heres', 'hers', 'herself', 'him', 'himself', 'his', 'how', 'hows', 'i', 'id', 'ill', 
        'im', 'ive', 'if', 'in', 'into', 'is', 'isnt', 'it', 'its', 'itself', 'lets', 'me', 'more', 'most', 'mustnt', 
        'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours', 
        'ourselves', 'out', 'over', 'own', 'same', 'shant', 'she', 'shed', 'shell', 'shes', 'should', 'shouldnt', 
        'so', 'some', 'such', 'than', 'that', 'thats', 'the', 'their', 'theirs', 'them', 'themselves', 'then', 'there', 
        'theres', 'these', 'they', 'theyd', 'theyll', 'theyre', 'theyve', 'this', 'those', 'through', 'to', 'too', 
        'under', 'until', 'up', 'very', 'was', 'wasnt', 'we', 'wed', 'well', 'were', 'weve', 'werent', 'what', 'whats', 
        'when', 'whens', 'where', 'wheres', 'which', 'while', 'who', 'whos', 'whom', 'why', 'whys', 'with', 'wont', 
        'would', 'wouldnt', 'you', 'youd', 'youll', 'youre', 'youve', 'your', 'yours', 'yourself', 'yourselves',
        # Common domain fillers to exclude
        'decision', 'trigger', 'injected', 'timeline', 'option', 'strategy', 'plan', 'parameter', 'parameters', 
        'initial', 'setup', 'state', 'transition'
    }
    
    keywords = []
    for w in words:
        if w not in stop_words and len(w) > 2:
            keywords.append(w)
            
    # Return unique keywords while preserving order
    seen = set()
    unique_keywords = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            unique_keywords.append(k)
            
    return unique_keywords


# ==========================================================
# HIGH-FIDELITY CAUSAL NARRATIVE GENERATORS
# ==========================================================

def _generate_event_evolution(decision: str, branch_type: str, divergence_score: float, keywords: list = None, inherited_risks: list = None) -> list:
    """
    Generates a chronological list of projected future event snapshots
    at T+1, T+3, T+6, and T+12 month intervals, dynamically weaving in keywords
    and cascading consequences.
    """
    # Pick keywords or use default context buffers
    k1 = keywords[0].capitalize() if (keywords and len(keywords) > 0) else "System optimization"
    k2 = keywords[1] if (keywords and len(keywords) > 1) else (keywords[0] if (keywords and len(keywords) > 0) else "infrastructure planning")
    k3 = keywords[2] if (keywords and len(keywords) > 2) else "operational interface"
    
    risk_suffix = ""
    if inherited_risks:
        risk_suffix = " under compounded prior instability"

    if branch_type == "stable_growth":
        return [
            {"timeframe": "T+1 Month", "state": f"{k1} phase initiated; baseline stabilization established under controlled resource velocity.", "status": "stable"},
            {"timeframe": "T+3 Months", "state": f"Targeted coordination milestones for {k2} achieved with optimal resource alignment{risk_suffix}.", "status": "stable"},
            {"timeframe": "T+6 Months", "state": f"Synergistic stabilization of {k3} processes completed, confirming high-efficiency output.", "status": "stable"},
            {"timeframe": "T+12 Months", "state": f"Long-term structural equilibrium achieved; optimized {k1} systems deliver robust risk-adjusted returns.", "status": "stable"},
        ]
    elif branch_type == "high_risk_growth":
        return [
            {"timeframe": "T+1 Month", "state": f"Aggressive scaling of {k1} initiated, driving sudden resource and capital absorption.", "status": "active"},
            {"timeframe": "T+3 Months", "state": f"Rapid scaling of {k2} introduces friction points and high operational strain{risk_suffix}.", "status": "warning"},
            {"timeframe": "T+6 Months", "state": f"Complexity from {k3} acceleration outpaces baseline mitigation capabilities, inducing volatility.", "status": "volatile"},
            {"timeframe": "T+12 Months", "state": f"Bifurcation threshold reached: {k1} scaling yields high-yield breakout or complete systemic overload.", "status": "critical"},
        ]
    elif branch_type == "systemic_collapse":
        return [
            {"timeframe": "T+1 Month", "state": f"Immediate operational disruption detected in {k1} core subsystems; resilience margins begin eroding.", "status": "warning"},
            {"timeframe": "T+3 Months", "state": f"Cascading failure loops propagate from {k2} domains, compromising critical dependent interfaces{risk_suffix}.", "status": "critical"},
            {"timeframe": "T+6 Months", "state": f"Resilience breach: {k3} fragmentation triggers widespread organizational coherence degradation.", "status": "critical"},
            {"timeframe": "T+12 Months", "state": f"Branch trajectory terminal collapse: structural viability of {k1} completely compromised.", "status": "collapsed"},
        ]
    else:
        # Volatile/Other
        return [
            {"timeframe": "T+1 Month", "state": f"Divergent impulse propagation begins as {k1} parameters are injected into baseline systems.", "status": "active"},
            {"timeframe": "T+3 Months", "state": f"Measurable drift of {divergence_score:.0%} recorded; {k2} adjustments trigger initial structural variation{risk_suffix}.", "status": "active"},
            {"timeframe": "T+6 Months", "state": f"Branch trajectory enters a complex stabilization corridor around {k3} variables.", "status": "stable"},
            {"timeframe": "T+12 Months", "state": f"Temporal resolution achieved: alternative state reaches dynamic equilibrium driven by {k1} patterns.", "status": "stable"},
        ]


def _generate_risk_analysis(branch_type: str, divergence_score: float, keywords: list = None, inherited_risks: list = None) -> str:
    """
    Analyzes potential downside trajectories, focusing strictly on systemic failure loops,
    threshold breaches, and resource depletion, factoring in prior ancestral instabilities.
    """
    k1 = keywords[0] if (keywords and len(keywords) > 0) else "operational core"
    k2 = keywords[1] if (keywords and len(keywords) > 1) else "resource infrastructure"
    
    risk_prefix = ""
    if inherited_risks:
        risk_prefix = f"Inherited volatility warning: {'; '.join(inherited_risks)}. "
        
    if branch_type == "stable_growth":
        return (
            f"{risk_prefix}Systemic volatility remains minimal. The deviation in {k1} parameters maintains a safety margin "
            f"well above critical failure thresholds. Divergence of {divergence_score:.2f} poses no structural risk to baseline stability."
        )
    elif branch_type == "high_risk_growth":
        return (
            f"{risk_prefix}High-volatility feedback loops identified. Fast-paced acceleration of {k1} exceeds "
            f"the standard stabilization threshold, risking acute bottlenecks in {k2} around T+6 months. "
            f"A divergence of {divergence_score:.2f} indicates a strong chance of non-linear risk compounding."
        )
    elif branch_type == "systemic_collapse":
        return (
            f"{risk_prefix}Critical cascading failure loops active. The extreme shift in {k1} triggers immediate resource "
            f"exhaustion, bypassing standard dampening mechanisms. At a divergence of {divergence_score:.2f}, "
            f"the timeline is highly vulnerable to systemic collapse, leaving zero buffer for error."
        )
    
    return (
        f"{risk_prefix}Moderate threat exposure. Divergence at {divergence_score:.2f} creates operational variance in {k1}. "
        f"While failure thresholds are not yet breached, close monitoring of {k2} metrics is advised."
    )


def _generate_opportunity_analysis(branch_type: str, decision: str, keywords: list = None) -> str:
    """
    Focuses strictly on value capture windows, strategic upsides, and unique competitive advantages,
    entirely avoiding risk or failure language.
    """
    k1 = keywords[0] if (keywords and len(keywords) > 0) else "innovation"
    k2 = keywords[1] if (keywords and len(keywords) > 1) else "value capture"
    
    if branch_type == "stable_growth":
        return (
            f"High-probability value capture window unlocked. The deliberate deployment of '{decision[:60]}...' "
            f"creates a highly predictable efficiency advantage. This stable environment provides a perfect platform "
            f"for systemic scaling of {k1} and long-term optimization of {k2}."
        )
    elif branch_type == "high_risk_growth":
        return (
            f"Aggressive growth and first-mover leverage unlocked. Choosing '{decision[:60]}...' "
            f"opens an elite window for rapid scaling in {k1}, with potential for unprecedented breakthrough "
            f"performance in {k2} if captured within the T+3 to T+6 month acceleration phase."
        )
    elif branch_type == "systemic_collapse":
        return (
            f"Highly constrained upside. While the shift toward {k1} attempts to exploit strategic gains, "
            f"the rapid onset of operational strain closes the value capture window prematurely, preventing "
            f"any meaningful capitalization on {k2}."
        )
        
    return (
        f"Standard value capture potential. The injection of '{decision[:60]}...' "
        f"creates moderate opportunities in {k1}. Execution speed will determine the yield of {k2} capture."
    )


def _generate_timeline_stability(branch_type: str, divergence_score: float) -> str:
    """
    Provides a quantitative-grade assessment of structural survivability and coherence.
    """
    if branch_type == "stable_growth":
        return "HIGH (90%+) — Branch maintains optimal structural coherence. Deviation is highly dampened, preventing path degradation."
    elif branch_type == "high_risk_growth":
        return f"MODERATE (55% - 70%) — Structural resilience is challenged. Current divergence of {divergence_score:.0%} indicates sensitive dependence on adaptive stabilization protocols."
    elif branch_type == "systemic_collapse":
        return f"LOW (<20%) — Critical structural fragmentation in progress. Degradation trajectory is irreversible under standard dampening models."
    return f"MODERATE — Standard resilience profile. Coherence remains intact with a projected survivability of 75%."


def _generate_strategic_outlook(branch_type: str, decision: str, divergence_score: float, keywords: list = None) -> str:
    """
    Provides concrete, action-oriented recommendations and quantitative metrics / threshold checks,
    advising the user on exact decision boundary criteria.
    """
    k1 = keywords[0] if (keywords and len(keywords) > 0) else "core implementation"
    
    if branch_type == "stable_growth":
        return (
            f"STRATEGIC RECOMMENDATION: APPROVE. Proceed with immediate execution of '{decision[:60]}...'. "
            f"This branch represents a premium risk-adjusted path. Recommendation: Establish a performance buffer of "
            f"+15% and schedule a routine optimization audit at T+6 months to lock in gains."
        )
    elif branch_type == "high_risk_growth":
        return (
            f"STRATEGIC RECOMMENDATION: PROCEED WITH CAUTION. Implement a phased deployment model for '{decision[:60]}...'. "
            f"Actionable Criteria: Establish a strict divergence circuit-breaker at score >= 0.75. "
            f"If {k1} volatility exceeds 25% by T+3 months, halt scaling and activate parent-branch fallback protocols."
        )
    elif branch_type == "systemic_collapse":
        return (
            f"STRATEGIC RECOMMENDATION: ABORT / REDESIGN. Do not proceed with the current '{decision[:60]}...' path. "
            f"Actionable Criteria: This decision is structurally unviable due to a divergence of {divergence_score:.2f}. "
            f"We advise immediate roll-back to the parent state and redirecting resources to a stable growth alternative."
        )
        
    return (
        f"STRATEGIC RECOMMENDATION: MONITOR. Proceed with limited implementation of '{decision[:60]}...'. "
        f"Actionable Criteria: Review divergence metrics at T+3 months. If drift remains below 0.50, "
        f"continue scaling; otherwise, freeze expansion."
    )


def _generate_divergence_reason(branch_type: str, decision: str, divergence_score: float, parent_decision: str = None, keywords: list = None) -> str:
    """
    Explains the exact causal mechanics driving timeline drift, specifically contrasting
    the current injected decision against the parent baseline.
    """
    k1 = keywords[0] if (keywords and len(keywords) > 0) else "the injected parameters"
    p_dec = parent_decision if parent_decision else "the baseline ancestral state"
    
    if branch_type == "stable_growth":
        return (
            f"Controlled trajectory shift of {divergence_score:.2f} triggered by the introduction of '{decision[:50]}...'. "
            f"This measured step introduces a localized variation in {k1} relative to the parent stance of '{p_dec[:50]}...', "
            f"allowing branch evolution without breaking core structural limits."
        )
    elif branch_type == "high_risk_growth":
        return (
            f"Significant trajectory divergence of {divergence_score:.2f} driven by rapid acceleration of '{decision[:50]}...'. "
            f"This choice introduces extreme variance when compared to the parent baseline of '{p_dec[:50]}...', "
            f"pushing {k1} parameters past the standard dampening envelope and into active bifurcation."
        )
    elif branch_type == "systemic_collapse":
        return (
            f"Catastrophic path divergence of {divergence_score:.2f} caused by severe structural shock from '{decision[:50]}...'. "
            f"By directly conflicting with the parent baseline of '{p_dec[:50]}...', this decision overloads the "
            f"system's capacity, fracturing the timeline's coherence."
        )
        
    return (
        f"Standard divergence of {divergence_score:.2f} caused by the transition from the parent state ('{p_dec[:50]}...') "
        f"to the current state ('{decision[:50]}...'), introducing normal drift in {k1}."
    )


# ==========================================================
# WEBSOCKET EMITTER
# ==========================================================

def emit_websocket_event(timeline_id: str, payload: dict):
    """
    Issues a synchronous HTTP POST request to Django's WebSocket broadcast bridge
    to relay AI events to the React client in real-time.
    """
    url = f"{DJANGO_URL.rstrip('/')}/api/timelines/broadcast/"
    try:
        last_error = None
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    url,
                    json={
                        "timeline_id": timeline_id,
                        "payload": payload
                    },
                    timeout=2.0
                )
                response.raise_for_status()
                return
            except requests.exceptions.HTTPError as err:
                print(
                    f"[WS AI EMITTER ERROR] Django broadcast returned "
                    f"{response.status_code}: {response.text[:500]}"
                )
                return
            except requests.exceptions.RequestException as err:
                last_error = err
                if attempt < 3:
                    time.sleep(0.5 * attempt)
        print(f"[WS AI EMITTER ERROR] Failed to emit WebSocket event after retries: {last_error}")
    except Exception as err:
        print(f"[WS AI EMITTER ERROR] Failed to emit WebSocket event: {err}")


# ==========================================================
# FALLBACK SUMMARY GENERATOR
# ==========================================================

def get_fallback_summary(decision: str, divergence_score: float, depth_level: int, branch_name: str, branch_type: str = None, keywords: list = None, inherited_risks: list = None) -> str:
    """
    Generates a high-precision, user-friendly fallback summary when the external Hugging Face LLM is unavailable.
    Weaves in extracted keywords and ancestral contexts.
    """
    decision_clean = decision.strip() if decision else ""
    k1 = keywords[0].capitalize() if (keywords and len(keywords) > 0) else "the alternate trajectory"
    k2 = keywords[1] if (keywords and len(keywords) > 1) else "system parameters"
    
    inherited_str = ""
    if inherited_risks:
        inherited_str = " Building on prior ancestral vulnerabilities,"

    if branch_type == "stable_growth":
        return (
            f"Deploying '{decision_clean[:60]}...' initiates a stable trajectory driven by {k1}. "
            f"{inherited_str} Operations show a highly controlled deviation, preserving critical buffer capacity "
            f"and locking in steady long-term progress with a minimal divergence of {divergence_score:.2f}."
        )
    elif branch_type == "high_risk_growth":
        return (
            f"Selecting '{decision_clean[:60]}...' triggers a rapid, high-momentum acceleration in {k1}. "
            f"{inherited_str} While this path opens valuable breakthrough windows, it introduces massive structural complexity "
            f"in {k2}, pushing divergence to {divergence_score:.2f} and risking sudden systemic volatility."
        )
    elif branch_type == "systemic_collapse":
        return (
            f"The decision to '{decision_clean[:60]}...' causes severe structural shock to our {k1}. "
            f"{inherited_str} This path triggers a cascading failure sequence across dependent {k2} systems, "
            f"culminating in critical degradation and timeline collapse at a divergence of {divergence_score:.2f}."
        )
        
    return (
        f"This timeline branch explores '{decision_clean[:60]}...'. "
        f"It shifts from the parent state, introducing moderate variations in {k1} and establishing a new alternative path."
    )


def clean_llm_output(output_text: str, prompt: str) -> str:
    """
    Clean raw text returned from Hugging Face Inference API.
    """
    if prompt in output_text:
        output_text = output_text.replace(prompt, "")
        
    if "Output:" in output_text:
        output_text = output_text.split("Output:")[-1]
    if "Instruct:" in output_text:
        output_text = output_text.split("Instruct:")[0]

    output_text = output_text.strip()
    output_text = re.sub(r'\s+', ' ', output_text)
    
    sentences = re.split(r'(?<=[.!?])\s+', output_text)
    clean_sentences = [s.strip() for s in sentences if s.strip()]
    
    final_text = " ".join(clean_sentences[:2])
    
    if len(final_text) < 15:
        return ""
        
    return final_text


# ==========================================================
# CORE SUMMARY GENERATION PIPELINE
# ==========================================================

def generate_timeline_summary(timeline_id: str, branch_id: str, simulation_id: str) -> dict:
    """
    Orchestrates the ChronoShift AI summary generation flow:
    1. Reconstructs ancestral branch trajectory up to the timeline root (Ancestry Traversal).
    2. Extracts semantic keywords from decision strings, filtering out common stop words.
    3. Calculates heuristic quant-grade risk and confidence scores.
    4. Assembles dynamic timeline-aware prompts using LangChain templates.
    5. Calls the external Hugging Face serverless API using microsoft/phi-2.
    6. Falls back to a high-fidelity, keyword-rich template fallback on failure.
    7. Generates non-overlapping analytical sections (Risk, Opportunity, stability, etc.).
    8. Persists the final outcome to MongoDB Atlas under `ai_summaries` collection.
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
            pass

    # Fetch context documents
    timeline = timelines_collection.find_one({"_id": t_id_obj})
    
    if branch_id == 'root':
        branch = {
            "branch_name": "Main Root Core",
            "decision_trigger": "Initial timeline setup parameters.",
            "divergence_score": 0.0,
            "depth_level": 1,
            "parent_branch_id": None,
            "branch_type": None
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
    branch_type = branch.get("branch_type", None)

    # 1. ANCESTRY TRAVERSAL (Memory Consistency)
    ancestry_data = _get_branch_ancestry(branch_id, timeline_id)
    history_summary = ancestry_data["history_summary_str"]
    inherited_risks = ancestry_data["inherited_risks"]
    event_progression = ancestry_data["event_progression"]
    
    # 2. KEYWORD SEMANTIC EXTRACTION
    current_keywords = _extract_keywords(decision)
    all_path_keywords = []
    for d in event_progression:
        all_path_keywords.extend(_extract_keywords(d))
    # Keep unique path keywords
    seen_kw = set()
    unique_path_keywords = [k for k in all_path_keywords if not (k in seen_kw or seen_kw.add(k))]

    # Get parent decision context
    parent_decision = "Root node launch configuration"
    if len(event_progression) > 1:
        parent_decision = event_progression[-2] # Second to last is parent

    # Fetch prior AI summaries within the timeline to maintain narrative continuity
    prior_context_str = ""
    try:
        prior_summaries = list(ai_summaries_collection.find({"timeline_id": timeline_id}).sort("generated_at", -1).limit(2))
        if prior_summaries:
            priors = [f"- {s.get('summary')}" for s in prior_summaries if s.get("summary")]
            prior_context_str = "\n".join(priors)
    except Exception as e:
        print(f"[AI WARNING] Could not retrieve prior summaries: {e}")

    # HEURISTIC CALCULATIONS
    risk_score = round(min(1.0, max(0.0, (divergence_score * 0.7) + (depth_level * 0.05))), 2)
    confidence_score = round(min(1.0, max(0.0, 1.0 - (divergence_score * 0.4) - (depth_level * 0.03))), 2)

    # LANGCHAIN PROMPT ORCHESTRATION (Upgrade Hugging Face Prompts to be Timeline-Aware)
    template = """Instruct: You are ChronoShift's premium AI Narrative Intelligence Engine.
Analyze the following alternate timeline parameters and generate a highly professional, causal, and timeline-aware 1-to-2 sentence narrative.
Describe what happens in this alternate future scenario by weaving in the current decision and ancestor trajectory keywords.
Adopt an analytical, quant-grade, intelligent tone (Bloomberg-terminal style). Focus on systemic impacts and cause-and-effect.

Timeline Base Context:
- Title: {timeline_title}
- Core Focus: {timeline_desc}

Ancestral Path History (Traversed Trajectory):
{history_summary}

Inherited Path Instabilities:
{inherited_risks_str}

Current State & Decision:
- Branch Name: {branch_name}
- Injected Decision: {decision}
- Branch Archetype: {branch_type}
- Divergence Magnitude: {divergence_score}
- Hierarchy Depth: {depth_level}
- Extracted Semantic Keywords: {extracted_keywords}

Prior Segment Summary (Narrative Continuity):
{prior_context}

Provide the explanation in exactly 1 or 2 sentences. Focus on high-fidelity causal consequences. Avoid conversational filler or introductory phrases.
Output: """

    prompt_template = PromptTemplate(
        input_variables=[
            "timeline_title",
            "timeline_desc",
            "history_summary",
            "inherited_risks_str",
            "branch_name",
            "decision",
            "branch_type",
            "divergence_score",
            "depth_level",
            "extracted_keywords",
            "prior_context"
        ],
        template=template
    )

    inherited_risks_str = "; ".join(inherited_risks) if inherited_risks else "No inherited prior branch instabilities detected."
    extracted_keywords_str = ", ".join(current_keywords) if current_keywords else "None"

    prompt = prompt_template.format(
        timeline_title=timeline_title,
        timeline_desc=timeline_desc,
        history_summary=history_summary,
        inherited_risks_str=inherited_risks_str,
        branch_name=branch_name,
        decision=decision,
        branch_type=branch_type if branch_type else "standard",
        divergence_score=divergence_score,
        depth_level=depth_level,
        extracted_keywords=extracted_keywords_str,
        prior_context=prior_context_str if prior_context_str else "No prior summaries generated yet."
    )

    # ==========================================================
    # HUGGING FACE INFERENCE CALL (WITH RESILIENT FALLBACK)
    # ==========================================================
    summary_text = ""
    api_success = False

    if AI_REMOTE_ENABLED and HF_TOKEN and MODEL_NAME:
        url = f"https://api-inference.huggingface.co/models/{MODEL_NAME}"
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": 80,
                "temperature": 0.4,
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
        summary_text = get_fallback_summary(
            decision=decision,
            divergence_score=divergence_score,
            depth_level=depth_level,
            branch_name=branch_name,
            branch_type=branch_type,
            keywords=current_keywords,
            inherited_risks=inherited_risks
        )
        print(f"[AI FALLBACK RESULT] Generated fallback: '{summary_text}'")

    # ==========================================================
    # GENERATE STRUCTURED REPORT FIELDS
    # ==========================================================
    event_evolution = _generate_event_evolution(
        decision=decision,
        branch_type=branch_type,
        divergence_score=divergence_score,
        keywords=current_keywords,
        inherited_risks=inherited_risks
    )
    risk_analysis = _generate_risk_analysis(
        branch_type=branch_type,
        divergence_score=divergence_score,
        keywords=current_keywords,
        inherited_risks=inherited_risks
    )
    opportunity_analysis = _generate_opportunity_analysis(
        branch_type=branch_type,
        decision=decision,
        keywords=current_keywords
    )
    timeline_stability = _generate_timeline_stability(
        branch_type=branch_type,
        divergence_score=divergence_score
    )
    divergence_reason = _generate_divergence_reason(
        branch_type=branch_type,
        decision=decision,
        divergence_score=divergence_score,
        parent_decision=parent_decision,
        keywords=current_keywords
    )
    strategic_outlook = _generate_strategic_outlook(
        branch_type=branch_type,
        decision=decision,
        divergence_score=divergence_score,
        keywords=current_keywords
    )

    # ==========================================================
    # MONGO PERSISTENCE LAYER
    # ==========================================================
    existing_summary = ai_summaries_collection.find_one({"branch_id": branch_id})

    report_fields = {
        "risk_score": risk_score,
        "confidence_score": confidence_score,
        "summary": summary_text,
        "branch_type": branch_type,
        "future_outlook": summary_text,
        "risk_analysis": risk_analysis,
        "opportunity_analysis": opportunity_analysis,
        "timeline_stability": timeline_stability,
        "divergence_reason": divergence_reason,
        "strategic_outlook": strategic_outlook,
        "event_evolution": event_evolution,
        "generated_at": datetime.utcnow()
    }

    if existing_summary:
        ai_summaries_collection.update_one(
            {"_id": existing_summary["_id"]},
            {"$set": report_fields}
        )
        summary_id = str(existing_summary["_id"])
        print(f"[DATABASE] Updated existing AI summary document: '{summary_id}'")
    else:
        summary_doc = {
            "timeline_id": timeline_id,
            "branch_id": branch_id,
            "simulation_id": simulation_id,
            **report_fields
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
        "summary": summary_text,
        "branch_type": branch_type,
        "future_outlook": summary_text,
        "risk_analysis": risk_analysis,
        "opportunity_analysis": opportunity_analysis,
        "timeline_stability": timeline_stability,
        "divergence_reason": divergence_reason,
        "strategic_outlook": strategic_outlook,
        "event_evolution": event_evolution
    }
