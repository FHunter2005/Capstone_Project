# master_chat_app.py
import streamlit as st
from pymongo import MongoClient
import numpy as np
from google import genai
import os
from dotenv import load_dotenv
import re
from google.genai import types

# -----------------------------
# Load environment variables
# -----------------------------
load_dotenv()

# -----------------------------
# MongoDB connection
# -----------------------------
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")
client = MongoClient(MONGO_URI)
db = client[MONGO_DB]
masters_collection = db.Masters
maps_collection = db.Maps_Location

# -----------------------------
# Google GenAI client
# -----------------------------
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ai_client = genai.Client(api_key=GOOGLE_API_KEY)
EMBED_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.5-flash"  # or another available model

# -----------------------------
# Streamlit layout
# -----------------------------
st.title("🎓 Master's Programs Finder")
st.markdown("Ask me about master's programs and I'll find matching programs for you.")

# -----------------------------
# Initialize session state
# -----------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.info(
        "👋 Welcome — ask about your interests and I'll find matching master's programs. "
        "Data comes from your MongoDB Atlas collection."
    )

# -----------------------------
# Helper functions
# -----------------------------
def generate_embedding(text: str):
    resp = ai_client.models.embed_content(
        model=EMBED_MODEL,
        contents=[text]
    )
    return np.array(resp.embeddings[0].values)

def cosine_similarity(a, b):
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return np.dot(a, b) / (norm_a * norm_b)

def ensure_embeddings():
    for doc in masters_collection.find():
        if "embedding" not in doc or not doc["embedding"]:
            text_to_embed = doc.get("about", doc.get("master", ""))
            if text_to_embed:
                emb = generate_embedding(text_to_embed)
                masters_collection.update_one({"_id": doc["_id"]}, {"$set": {"embedding": emb.tolist()}})

def search_master_programs(user_emb, top_k=5):
    results = []
    for doc in masters_collection.find():
        emb = np.array(doc.get("embedding", []))
        if emb.size == 0:
            continue
        score = cosine_similarity(user_emb, emb)
        results.append((score, doc))
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:top_k]]

def get_location_link(university_name):
    doc = maps_collection.find_one({"Institution": {"$regex": f"^{re.escape(university_name)}$", "$options": "i"}})
    if doc and "GoogleMaps" in doc:
        return doc["GoogleMaps"]
    return None

def keyword_fallback_search(query):
    regex = re.compile(re.escape(query), re.IGNORECASE)
    return list(masters_collection.find({"master": {"$regex": regex}}))[:5]

def elaborate_answer(master_doc, user_query):
    """Use AI to generate a fluent and elaborated answer about a master program."""
    about_text = master_doc.get("about", "No description available.")
    prompt = (
        f"You are an expert educational advisor. A user asked: '{user_query}'.\n"
        f"Based on the following program information, provide a detailed, engaging, "
        f"and natural explanation of why this program might be interesting for the user, "
        f"what they would learn, and any other helpful insights.\n\n"
        f"Master Program: {master_doc.get('master')}\n"
        f"University: {master_doc.get('university')}\n"
        f"Location: {master_doc.get('Location', 'Not available')}\n"
        f"Duration: {master_doc.get('Duration', 'Not available')}\n"
        f"Tuition Fee: {master_doc.get('Tuition Fee', 'Not available')}\n"
        f"About: {about_text}\n"
    )
    response = ai_client.models.generate_content(
        model=LLM_MODEL,
        contents=[prompt],
        config=types.GenerateContentConfig(
            temperature=0.7,
            max_output_tokens=400
        )
    )
    # SDK returns a list of items in `response.candidates`
    if hasattr(response, "candidates") and response.candidates:
        return response.candidates[0].content
    else:
        return "No elaborated text available."


# -----------------------------
# Ensure all masters have embeddings
# -----------------------------
ensure_embeddings()

# -----------------------------
# Chat input
# -----------------------------
user_input = st.text_input(
    "Ask me about master's programs or specific details:",
    placeholder="Tell me your goals, interests, or preferred study area..."
)

# -----------------------------
# Chat logic
# -----------------------------
if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Check for a specific master reference
    master_names = [m['master'] for m in masters_collection.find()]
    referenced_master = next(
        (name for name in master_names if re.search(rf"\b{name}\b", user_input, re.IGNORECASE)), None
    )

    if referenced_master:
        doc = masters_collection.find_one({"master": referenced_master})
        reply = elaborate_answer(doc, user_input)

    else:
        # General search using embeddings
        user_emb = generate_embedding(user_input)
        top_masters = search_master_programs(user_emb, top_k=5)

        # Fallback if no embeddings match
        if not top_masters:
            top_masters = keyword_fallback_search(user_input)

        if not top_masters:
            reply = "❌ Sorry, no matching master's programs found."
        else:
            reply_lines = []
            for i, doc in enumerate(top_masters, 1):
                location = doc.get("Location", "Not available")
                maps_link = get_location_link(doc.get("university", ""))
                if maps_link:
                    location = f"[{location}]({maps_link})"
                elaborated_text = elaborate_answer(doc, user_input)
                reply_lines.append(
                    f"🔸 Match #{i}\n"
                    f"🎓 Master: {doc.get('master','Not available')}\n"
                    f"🏛 University: {doc.get('university','Not available')}\n"
                    f"📍 Location: {location}\n"
                    f"⏳ Duration: {doc.get('Duration','Not available')}\n"
                    f"💰 Tuition Fee: {doc.get('Tuition Fee','Not available')}\n\n"
                    f"{elaborated_text}\n"
                )
            reply = "\n".join(reply_lines)

    st.session_state.messages.append({"role": "assistant", "content": reply})

# -----------------------------
# Display chat history
# -----------------------------
for msg in st.session_state.messages:
    role = "user" if msg["role"] == "user" else "assistant"
    with st.chat_message(role):
        st.markdown(msg["content"])
