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
# 3. Website links to load (no CSV needed)
# ======================================================
MASTER_LINKS = ["https://www.mastersportal.com/search/master/portugal?page=3"]

# Show links
st.subheader("🔗 Loaded Master Page Links")
for link in MASTER_LINKS:
    st.write(link)


# ======================================================
# 4. Extract website knowledge ONCE
# ======================================================
if "website_knowledge" not in st.session_state:
    st.session_state.website_knowledge = ""

    with st.spinner("Extracting master's programs from websites..."):
        for link in MASTER_LINKS:

            query = (
                f"Extract all Master's programs listed on this page: {link}. ",
                "Include program names, university, city."
            )

            result = tv.search(
                query=query,
                include_raw_content=False,
                max_results=10
            )

            raw = "\n\n".join(
                r.get("raw_content", "") or "" for r in result.get("results", [])
            )

            st.session_state.website_knowledge += f"\n\n=== WEBSITE: {link} ===\n{raw}"


# ======================================================
# 5. Summarize WEBSITE knowledge ONLY
# ======================================================
if "combined_summary" not in st.session_state:

    with st.spinner("Summarizing all master's program information..."):
        content_to_summarize = (
            "Here is website content extracted:\n\n"
            + st.session_state.website_knowledge
        )

        summary = client.models.generate_content(
            model="gemini-2.0-flash-lite",
            contents=(
                "Summarize ALL master's program information below into a structured list. "
                "Include program name, fields, duration, university, and key notes. "
                "Ignore ads, menus, and irrelevant content.\n\n"
                + content_to_summarize
            )
        )

        st.session_state.combined_summary = summary.text


# ======================================================
# 6. Build system instruction for AI
# ======================================================
system_instruction = f"""
You are a professional Master's degree advisor.

You have access to the following structured knowledge:

========================
{st.session_state.combined_summary}
========================

Rules:
- ALWAYS base recommendations only on the knowledge above.
- Provide 5 recommendations.
- For each master's program, ALWAYS include in this order:
    1. Program name
    2. Institution
    3. City (if available)
- DO NOT mention Google Maps links.
- Give clear, helpful, personalized suggestions.
"""


# ======================================================
# 7. Chat initialization
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

# Replay conversation
for m in st.session_state.messages:
    chat.send_message(m["content"])

# Display chat history
for m in st.session_state.messages:
    avatar = "👤" if m["role"] == "user" else "🤖"
    with st.chat_message(m["role"], avatar=avatar):
        st.write(m["content"])


# ======================================================
# 8. User Input
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
# 9. Welcome message
# ======================================================
if len(st.session_state.messages) == 0:
    st.info("""
    👋 Welcome to your Master's Program Advisor!

    Try asking:
    • “I like technology and business, what master fits me?”
    • “Which programs match data science?”
    • “I want a master's that helps me get a high-paying job.”
    """)
