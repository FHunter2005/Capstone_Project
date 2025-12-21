from __future__ import annotations
from langfuse import observe

# --- 1. NEW GLOBAL BUFFER (The "Mailbox") ---
RESULTS_BUFFER = []

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

@observe(name="tool_search_masters")
def search_masters_tool(user_query: str):
    """
    USE THIS TOOL when the user asks for recommendations, suggestions, or information
    about master's degree programs.
    """
    # --- 2. TELL FUNCTION TO USE THE GLOBAL BUFFER ---
    global RESULTS_BUFFER
    
    obs = _tool_observation("search_masters_tool", {"user_query": user_query})

    # Lazy Imports (keeps Streamlit reloads happier)
    from ai.ai_client import AIClient
    from services.db_service import DatabaseService
    # We still import streamlit to avoid breaking old logic, but we won't rely on it for the API
    import streamlit as st 

    def _run():
        # Initialize "Lightweight" Client
        ai_client = AIClient(use_tools=False)
        db_service = DatabaseService()
        collection = db_service.masters()

        # Generate Embedding
        user_emb = ai_client.embed(user_query)

        # Vector Search
        top_k = 5
        pipeline = [
            {
                "$vectorSearch": {
                    "index": "vector_index",
                    "path": "embedding",
                    "queryVector": user_emb,
                    "numCandidates": top_k * 20,
                    "limit": top_k,
                }
            },
            {
                "$project": {
                    "embedding": 0,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ]

        cursor = collection.aggregate(pipeline)
        results = list(cursor)

        if not results:
            return "No masters found in the database.", []

        # --- 3. THE FIX: SAVE TO BUFFER INSTEAD OF SESSION STATE ---
        # Clear any old data
        RESULTS_BUFFER.clear()
        # Add the new results so the Backend can see them
        RESULTS_BUFFER.extend(results)
        
        # (Optional) We keep this for local testing, but the API ignores it:
        try:
            if st.session_state:
                st.session_state["last_recommended_masters"] = results
        except:
            pass
        # -----------------------------------------------------------

        output_text = f"Found {len(results)} programs for '{user_query}':\n\n"
        for doc in results:
            score = doc.get("score", 0.0)
            output_text += (
                f"- MASTER: {doc.get('master', 'N/A')}\n"
                f"  University: {doc.get('university', 'N/A')}\n"
                f"  Tuition Fee: {doc.get('Tuition Fee', 'N/A')}\n"
                f"  Location: {doc.get('Location', 'N/A')}\n"
                f"  Match Score: {score:.4f}\n"
                f"  About: {str(doc.get('about', ''))[:200]}...\n\n"
            )

        return output_text, results

    # If Langfuse disabled, just run normally
    if obs is None:
        try:
            text, _results = _run()
            return text
        except Exception as e:
            return f"Error in search_masters_tool: {e}"

    # Langfuse enabled: run inside observation context
    try:
        with obs as span:
            text, results = _run()
            span.update(output={"result_count": len(results)})
            return text
    except Exception as e:
        try:
            span.update(metadata={"error": str(e)})  # type: ignore[name-defined]
        except Exception:
            pass
        return f"Error in search_masters_tool: {e}"


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
            span.update(metadata={"error": str(e)})  # type: ignore[name-defined]
        except Exception:
            pass
        return f"Error in get_map_link_tool: {e}"


my_toolbox = [search_masters_tool, get_map_link_tool]