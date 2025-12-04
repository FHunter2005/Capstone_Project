# calculator.py
import pandas as pd
from pathlib import Path
import streamlit as st

# ---------- Paths ----------
BASE_DIR = Path(__file__).parent           # e.g. Capstone_Project/notebooks
CURRENCY_PATH = BASE_DIR / "currencies_clean.csv"


# ---------- Load currencies ----------
@st.cache_data
def load_currencies():
    df = pd.read_csv(CURRENCY_PATH)
    df = df.dropna(subset=["name"])
    df["symbol"] = df["symbol"].fillna("")
    return df


CURRENCIES_DF = load_currencies()


# ---------- Price Calculator ----------
def render_price_calculator():
    st.subheader("Total Cost Calculator (Master’s)")

    with st.form("calc"):
        # --- main cost inputs ---
        c1, c2 = st.columns(2)

        tuition = c1.number_input(
            "Tuition total (€)",
            min_value=0,
            value=12000,
            step=500,
        )

        fees = c1.number_input(
            "Other one-off fees (€)",
            min_value=0,
            value=500,
            step=50,
        )

        living = c2.number_input(
            "Living cost per month (€)",
            min_value=0,
            value=900,
            step=50,
        )

        months = c2.number_input(
            "Total months of study",
            min_value=1,
            value=24,
            step=1,
        )

        # --- scholarship + currency + part-time ---
        c3, c4, c5 = st.columns(3)

        scholarship = c3.slider(
            "Scholarship on tuition (%)",
            min_value=0,
            max_value=100,
            value=20,
        )

        # currency select with placeholder (no default)
        currency_index = c4.selectbox(
            "Your currency",
            options=CURRENCIES_DF.index,
            format_func=lambda i: f"{CURRENCIES_DF.loc[i,'symbol']} {CURRENCIES_DF.loc[i,'name']}",
            index=None,  # <- nothing selected at start
            placeholder="Select your currency",
        )

        exchange = c4.number_input(
            "Exchange rate (your currency per €)",
            min_value=0.0,
            value=1.0,
            step=0.01,
        )

        part_time = c5.number_input(
            "Part-time income offset (€ / month)",
            min_value=0,
            value=0,
            step=50,
        )

        submitted = st.form_submit_button("Calculate")

    if submitted:
        # user pressed Calculate
        if currency_index is None:
            st.error("Please select your currency before calculating.")
            return

        # --- calculations ---
        tuition_net = tuition * (1 - scholarship / 100) + fees
        living_total = max(0, living - part_time) * months
        total_eur = round(tuition_net + living_total, 2)
        total_local = round(total_eur * exchange, 2)

        # get symbol/name of chosen currency
        row = CURRENCIES_DF.loc[currency_index]
        curr_name = row["name"]
        curr_symbol = row["symbol"] or ""

        c1, c2 = st.columns(2)
        c1.metric("Total cost (€)", f"{total_eur:,.2f}")
        c2.metric(
            f"Total cost ({curr_name})",
            f"{curr_symbol} {total_local:,.2f}",
        )
