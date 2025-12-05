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
LLM_MODEL = "gemini-2.0-flash"   # fast & free

# ---------- MongoDB ----------
mongo_client = MongoClient(MONGO_URI)
db = mongo_client[MONGO_DB]
masters_collection = db.Masters
maps_collection = db.Maps_Location


# -------------------------------------------------------
#  LOTTIE INTRO
# -------------------------------------------------------
def play_lottie_intro(json_path: str, height: int = 300, duration: float = 3.0):
    if st.session_state.get("intro_played", False):
        return
    st.session_state["intro_played"] = True

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


# -------------------------------------------------------
#  EMBEDDINGS
# -------------------------------------------------------
def _generate_embedding(text: str) -> np.ndarray:
    """Generate embedding ONLY for user input."""
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


# -------------------------------------------------------
#  SEARCH (scans dataset ONE time)
# -------------------------------------------------------
def _search_master_programs(user_emb: np.ndarray, top_k: int = 5):
    """Return top_k Mongo docs most similar to user_emb."""
    results = []

    for doc in masters_collection.find():
        emb_list = doc.get("embedding", [])
        if not emb_list:
            continue

        emb = np.array(emb_list, dtype=float)
        score = _cosine_similarity(user_emb, emb)
        results.append((score, doc))

    results.sort(key=lambda x: x[0], reverse=True)
    return [r[1] for r in results[:top_k]]


# -------------------------------------------------------
#  TOOLS
# -------------------------------------------------------
def _get_location_link(university_name: str):
    doc = maps_collection.find_one(
        {"Institution": {"$regex": f"^{re.escape(university_name)}$", "$options": "i"}}
    )
    return doc.get("GoogleMaps") if doc else None


def _keyword_fallback_search(query: str):
    regex = re.compile(re.escape(query), re.IGNORECASE)
    return list(masters_collection.find({"master": {"$regex": regex}}))[:5]


# -------------------------------------------------------
#  MULTI-PROGRAM GEMINI RESPONSE (FAST: 1 CALL)
# -------------------------------------------------------
def _elaborate_multiple_answers(master_docs: list, user_query: str) -> str:
    """
    One Gemini call → explanation for all 5 masters.
    Much faster than 5 LLM calls.
    """

    programs_text = ""
    for i, doc in enumerate(master_docs, 1):
        programs_text += (
            f"\n### Program {i}\n"
            f"Master Program: {doc.get('master')}\n"
            f"University: {doc.get('university')}\n"
            f"Location: {doc.get('Location')}\n"
            f"Duration: {doc.get('Duration')}\n"
            f"Tuition Fee: {doc.get('Tuition Fee')}\n"
            f"About: {doc.get('about', '')}\n"
        )

    prompt = f"""
You are an educational advisor. The user asked:

**"{user_query}"**

You will receive 5 master's programs from a dataset that ONLY contains programs from PORTUGAL.

### STRICT RULES:
- Only describe THESE programs.
- Do NOT create new universities or programs.
- Do NOT mention programs outside Portugal.
- No comparisons with foreign institutions.
- Give ALL 5 results in a clean, structured format.

### Format required for EACH program:
- **Master Program**: 
- **University**:
- **Location**:
- **Tuition Fee**:
- **Why it could be a good fit**:
- **Ideal for students who**:
- **What makes it special**:

---

Here are the programs:

{programs_text}
"""

    try:
        response = ai_client.models.generate_content(
            model=LLM_MODEL,
            contents=[prompt],
            config=genai.types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=15000,
            ),
        )
        if response.candidates:
            return "".join(
                getattr(p, "text", "") for p in response.candidates[0].content.parts
            ).strip()
    except Exception as e:
        return f"(Error generating explanation: {e})"

    return "No elaborated text available."


# -------------------------------------------------------
#  MAIN QUERY ENTRYPOINT
# -------------------------------------------------------
def handle_user_query(user_input: str) -> str:

    # FIRST: direct reference?
    master_names = [m.get("master", "") for m in masters_collection.find()]
    referenced_master = next(
        (name for name in master_names if name and re.search(rf"\b{name}\b", user_input, re.IGNORECASE)),
        None,
    )

    if referenced_master:
        # Only 1 result requested → use old single-answer function
        doc = masters_collection.find_one({"master": referenced_master})
        return _elaborate_multiple_answers([doc], user_input)

    # OTHERWISE: semantic search
    try:
        user_emb = _generate_embedding(user_input)
    except Exception as e:
        return f"❌ Error generating embedding: {e}"

    top_masters = _search_master_programs(user_emb, top_k=5)

    if not top_masters:
        top_masters = _keyword_fallback_search(user_input)

    if not top_masters:
        return "❌ No matching master's programs found."

    # ONE GEMINI CALL FOR ALL 5 PROGRAMS → FAST
    return _elaborate_multiple_answers(top_masters, user_input)
