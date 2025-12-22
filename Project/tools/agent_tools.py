from __future__ import annotations
from langfuse import observe
import re

"""
Agent Tools Module.

This module defines the specific "skills" (functions) available to the AI Agent.
These tools bridge the gap between the LLM's reasoning and the application's data.
Critically, they handle the 'Hybrid Search' logic—combining semantic vector retrieval 
with strict deterministic filtering (e.g., Budget < X) to ensure accuracy.
"""

def _tool_observation(tool_name: str, input_data: dict):
    """
    Helper to start a Langfuse observation span for tool calls.
    Returns None if observability is disabled/misconfigured.
    """
    try:
        from utils.observability import get_langfuse
        langfuse = get_langfuse()
        if not langfuse:
            return None

        return langfuse.start_as_current_observation(
            as_type="span",
            name=f"tool:{tool_name}",
            input=input_data,
        )
    except Exception:
        return None


def parse_tuition_value(tuition_str: str) -> float:
    """
    Utility to normalize tuition fee strings into float values for comparison.
    Handles various formats like '1 250 EUR', '30.000', or '1500 / year'.
    """
    if not tuition_str or not isinstance(tuition_str, str):
        return 0.0
    
    # Normalize: Remove spaces (common in EU number formatting) and replace commas with dots
    clean_str = tuition_str.replace(" ", "").replace(",", ".")
    
    # Extract the first sequence of digits found
    match = re.search(r"(\d+)", clean_str)
    if match:
        return float(match.group(1))
    return 0.0


@observe(name="tool_search_masters")
def search_masters_tool(user_query: str, max_budget: int = None, preferred_location: str = None, preferred_duration: str = None):
    """
    CORE RAG TOOL: Performs a Hybrid Search for Master's programs.
    
    Strategy:
    1. Retrieval: Semantic Vector Search to find the top 50 matches for the topic.
    2. Filtering: Strict Python-based filtering for Budget, Location, and Duration.
    3. Ranking: Prioritizes exact matches, falling back to 'close matches' if necessary.

    Args:
        user_query (str): The semantic topic (e.g. "Marketing", "Artificial Intelligence").
        max_budget (int): Hard limit for tuition fees (EUR).
        preferred_location (str): Target city or region (e.g. "Lisbon").
        preferred_duration (str): Target duration (e.g. "2 years").
    """
    # Start tracing span
    obs = _tool_observation("search_masters_tool", {
        "user_query": user_query, 
        "max_budget": max_budget,
        "location": preferred_location,
        "duration": preferred_duration
    })

    # Lazy imports to avoid circular dependencies during app startup
    from ai.ai_client import AIClient
    from services.db_service import DatabaseService

    def _run():
        ai_client = AIClient(use_tools=False)
        db_service = DatabaseService()
        collection = db_service.masters()

        # Step 1: Generate Embedding for the user's query
        user_emb = ai_client.embed(user_query)

        # Step 2: Vector Search (Semantic Retrieval)
        # We fetch a LARGE pool (top_k=50) to maximize the chance of finding programs 
        # that satisfy the strict constraints in the next step.
        top_k = 50 
        pipeline = [
            {"$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": user_emb,
                "numCandidates": top_k * 10,
                "limit": top_k,
            }},
            # Project only necessary fields and the search score
            {"$project": {"embedding": 0, "score": {"$meta": "vectorSearchScore"}}}
        ]

        raw_results = list(collection.aggregate(pipeline))

        if not raw_results:
            return {"text": "No programs found in the database.", "raw_data": []}

        # Step 3: Python-Side Deterministic Filtering
        exact_matches = []
        close_matches = []

        for doc in raw_results:
            doc["_id"] = str(doc.get("_id"))
            
            is_match = True
            reasons = []

            # -- Constraint: Budget --
            if max_budget:
                fee_str = doc.get("Tuition Fee") or doc.get("tuition", "")
                cost = parse_tuition_value(fee_str)
                # Apply a 10% tolerance margin to avoid filtering borderline cases
                if cost > (max_budget * 1.1): 
                    is_match = False
                    reasons.append(f"Over budget ({fee_str})")

            # -- Constraint: Location --
            if preferred_location:
                loc = doc.get("Location") or doc.get("location", "")
                # Simple substring match (case-insensitive)
                if preferred_location.lower() not in loc.lower():
                    is_match = False
                    reasons.append(f"Wrong location ({loc})")
            
            # -- Constraint: Duration --
            if preferred_duration:
                dur = doc.get("Duration") or doc.get("duration", "")
                if preferred_duration.lower() not in dur.lower():
                     is_match = False
                     reasons.append(f"Duration mismatch ({dur})")

            # -- Categorization --
            if is_match:
                exact_matches.append(doc)
            else:
                # Store reason for rejection to potentially explain to the user later
                doc["missed_criteria"] = ", ".join(reasons)
                close_matches.append(doc)

        # Step 4: Final Selection & Safety Net
        # Priority: Return up to 5 Exact Matches
        final_results = exact_matches[:5]
        
        # Fallback: If strict constraints killed all results, return the "closest" ones
        # This prevents the "I found nothing" dead-end experience.
        safety_net_triggered = False
        if not final_results:
            safety_net_triggered = True
            final_results = close_matches[:3]

        # Step 5: Format Output for the LLM
        # We construct a text summary for the LLM to "read", and pass the raw dicts 
        # separately in 'raw_data' for the UI to render.
        summary = ""
        if safety_net_triggered:
            summary += f"⚠️ NO EXACT MATCHES FOUND for budget < {max_budget}, {preferred_location}, {preferred_duration}.\n"
            summary += "Here are the closest alternatives (please check why they didn't match):\n\n"
        else:
            summary += f"✅ Found {len(exact_matches)} programs matching all criteria:\n"

        for doc in final_results:
            summary += f"- {doc.get('master')} at {doc.get('university')}\n"
            summary += f"  Location: {doc.get('Location')} | Fee: {doc.get('Tuition Fee')} | Duration: {doc.get('Duration')}\n"
            if "missed_criteria" in doc:
                summary += f"  (Note: {doc['missed_criteria']})\n"
            summary += "\n"

        return {"text": summary, "raw_data": final_results}

    # Execute with observability handling
    try:
        if obs:
            with obs as span:
                return _run()
        else:
            return _run()
    except Exception as e:
        return f"Error: {e}"


@observe(name="tool_get_map_link")
def get_map_link_tool(university_name: str):
    """
    Retrieves the Google Maps URL for a specific university via the LocationService.
    """
    obs = _tool_observation("get_map_link_tool", {"university_name": university_name})

    def _run():
        from services.location_service import LocationService
        service = LocationService()
        link = service.get_location_link(university_name)
        return link

    # Error handling wrapper to prevent agent crash on DB failure
    if obs is None:
        try:
            link = _run()
            if link:
                return f"Google Maps Link: {link}"
            return "Location link not found in database."
        except Exception as e:
            return f"Error in get_map_link_tool: {e}"

    try:
        with obs as span:
            link = _run()
            span.update(output={"found": bool(link)})
            if link:
                return f"Google Maps Link: {link}"
            return "Location link not found in database."
    except Exception as e:
        try:
            span.update(metadata={"error": str(e)}) 
        except Exception:
            pass
        return f"Error in get_map_link_tool: {e}"


@observe(name="tool_final_recommendations")
def final_recommendations_tool(programs: list[dict]):
    """
    UI SIGNALING TOOL.
    
    This tool does not perform logic. Instead, the Agent calls it to signal 
    that it has selected specific programs to recommend. 
    
    The backend/frontend intercepts the 'raw_data' from this tool call 
    to render the "Recommended Programs" cards in the UI.
    
    Args:
        programs (list[dict]): The list of selected program dictionaries found by search_masters_tool.
    """
    obs = _tool_observation("final_recommendations_tool", {"count": len(programs)})
    
    # Echo the data back. The key is 'raw_data', which the frontend looks for.
    summary = f"Displaying {len(programs)} recommendations to the user."
    return {"text": summary, "raw_data": programs}

# Export the tools list for the AI Client
my_toolbox = [search_masters_tool, get_map_link_tool, final_recommendations_tool]