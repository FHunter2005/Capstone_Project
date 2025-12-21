# Project/calculator.py
import streamlit as st

def render_price_calculator():
    st.subheader("Total Cost Calculator (Master’s)")

    with st.form("calc"):
        c1, c2 = st.columns(2)
        tuition = c1.number_input("Tuition total (€)", 0, 100000, 12000, 500)
        fees = c1.number_input("Other one-off fees (€)", 0, 5000, 500, 50)

        living = c2.number_input("Living cost per month (€)", 0, 5000, 900, 50)
        months = c2.number_input("Total months of study", 1, 60, 24, 1)

        c3, c4, c5 = st.columns(3)
        scholarship = c3.slider("Scholarship on tuition (%)", 0, 100, 20)
        exchange = c4.number_input(
            "Exchange rate (your currency per €)", 0.0, 10.0, 1.0, 0.01
        )
        part_time = c5.number_input(
            "Part-time income offset (€ / month)", 0, 5000, 0, 50
        )

        submitted = st.form_submit_button("Calculate")

    if submitted:
        tuition_net = tuition * (1 - scholarship / 100) + fees
        living_total = max(0, living - part_time) * months
        total_eur = round(tuition_net + living_total, 2)
        total_local = round(total_eur * exchange, 2)

        c1, c2 = st.columns(2)
        c1.metric("Total cost (€)", f"{total_eur:,.2f}")
        c2.metric("Total cost (local)", f"{total_local:,.2f}")