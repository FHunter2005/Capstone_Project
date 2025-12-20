# tools/agent_tools.py

def search_masters_tool(user_query: str):
    """
    USE THIS TOOL when the user asks for recommendations, suggestions, or information 
    about master's degree programs.
    """
    # Lazy Imports
    from ai.ai_client import AIClient
    from services.db_service import DatabaseService
    import streamlit as st  # Import Streamlit to access Session State
    
    # Initialize "Lightweight" Client
    ai_client = AIClient(use_tools=False)
    db_service = DatabaseService()
    collection = db_service.masters()

    # Generate Embedding
    try:
        user_emb = ai_client.embed(user_query)
    except Exception as e:
        return f"Error generating embedding: {e}"

    # Vector Search
    top_k = 5
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index", 
                "path": "embedding",   
                "queryVector": user_emb,    
                "numCandidates": top_k * 20, 
                "limit": top_k                
            }
        },
        {
            "$project": {
                "embedding": 0, 
                "score": {"$meta": "vectorSearchScore"} 
            }
        }
    ]

    try:
        cursor = collection.aggregate(pipeline)
        results = list(cursor)
    except Exception as e:
        return f"Error connecting to database: {e}"

    if not results:
        return "No masters found in the database."

    st.session_state['last_recommended_masters'] = results

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
    
    return output_text

def get_map_link_tool(university_name: str):
    from services.location_service import LocationService
    service = LocationService()
    link = service.get_location_link(university_name)
    if link:
        return f"Google Maps Link: {link}"
    return "Location link not found in database."

my_toolbox = [search_masters_tool, get_map_link_tool]