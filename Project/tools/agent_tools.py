from __future__ import annotations
from langfuse import observe


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

@observe(name="tool_search_masters")
def search_masters_tool(user_query: str):
    """
    USE THIS TOOL when the user asks for recommendations, suggestions, or information
    about master's degree programs in Portugal.
    """
    obs = _tool_observation("search_masters_tool", {"user_query": user_query})

    from ai.ai_client import AIClient
    from services.db_service import DatabaseService

    def _run():
        ai_client = AIClient(use_tools=False)
        db_service = DatabaseService()
        collection = db_service.masters()

        user_emb = ai_client.embed(user_query)

        top_k = 5
        pipeline = [
            {"$vectorSearch": {
                "index": "vector_index",
                "path": "embedding",
                "queryVector": user_emb,
                "numCandidates": top_k * 20,
                "limit": top_k,
            }},
            {"$project": {"embedding": 0, "score": {"$meta": "vectorSearchScore"}}}
        ]

        results = list(collection.aggregate(pipeline))

        if not results:
            return "No programs found.", []

        # Create a string representation for the AI to "read"
        summary = f"Found {len(results)} programs:\n"
        for doc in results:
            summary += f"- {doc.get('master')} at {doc.get('university')} (Score: {doc.get('score', 0):.2f})\n"
        
        # Return a dictionary containing both the text and the raw data
        return {"text": summary, "raw_data": results}

    try:
        if obs:
            with obs as span:
                output = _run()
                span.update(output={"count": len(output[1]) if isinstance(output, tuple) else 0})
                return output["text"] if isinstance(output, dict) else output
        else:
            res = _run()
            return res["text"] if isinstance(res, dict) else res
    except Exception as e:
        return f"Error: {e}"

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

my_toolbox = [search_masters_tool, get_map_link_tool]