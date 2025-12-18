# tools/agent_tools.py

def search_masters_tool(user_query: str):
    """
    USE THIS TOOL when the user asks for recommendations, suggestions, or information 
    about master's degree programs, universities, tuition fees, or courses.
    
    Args:
        user_query: The specific topic the user is interested in (e.g. "Data Science", "Marketing").
    """
    # 1. LAZY IMPORTS (Crucial to avoid Circular Import errors)
    from ai.ai_client import AIClient
    from services.db_service import DatabaseService
    
    # 2. SETUP (Initialize connections inside the tool)
    # use_tools=False prevents the AIClient from trying to load tools recursively
    ai_client = AIClient()
    db_service = DatabaseService()
    collection = db_service.masters()

    # 3. GENERATE EMBEDDING (Logic extracted from EmbeddingService)
    # The AI Client returns the list of floats directly
    user_emb = ai_client.embed(user_query)

    # 4. VECTOR SEARCH (Logic extracted from EmbeddingService)
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

    # Execute search
    try:
        cursor = collection.aggregate(pipeline)
        results = list(cursor)
    except Exception as e:
        return f"Error connecting to database: {e}"

    if not results:
        return "No masters found in the database."

    # 5. FORMAT OUTPUT (Convert JSON to String for the LLM)
    output_text = f"Found {len(results)} programs for '{user_query}':\n\n"
    
    for doc in results:
        # We process the score and fields here
        score = doc.get("score", 0.0)
        
        # We construct a readable block of text for the Gemini Agent
        output_text += (
            f"- MASTER: {doc.get('master', 'N/A')}\n"
            f"  University: {doc.get('university', 'N/A')}\n"
            f"  Tuition Fee: {doc.get('Tuition Fee', 'N/A')}\n"
            f"  Location: {doc.get('Location', 'N/A')}\n"
            f"  Match Score: {score:.4f}\n" 
            f"  About: {doc.get('about', '')[:200]}...\n\n" # Truncate long descriptions
        )
    
    return output_text

def get_map_link_tool(university_name: str):
    """
    USE THIS TOOL when the user specifically asks for a map, location link, 
    or where a university is located geographically.
    """
    # Lazy Import
    from services.location_service import LocationService
    
    service = LocationService()
    link = service.get_location_link(university_name)
    
    if link:
        return f"Google Maps Link: {link}"
    return "Location link not found in database."

# List of tools to export
my_toolbox = [search_masters_tool, get_map_link_tool]