import streamlit as st
import pandas as pd
from google import genai
from dotenv import load_dotenv
from tavily import TavilyClient
import os

# ======================================================
# 1. Load environment variables
# ======================================================
load_dotenv()

GOOGLE_KEY = os.getenv("GOOGLE_API_KEY")
TAVILY_KEY = os.getenv("TAVILY_API_KEY")

if not GOOGLE_KEY:
    st.error("❌ Missing GOOGLE_API_KEY in .env")
    st.stop()

if not TAVILY_KEY:
    st.error("❌ Missing TAVILY_API_KEY in .env")
    st.stop()

client = genai.Client(api_key=GOOGLE_KEY)
tv = TavilyClient(api_key=TAVILY_KEY)
MODEL = "gemini-2.5-flash-lite"


# ======================================================
# 2. Streamlit Page Setup
# ======================================================
st.set_page_config(page_title="Master's Advisor AI", page_icon="🎓")
st.title("🎓 Master's Program Advisor AI")


# ======================================================
# 3. Load CSV file
# ======================================================
csv_path = "C:/Users/filip/OneDrive - NOVAIMS/Documents/Github/Capstone_Project/notebooks/institutions_locations.csv"

if not os.path.exists(csv_path):
    st.error(f"❌ CSV file not found: {csv_path}")
    st.stop()

# Load only first 2 columns (Institution and GoogleMaps)
df = pd.read_csv(
    csv_path,
    sep=";",
    engine="python",
    usecols=[0, 1],
    names=["Institution", "GoogleMaps"],
    header=0,
    on_bad_lines="warn"
)
st.write("📄 Loaded CSV with", len(df), "rows.")


# ======================================================
# 4. Website links to load
# ======================================================
MASTER_LINKS = [
    "https://eduportugal.eu/cursos-estudo/mestrado/"
]


# ======================================================
# 5. Extract website knowledge ONCE
# ======================================================
if "website_knowledge" not in st.session_state:
    st.session_state.website_knowledge = ""

    with st.spinner("Extracting master's programs from websites..."):
        for link in MASTER_LINKS:

            query = (
                f"Extract all Master's programs listed on this page: {link}. "
                "Include program names, areas, descriptions, and university info."
            )

            result = tv.search(
                query=query,
                include_raw_content=True,
                max_results=5
            )

            raw = "\n\n".join(
                r.get("raw_content", "") or "" for r in result.get("results", [])
            )

            st.session_state.website_knowledge += f"\n\n=== WEBSITE: {link} ===\n{raw}"


# ======================================================
# 6. Format CSV nicely for AI (preserve Google Maps links)
# ======================================================
csv_text = ""
for _, row in df.iterrows():
    institution = row["Institution"]
    maps_link = row["GoogleMaps"] if row["GoogleMaps"] else "No link"
    csv_text += f"- {institution} | Google Maps: {maps_link}\n"


# ======================================================
# 7. Summarize CSV + website knowledge ONCE
# ======================================================
if "combined_summary" not in st.session_state:

    with st.spinner("Summarizing all master's program information..."):
        content_to_summarize = (
            "Here is the CSV dataset containing master's programs and their locations:\n\n"
            + csv_text
            + "\n\nHere is website content extracted:\n\n"
            + st.session_state.website_knowledge
        )

        summary = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=(
                "Summarize ALL master's program information below into a structured list. "
                "Include ONLY program name, fields, duration, university, and key notes. "
                "Keep Google Maps links for each institution. "
                "Ignore ads, menus, and irrelevant content.\n\n"
                + content_to_summarize
            )
        )

        st.session_state.combined_summary = summary.text


# ======================================================
# 8. Build system instruction for AI — Knowledge base
# ======================================================
system_instruction = f"""
You are a professional Master's degree advisor.

You have access to the following summarized, structured knowledge:

========================
{st.session_state.combined_summary}
========================

Rules:
- ALWAYS base your recommendations ONLY on the knowledge above.
-Give like 5 recomendations
- When recommending a master's program, ALWAYS include in this order:
    1. Program name
    2. Institution
    3. City
    4. Google Maps link
- Do NOT reveal the raw CSV or raw website text unless the user asks explicitly.
- Provide helpful, personalized advice.
- Your responses must start with the program name and institution; location and Google Maps link come immediately after.
"""


# ======================================================
# 9. Chat initialization
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

# Replay previous messages
for m in st.session_state.messages:
    chat.send_message(m["content"])

# Display chat history
for m in st.session_state.messages:
    avatar = "👤" if m["role"] == "user" else "🤖"
    with st.chat_message(m["role"], avatar=avatar):
        st.write(m["content"])


# ======================================================
# 10. User Input
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
# 11. Welcome message
# ======================================================
if len(st.session_state.messages) == 0:
    st.info("""
    👋 Welcome to your Master's Program Advisor!

    Try asking:
    • “I like technology and business, what master fits me?”
    • “Which programs match data science?”
    • “I want a master's that helps me get a high-paying job.”
    """)
