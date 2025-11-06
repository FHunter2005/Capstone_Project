# ===========================
# Masters Finder – Chat + Filters + Calculator
# ===========================
import os
import re
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# ---------- Inline data helpers (no utils) ----------
DATA_DIR = Path(__file__).parent / "data"
DATA_PATH = DATA_DIR / "masters.csv"

SAMPLE_COUNTRIES = ["Portugal","Spain","France","Germany","Netherlands"]
SAMPLE_FIELDS = ["Data Science","Economics","Engineering","Management","Statistics"]
SAMPLE_MODALITY = ["On-campus","Online","Hybrid"]
SAMPLE_LANG = ["English","Portuguese","Spanish","French","German"]

def _make_sample(n=120) -> pd.DataFrame:
    rng = np.random.default_rng(42)
    df = pd.DataFrame({
        "program_id": np.arange(1, n+1),
        "program": [f"Master Program {i}" for i in range(1, n+1)],
        "university": [f"University {i%12 + 1}" for i in range(1, n+1)],
        "country": rng.choice(SAMPLE_COUNTRIES, n),
        "field": rng.choice(SAMPLE_FIELDS, n),
        "modality": rng.choice(SAMPLE_MODALITY, n),
        "language": rng.choice(SAMPLE_LANG, n),
        "duration_months": rng.integers(12, 30, n),
        "credits_ects": rng.integers(60, 150, n),
        "ranking": rng.integers(1, 500, n),
        "tuition_total": rng.integers(2500, 35000, n),
        "application_fee": rng.integers(0, 200, n),
        "scholarship_max_pct": rng.integers(0, 60, n),
        "living_cost_month": rng.integers(500, 1600, n),
    })
    return df

def ensure_dataset() -> str:
    DATA_DIR.mkdir(exist_ok=True)
    if not DATA_PATH.exists():
        _make_sample().to_csv(DATA_PATH, index=False)
    return str(DATA_PATH)

@st.cache_data(show_spinner=False)
def load_data() -> pd.DataFrame:
    ensure_dataset()
    df = pd.read_csv(DATA_PATH)
    df["program_id"] = df["program_id"].astype(str)
    return df

# ---------- Chat helpers ----------
def init_state():
    ss = st.session_state
    ss.setdefault("chat_msgs", [])
    ss.setdefault("flt_country", [])
    ss.setdefault("flt_field", [])
    ss.setdefault("flt_modality", [])
    ss.setdefault("flt_language", [])
    ss.setdefault("flt_rank", None)
    ss.setdefault("flt_price", None)
    ss.setdefault("flt_keyword", "")

def filters_summary():
    ss = st.session_state
    parts = []
    if ss.flt_country:  parts.append(f"Country={', '.join(ss.flt_country)}")
    if ss.flt_field:    parts.append(f"Field={', '.join(ss.flt_field)}")
    if ss.flt_modality: parts.append(f"Modality={', '.join(ss.flt_modality)}")
    if ss.flt_language: parts.append(f"Language={', '.join(ss.flt_language)}")
    if ss.flt_rank:     parts.append(f"Ranking={ss.flt_rank[0]}–{ss.flt_rank[1]}")
    if ss.flt_price:    parts.append(f"Tuition={ss.flt_price[0]}–{ss.flt_price[1]}")
    if ss.flt_keyword:  parts.append(f"Keyword='{ss.flt_keyword}'")
    return " | ".join(parts) if parts else "No filters set."

def parse_csv_list(text):
    return [t.strip().capitalize() for t in text.split(",") if t.strip()]

def parse_command(text, df):
    ss = st.session_state
    t = text.strip().lower()
    if t in {"clear", "reset"}:
        ss.flt_country = ss.flt_field = ss.flt_modality = ss.flt_language = []
        ss.flt_rank = ss.flt_price = None
        ss.flt_keyword = ""
        return "Filters cleared."

    m = re.match(r"country\s+(.+)", t)
    if m:
        ss.flt_country = parse_csv_list(m.group(1))
        return f"Country set to: {', '.join(ss.flt_country)}"

    m = re.match(r"field\s+(.+)", t)
    if m:
        ss.flt_field = parse_csv_list(m.group(1))
        return f"Field set to: {', '.join(ss.flt_field)}"

    m = re.match(r"modality\s+(.+)", t)
    if m:
        ss.flt_modality = parse_csv_list(m.group(1))
        return f"Modality set to: {', '.join(ss.flt_modality)}"

    m = re.match(r"language\s+(.+)", t)
    if m:
        ss.flt_language = parse_csv_list(m.group(1))
        return f"Language set to: {', '.join(ss.flt_language)}"

    m = re.match(r"(rank|ranking)\s+(\d+)\s*[-to]\s*(\d+)", t)
    if m:
        a,b = int(m.group(2)), int(m.group(3))
        if a > b: a,b = b,a
        ss.flt_rank = (a,b)
        return f"Ranking set to {a}–{b}"

    m = re.match(r"(price|tuition)\s+under\s+(\d+)", t)
    if m:
        b = int(m.group(2))
        ss.flt_price = (int(df["tuition_total"].min()), b)
        return f"Tuition under {b}€"
    m = re.match(r"(price|tuition)\s+(\d+)\s*[-to]\s*(\d+)", t)
    if m:
        a,b = int(m.group(2)), int(m.group(3))
        if a>b: a,b=b,a
        ss.flt_price = (a,b)
        return f"Tuition {a}–{b}€"

    m = re.match(r"(keyword|search)\s+(.+)", t)
    if m:
        ss.flt_keyword = m.group(2).strip()
        return f"Keyword set to '{ss.flt_keyword}'"

    if t in {"show","filters"}:
        return f"Current filters → {filters_summary()}"

    return "Unknown command. Try: `country portugal`, `field data science`, `price under 10000`, `rank 1-200`, `clear`."

# ---------- Streamlit Layout ----------
st.set_page_config(page_title="Masters Matchr", page_icon="🎓", layout="wide")
init_state()

st.markdown("""
<div style='text-align: center; background-color:#262730; padding:25px; border-radius:10px;'>
    <h1 style='color:#F4B400;'>🎓 Masters Finder</h1>
    <p style='font-size:18px; color:lightgray;'>
        Find programs that match your preferences and estimate total cost.
    </p>
</div>
""", unsafe_allow_html=True)
ensure_dataset()

tab_find, tab_price = st.tabs(["🔎 Find Programs", "💶 Price Calculator"])

# ---------- TAB 1: Find Programs ----------
with tab_find:
    df = load_data()

    # Chat
    st.subheader("Chat Your Filters")
    for role, msg in st.session_state.chat_msgs:
        with st.chat_message(role):
            st.markdown(msg)

    with st.chat_message("assistant"):
        st.markdown(
            "**Tell me your filters** (e.g., `country portugal`, `field data science`, "
            "`price under 10000`, `rank 1-200`, `keyword machine learning`).\n\n"
            f"**Current:** {filters_summary()}"
        )

    msg = st.chat_input("Type a filter command")
    if msg:
        st.session_state.chat_msgs.append(("user", msg))
        reply = parse_command(msg, df)
        st.session_state.chat_msgs.append(("assistant", reply))
        st.rerun()

    st.divider()
    st.subheader("Filter & Explore")

    # Build mask from filters
    mask = pd.Series(True, index=df.index)
    ss = st.session_state
    if ss.flt_country:
        mask &= df["country"].isin(ss.flt_country)
    if ss.flt_field:
        mask &= df["field"].isin(ss.flt_field)
    if ss.flt_modality:
        mask &= df["modality"].isin(ss.flt_modality)
    if ss.flt_language:
        mask &= df["language"].isin(ss.flt_language)
    if ss.flt_rank:
        a,b = ss.flt_rank
        mask &= df["ranking"].between(a,b)
    if ss.flt_price:
        a,b = ss.flt_price
        mask &= df["tuition_total"].between(a,b)
    if ss.flt_keyword:
        s = ss.flt_keyword.lower()
        mask &= df["program"].str.lower().str.contains(s) | df["university"].str.lower().str.contains(s)

    filtered = df[mask].copy()

    # Metrics
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Programs", f"{len(filtered):,}")
    c2.metric("Avg Tuition (€)", f"{int(filtered['tuition_total'].mean()):,}" if len(filtered) else "—")
    c3.metric("Median Ranking", f"{int(filtered['ranking'].median())}" if len(filtered) else "—")
    c4.metric("Countries", f"{filtered['country'].nunique()}" if len(filtered) else "—")

    st.divider()
    st.subheader("Results")

    if filtered.empty:
        st.info("No programs match your filters.")
    else:
        view = filtered.sort_values(["tuition_total","ranking"]).reset_index(drop=True)
        st.dataframe(
            view[["program","university","country","field","modality","language","ranking","tuition_total"]],
            use_container_width=True
        )

        st.subheader("Price vs Ranking")
        fig = px.scatter(
            filtered, x="ranking", y="tuition_total",
            hover_data=["program","university","country"],
            labels={"ranking":"Ranking (lower is better)", "tuition_total":"Tuition (€)"}
        )
        st.plotly_chart(fig, use_container_width=True)

# ---------- TAB 2: Price Calculator ----------
with tab_price:
    st.subheader("Total Cost Calculator")
    with st.form("calc"):
        c1,c2 = st.columns(2)
        tuition = c1.number_input("Tuition (€)", 0, 100000, 10000, 250)
        fees = c1.number_input("Other fees (€)", 0, 5000, 500, 50)
        living = c2.number_input("Living cost per month (€)", 0, 5000, 800, 50)
        months = c2.number_input("Months", 1, 60, 24, 1)

        c3,c4,c5 = st.columns(3)
        scholarship = c3.slider("Scholarship (%)", 0, 100, 20)
        exchange = c4.number_input("Exchange rate (your currency per €)", 0.0, 10.0, 1.0, 0.01)
        part_time = c5.number_input("Part-time offset (€ / month)", 0, 5000, 0, 50)
        submitted = st.form_submit_button("Calculate")

    if submitted:
        tuition_net = tuition * (1 - scholarship/100) + fees
        total_eur = tuition_net + max(0, living - part_time) * months
        total_local = total_eur * exchange
        c1,c2 = st.columns(2)
        c1.metric("Total (€)", f"{int(total_eur):,}")
        c2.metric("Total (local)", f"{int(total_local):,}")

st.caption("💬 Example chat: `country portugal, spain | field data science | price under 12000 | rank 1-200`")
