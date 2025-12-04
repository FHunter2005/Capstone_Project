# master_backend.py
import os
import re
import numpy as np
from dotenv import load_dotenv
from pymongo import MongoClient
from google import genai
from streamlit_lottie import st_lottie
import requests
import streamlit as st
import time
import json

# ---------- Load env ----------
load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
MONGO_URI = os.getenv("MONGO_URI")
MONGO_DB = os.getenv("MONGO_DB")

if not GOOGLE_KEY:
    raise RuntimeError("Missing GOOGLE_API_KEY in .env")
if not MONGO_URI or not MONGO_DB:
    raise RuntimeError("Missing MONGO_URI or MONGO_DB in .env")

# ---------- Gemini client & models ----------
ai_client = genai.Client(api_key=GOOGLE_KEY)
EMBED_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.0-flash"   # good free-tier choice

# ---------- MongoDB ----------
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
masters_collection = db.Masters
maps_collection = db.Maps_Location


def play_lottie_intro(json_path: str, height: int = 300, duration: float = 3.0):
    # If animation already played in this session → do nothing
    if st.session_state.get("intro_played", False):
        return

    # Mark it as played
    st.session_state["intro_played"] = True

    # Load JSON
    try:
        with open(json_path, "r") as f:
            animation = json.load(f)
    except Exception as e:
        st.error(f"Could not load Lottie animation: {e}")
        return

    placeholder = st.empty()
    with placeholder:
        st_lottie(animation, height=height, loop=False)

    time.sleep(duration)
    placeholder.empty()


# ---------- Embedding helpers ----------
def _generate_embedding(text: str) -> np.ndarray:
    resp = ai_client.models.embed_content(
        model=EMBED_MODEL,
        contents=[text],
    )
    return np.array(resp.embeddings[0].values, dtype=float)


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def ensure_embeddings():
    """Ensure each master document in Mongo has an 'embedding' field."""
    for doc in masters_collection.find():
        if "embedding" not in doc or not doc["embedding"]:
            text_to_embed = doc.get("about", doc.get("master", ""))
            if not text_to_embed:
                continue
            emb = _generate_embedding(text_to_embed)
            masters_collection.update_one(
                {"_id": doc["_id"]},
                {"$set": {"embedding": emb.tolist()}},
            )


def _search_master_programs(user_emb: np.ndarray, top_k: int = 5):
    """Return top_k Mongo docs most similar to user_emb."""
    results = []
    for doc in masters_collection.find():
        emb_list = doc.get("embedding", [])
        emb = np.array(emb_list, dtype=float)
        if emb.size == 0:
            continue
        score = _cosine_similarity(user_emb, emb)
        results.append((score, doc))
    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:top_k]]


def _get_location_link(university_name: str):
    """Get Google Maps link from Maps_Location by institution name."""
    doc = maps_collection.find_one(
        {"Institution": {"$regex": f"^{re.escape(university_name)}$", "$options": "i"}}
    )
    if doc and "GoogleMaps" in doc:
        return doc["GoogleMaps"]
    return None


def _keyword_fallback_search(query: str):
    """Simple regex search over master name if embeddings fail."""
    regex = re.compile(re.escape(query), re.IGNORECASE)
    return list(masters_collection.find({"master": {"$regex": regex}}))[:5]


def _elaborate_answer(master_doc: dict, user_query: str) -> str:
    """Use Gemini to generate a detailed explanation about a master program."""
    about_text = master_doc.get("about", "No description available.")
    prompt = (
        f"You are an educational advisor. The user asked: '{user_query}'.\n\n"
        
        f"You will receive information about ONE master's program from a dataset that "
        f"ONLY contains master's programs from PORTUGAL.\n"
        
        f"⚠️ RULES YOU MUST FOLLOW STRICTLY:\n"
        f"- Only describe the program shown below.\n"
        f"- Do NOT create, imagine, or reference any university or master's program "
        f"outside Portugal.\n"
        f"- Do NOT recommend additional programs.\n"
        f"- Do NOT mention international rankings, comparisons, or foreign alternatives.\n"
        f"- Your entire answer must be ONLY about the program provided below.\n\n"
        
        f"Format your answer EXACTLY like this:\n"
        f"- **Master Program**: (name)\n"
        f"- **University**: (name)\n"
        f"- **Location**: (city or region in Portugal)\n"
        f"- **Tuition Fee**: (value)\n"
        f"- **Why it could be a good fit**: 1-2 short sentences\n"
        f"- **Ideal for students who**: 1 short sentence\n"
        f"- **What makes it special**: 1 short sentence\n\n"
        
        f"--- Program Information ---\n"
        f"Master Program: {master_doc.get('master')}\n"
        f"University: {master_doc.get('university')}\n"
        f"Location: {master_doc.get('Location', 'Not available')}\n"
        f"Duration: {master_doc.get('Duration', 'Not available')}\n"
        f"Tuition Fee: {master_doc.get('Tuition Fee', 'Not available')}\n"
        f"About: {about_text}\n"
    )




    try:
        response = ai_client.models.generate_content(
            model=LLM_MODEL,
            contents=[prompt],
            config=genai.types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=10000,
            ),
        )
        if response.candidates:
            parts = response.candidates[0].content.parts
            text = "".join(getattr(p, "text", "") for p in parts)
            return text.strip() or "No elaborated text available."
    except Exception as e:
        return f"(Could not generate detailed explanation: {e})"

    return "No elaborated text available."


def handle_user_query(user_input: str) -> str:
    """
    Public API for the app:
    Given a user query, returns a markdown string with recommended programs + explanations.
    """
    # 1) Direct reference by master name?
    master_names = [m.get("master", "") for m in masters_collection.find()]
    referenced_master = next(
        (name for name in master_names if name and re.search(rf"\b{name}\b", user_input, re.IGNORECASE)),
        None,
    )

    if referenced_master:
        doc = masters_collection.find_one({"master": referenced_master})
        if not doc:
            return "I couldn't find detailed information about that specific master."
        return _elaborate_answer(doc, user_input)

    # 2) Otherwise: semantic search
    try:
        user_emb = _generate_embedding(user_input)
    except Exception as e:
        return f"❌ Error while generating embedding: {e}"

    top_masters = _search_master_programs(user_emb, top_k=5)

    # 3) Fallback if nothing found
    if not top_masters:
        top_masters = _keyword_fallback_search(user_input)

    if not top_masters:
        return "❌ Sorry, no matching master's programs found."

    # 4) Build markdown answer with multiple matches
    reply_lines = []
    for i, doc in enumerate(top_masters, 1):
        location = doc.get("Location", "Not available")
        maps_link = _get_location_link(doc.get("university", ""))
        if maps_link:
            location = f"[{location}]({maps_link})"

        elaborated_text = _elaborate_answer(doc, user_input)

        reply_lines.append(
            f"🔸 **Match #{i}**\n"
            f"🎓 **Master:** {doc.get('master', 'Not available')}\n"
            f"🏛 **University:** {doc.get('university', 'Not available')}\n"
            f"📍 **Location:** {location}\n"
            f"⏳ **Duration:** {doc.get('Duration', 'Not available')}\n"
            f"💰 **Tuition Fee:** {doc.get('Tuition Fee', 'Not available')}\n\n"
            f"{elaborated_text}\n"
        )

    return "\n".join(reply_lines)
