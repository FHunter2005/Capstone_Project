import streamlit as st
import pandas as pd
from google import genai
from dotenv import load_dotenv
import os

# ======================================================
# 1. Load environment variables
# ======================================================
load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_KEY:
    st.error("❌ Missing GOOGLE_API_KEY in .env")
    st.stop()

# Initialize Google GenAI client
client = genai.Client(api_key=GOOGLE_KEY)
MODEL = "gemini-2.5-flash-lite"

# ======================================================
# 2. Streamlit Page Setup
# ======================================================
st.set_page_config(page_title="Master's Advisor AI", page_icon="🎓")
st.title("🎓 Master's Program Advisor AI")

# ======================================================
# 3. Load CSVs
# ======================================================
MASTER_CSV_FILE = r"C:\Users\filip\OneDrive - NOVAIMS\Documents\Github\Capstone_Project\notebooks\masters_portugal_all_pages.csv"
LOCATION_CSV_FILE = r"C:\Users\filip\OneDrive - NOVAIMS\Documents\Github\Capstone_Project\notebooks\institutions_locations.csv"

try:
    df_masters = pd.read_csv(MASTER_CSV_FILE)
except FileNotFoundError:
    st.error(f"❌ Master CSV not found: {MASTER_CSV_FILE}")
    st.stop()

try:
    df_locations = pd.read_csv(
        LOCATION_CSV_FILE,
        sep=';',
        usecols=[0, 1],
        engine='python',
        on_bad_lines='skip'
    )
    df_locations.columns = ["Institution", "GoogleMaps"]
except FileNotFoundError:
    st.error(f"❌ Location CSV not found: {LOCATION_CSV_FILE}")
    st.stop()

# ======================================================
# 4. Build structured knowledge for AI
# ======================================================
if "website_knowledge" not in st.session_state:
    # Masters programs
    masters_knowledge = ""
    for idx, row in df_masters.iterrows():
        masters_knowledge += (
            f"Program: {row['Master Name']}\n"
            f"University: {row['University']}\n"
            f"Location: {row['Location']}\n"
            f"Duration: {row['Duration']}\n"
            f"Tuition: {row['Tuition Fee']}\n\n"
        )

    # Universities & locations
    location_knowledge = ""
    for idx, row in df_locations.iterrows():
        location_knowledge += f"Institution: {row['Institution']} | GoogleMaps: {row['GoogleMaps']}\n"

    # Combine knowledge
    st.session_state.website_knowledge = (
        "Masters Programs:\n" + masters_knowledge + "\n" +
        "Universities and Locations:\n" + location_knowledge
    )

# ======================================================
# 5. Build system instruction for AI
# ======================================================
system_instruction = f"""
You are a professional Master's degree advisor.

You have access to the following structured knowledge:

========================
{st.session_state.website_knowledge}
========================

Rules:
- ALWAYS base recommendations only on the knowledge above.
- Provide 5 recommendations.
- For each master's program, ALWAYS include in this order:
    1. Program name
    2. Institution
    3. Google Maps link (if available)
- Give clear, helpful, personalized suggestions.
"""

# ======================================================
# 6. Initialize chat
# ======================================================
if "messages" not in st.session_state:
    st.session_state.messages = []

chat = client.chats.create(
    model=MODEL,
    config={
        "system_instruction": system_instruction,
        "temperature": 0.7
    }
)

# Replay conversation history
for m in st.session_state.messages:
    avatar = "👤" if m["role"] == "user" else "🤖"
    with st.chat_message(m["role"], avatar=avatar):
        st.write(m["content"])

# ======================================================
# 7. User input
# ======================================================
if prompt := st.chat_input("Tell me your goals, interests, or preferred study area..."):

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user", avatar="👤"):
        st.write(prompt)

    with st.chat_message("assistant", avatar="🤖"):
        with st.spinner("Thinking..."):
            response = chat.send_message(prompt)
            reply_text = response.text

            st.session_state.messages.append(
                {"role": "assistant", "content": reply_text}
            )

            st.write(reply_text)

# ======================================================
# 8. Welcome message
# ======================================================
if len(st.session_state.messages) == 0:
    st.info("""
    👋 Welcome to your Master's Program Advisor!

    Try asking:
    • “I like technology and business, what master fits me?”
    • “Which programs match data science?”
    • “I want a master's that helps me get a high-paying job.”
    """)
