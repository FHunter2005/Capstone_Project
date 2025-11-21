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

client = genai.Client(api_key=GOOGLE_KEY)
tv = TavilyClient(api_key=TAVILY_KEY) if TAVILY_KEY else None

MODEL = "gemini-2.5-flash-lite"

# ======================================================
# 2. Streamlit Page Setup
# ======================================================
st.set_page_config(page_title="Master's Advisor AI", page_icon="🎓")
st.title("🎓 Master's Program Advisor AI")

# ======================================================
# 3. CSV input
# ======================================================
st.subheader("📄 Load CSV Files")

master_csv_file = st.file_uploader(
    "Upload Master's Programs CSV",
    type="csv",
    key="master_csv"
)
location_csv_file = st.file_uploader(
    "Upload Institutions Locations CSV",
    type="csv",
    key="location_csv"
)

# ======================================================
# 4. Website link for Tavily extraction
# ======================================================
st.subheader("🔗 Website via Tavily")
master_links = st.text_area(
    "Enter master program page URL(s), one per line:",
    "https://eduportugal.eu/cursos-estudo/mestrado/",
    height=80
).splitlines()

# ======================================================
# 5. Build combined knowledge
# ======================================================
website_knowledge = ""

# 5A. CSV Masters Programs
if master_csv_file:
    df_masters = pd.read_csv(master_csv_file)
    masters_knowledge = ""
    for idx, row in df_masters.iterrows():
        masters_knowledge += (
            f"Program: {row['Master Name']}\n"
            f"University: {row['University']}\n"
            f"Location: {row.get('Location','')}\n"
            f"Duration: {row.get('Duration','')}\n"
            f"Tuition: {row.get('Tuition Fee','')}\n\n"
        )
    website_knowledge += "Masters Programs from CSV:\n" + masters_knowledge + "\n"
    st.write("✅ Loaded Master's programs from CSV")

# 5B. CSV Institutions Locations
if location_csv_file:
    df_locations = pd.read_csv(
        location_csv_file,
        sep=';',
        usecols=[0,1],
        engine='python',
        on_bad_lines='skip'
    )
    df_locations.columns = ["Institution","GoogleMaps"]
    location_knowledge = ""
    for idx, row in df_locations.iterrows():
        location_knowledge += f"Institution: {row['Institution']} | GoogleMaps: {row['GoogleMaps']}\n"
    website_knowledge += "Institutions and Locations from CSV:\n" + location_knowledge + "\n"
    st.write("✅ Loaded Institutions/Locations from CSV")

# 5C. Tavily Website Extraction
if tv and master_links:
    with st.spinner("Extracting master's programs from website via Tavily..."):
        for link in master_links:
            query = f"Extract all Master's programs listed on this page: {link}. Include program names, university, city."
            result = tv.search(query=query, include_raw_content=False, max_results=20)
            raw = "\n\n".join(r.get("raw_content","") or "" for r in result.get("results", []))
            website_knowledge += f"\n\n=== WEBSITE: {link} ===\n{raw}"
    st.write("✅ Extracted knowledge from Tavily website(s)")

# Save combined knowledge in session state
if website_knowledge:
    st.session_state.website_knowledge = website_knowledge
else:
    st.warning("⚠️ No data loaded. Upload CSVs or provide website links to proceed.")

# ======================================================
# 6. Build system instruction
# ======================================================
if "website_knowledge" in st.session_state:
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
    # 7. Initialize chat
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
    # 8. User input
    # ======================================================
    if prompt := st.chat_input("Tell me your goals, interests, or preferred study area..."):
        st.session_state.messages.append({"role": "user", "content": prompt})

        with st.chat_message("user", avatar="👤"):
            st.write(prompt)

        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("Thinking..."):
                response = chat.send_message(prompt)
                reply_text = response.text
                st.session_state.messages.append({"role": "assistant", "content": reply_text})
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
