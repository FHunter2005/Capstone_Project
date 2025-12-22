from __future__ import annotations
from langfuse import observe
import re

def _tool_observation(tool_name: str, input_data: dict):
    """
    Starts a Langfuse observation span for a tool call, if Langfuse is enabled.
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

# Project/tools/agent_tools.py

# ... (keep _tool_observation function as is) ...

def parse_tuition_value(tuition_str: str) -> float:
    """
    Extracts the numeric value from strings like '1250 EUR / year' or '30 000 EUR'.
    Returns a float or a high number if not found.
    """
    if not tuition_str or not isinstance(tuition_str, str):
        return 0.0
    
    # Remove spaces (e.g. "30 000") and look for digits
    clean_str = tuition_str.replace(" ", "").replace(",", ".")
    match = re.search(r"(\d+)", clean_str)
    if match:
        return float(match.group(1))
    return 0.0

@observe(name="tool_search_masters")
def search_masters_tool(user_query: str, max_budget: int = None, preferred_location: str = None, preferred_duration: str = None):
    """
    USE THIS TOOL to find master's programs.
    
    Args:
        user_query: The topic or field of study (e.g. "Marketing", "AI").
        max_budget: The maximum tuition fee allowed (in EUR).
        preferred_location: The city or region (e.g. "Lisbon").
        preferred_duration: The duration (e.g. "2 years").
    """
    obs = _tool_observation("search_masters_tool", {
        "user_query": user_query, 
        "max_budget": max_budget,
        "location": preferred_location,
        "duration": preferred_duration
    })

    from ai.ai_client import AIClient
    from services.db_service import DatabaseService

    def _run():
        ai_client = AIClient(use_tools=False)
        db_service = DatabaseService()
        collection = db_service.masters()

        user_emb = ai_client.embed(user_query)

        # 1. Fetch a LARGER pool of candidates (e.g. 50) based on semantic similarity
        #    We filter them using Python logic below to ensure strict compliance.
        top_k = 50 
        pipeline = [
            {"$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": user_emb,
                "numCandidates": top_k * 10,
                "limit": top_k,
            }},
            {"$project": {"embedding": 0, "score": {"$meta": "vectorSearchScore"}}}
        ]

        raw_results = list(collection.aggregate(pipeline))

        if not raw_results:
            return {"text": "No programs found in the database.", "raw_data": []}

        # 2. Filter and Rank Results in Python
        exact_matches = []
        close_matches = []

        for doc in raw_results:
            doc["_id"] = str(doc.get("_id"))
            
            # --- Check Constraints ---
            is_match = True
            reasons = []

            # Check Budget
            if max_budget:
                fee_str = doc.get("Tuition Fee") or doc.get("tuition", "")
                cost = parse_tuition_value(fee_str)
                # If cost > budget + 10% tolerance, fail
                if cost > (max_budget * 1.1): 
                    is_match = False
                    reasons.append(f"Over budget ({fee_str})")

            # Check Location (Partial string match)
            if preferred_location:
                loc = doc.get("Location") or doc.get("location", "")
                if preferred_location.lower() not in loc.lower():
                    is_match = False
                    reasons.append(f"Wrong location ({loc})")
            
            # Check Duration
            if preferred_duration:
                dur = doc.get("Duration") or doc.get("duration", "")
                # Simple check: if user wants "1 year" and course is "2 years", that's a mismatch
                if preferred_duration.lower() not in dur.lower():
                     # Allow slight flexibility (e.g. "2 years" fits "1-2 years") could be added here
                     is_match = False
                     reasons.append(f"Duration mismatch ({dur})")

            # --- Categorize ---
            if is_match:
                exact_matches.append(doc)
            else:
                # Only keep close matches that have high semantic relevance (score)
                # or failed only 1-2 criteria.
                doc["missed_criteria"] = ", ".join(reasons)
                close_matches.append(doc)

        # 3. Construct the Response
        # Priority: Exact Matches -> Top 5
        final_results = exact_matches[:5]
        
        # Safety Net: If no exact matches, pick top close matches
        safety_net_triggered = False
        if not final_results:
            safety_net_triggered = True
            final_results = close_matches[:3] # Suggest top 3 alternatives

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

    try:
        if obs:
            with obs as span:
                return _run()
        else:
            return _run()
    except Exception as e:
        return f"Error: {e}"

# ... (keep get_map_link_tool and my_toolbox definition) ...

@observe(name="tool_get_map_link")
def get_map_link_tool(university_name: str):
    obs = _tool_observation("get_map_link_tool", {"university_name": university_name})

    def _run():
        from services.location_service import LocationService
        service = LocationService()
        link = service.get_location_link(university_name)
        return link

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
    STEP 2: USE THIS TOOL to display the FINAL selection of programs to the user.
    Input: 'programs' -> A list of the program dictionaries you selected from the search results.
    Each dictionary MUST contain: 'master', 'university', 'Location', 'Tuition Fee'.
    """
    obs = _tool_observation("final_recommendations_tool", {"count": len(programs)})
    
    # This simply "echoes" the data so the Frontend can see it in 'raw_data'
    summary = f"Displaying {len(programs)} recommendations to the user."
    return {"text": summary, "raw_data": programs}

my_toolbox = [search_masters_tool, get_map_link_tool, final_recommendations_tool]