# Project/calculator.py
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import streamlit as st

"""
Financial Calculator Module.

This module provides a standalone UI component for the "Financial Path Planner".
It allows students to estimate the Total Cost of Attendance (Tuition + Living)
and convert it into their home currency.

It includes robust data loading utilities to handle the varying file structures
often found in different deployment environments (local vs cloud).
"""

def _find_currencies_file() -> Optional[Path]:
    """
    Heuristic File Search Strategy.

    Locates the 'currencies.csv' data file by scanning common directory structures.
    
    Why this is needed:
    - In local development, the file might be in 'Project/extras/data'.
    - In Docker/Cloud deployment, the working directory might shift, breaking relative paths.
    - This function recursively checks parents and known subfolders to find the file dynamically,
      preventing 'FileNotFoundError' crashes in production.

    Returns:
        Path | None: The absolute path to the file if found, else None.
    """
    filenames = ["currencies_clean.csv", "Currencies.csv", "currencies.csv"]

    # distinct anchor points to search from
    here = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()

    # Search up to 6 levels up from both the script location and current working dir
    roots = [here] + list(here.parents)[:6] + [cwd] + list(cwd.parents)[:6]

    candidate_subfolders = [
        (),  # root itself
        ("csv",),
        ("data",),
        ("extras", "data"),
        ("Project", "csv"),
        ("Project", "extras", "data"),
    ]

    checked = set()
    for r in roots:
        for sub in candidate_subfolders:
            for fname in filenames:
                p = r.joinpath(*sub, fname)
                # Optimization: Skip paths we've already checked
                if p in checked:
                    continue
                checked.add(p)
                
                if p.exists():
                    return p
    return None


def _load_currencies(path: Path) -> Tuple[pd.DataFrame, list, dict]:
    """
    Robust CSV Data Loader.

    Reads and normalizes the currencies dataset. It includes logic to handle
    malformed CSVs often encountered in legacy datasets (e.g., wrong delimiters,
    combined columns, or BOM characters).

    Args:
        path (Path): Path to the CSV file.

    Returns:
        Tuple containing:
            - DataFrame: Cleaned data.
            - list: List of currency names for the UI dropdown.
            - dict: Lookup map {currency_name: symbol}.
    """
    # Engine='python' allows more flexible separator detection
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", sep=None, engine="python").fillna("")
    
    # Normalize headers to handle case sensitivity issues
    df.columns = [str(c).strip().lower() for c in df.columns]

    # --- Data Cleaning & Normalization ---
    
    # Case 1: Standard format (columns: name, symbol)
    if "name" in df.columns and "symbol" in df.columns:
        pass

    # Case 2: Comma-merged columns (common in some exports) -> "name,symbol"
    elif "name,symbol" in df.columns:
        split = df["name,symbol"].astype(str).str.split(",", n=1, expand=True)
        df["name"] = split[0].astype(str).str.strip()
        df["symbol"] = split[1].fillna("").astype(str).str.strip()

    # Case 3: Semicolon-merged columns -> "name;symbol"
    elif "name;symbol" in df.columns:
        split = df["name;symbol"].astype(str).str.split(";", n=1, expand=True)
        df["name"] = split[0].astype(str).str.strip()
        df["symbol"] = split[1].fillna("").astype(str).str.strip()

    # Case 4: Missing headers (fallback to positional assumption)
    elif df.shape[1] >= 2:
        df = df.rename(columns={df.columns[0]: "name", df.columns[1]: "symbol"})

    else:
        raise ValueError(f"CSV must have currencies info, but columns are: {list(df.columns)}")

    # Final cleanup
    df["name"] = df["name"].astype(str).str.strip()
    df["symbol"] = df["symbol"].astype(str).str.strip()
    
    # Remove empty rows and duplicates
    df = df[df["name"] != ""].drop_duplicates(subset=["name"], keep="first")

    currency_list = df["name"].tolist()
    symbol_map = dict(zip(df["name"], df["symbol"]))

    if not currency_list:
        raise ValueError("No currencies loaded (name column is empty after cleaning).")

    return df, currency_list, symbol_map


def render_price_calculator():
    """
    Renders the Financial Calculator UI Component.
    
    This function manages the entire calculator state and layout.
    It takes user inputs for tuition, living costs, and funding, 
    and outputs a detailed financial breakdown.
    """
    PLACEHOLDER = "__none__"

    currencies_path = _find_currencies_file()

    # Graceful degradation: Fallback to basic currencies if CSV is missing/corrupt
    try:
        if currencies_path is None:
            raise FileNotFoundError("No currencies CSV found. Put it in ./csv/ or ./Project/extras/data/")

        df_currencies, currency_list, symbol_map = _load_currencies(currencies_path)

    except Exception as e:
        st.warning(f"Could not load currencies CSV. Using fallback.\nDetails: {e}")
        currency_list = ["USD", "GBP", "BRL"]
        symbol_map = {"USD": "$", "GBP": "£", "BRL": "R$"}

    # --- Header Section ---
    st.markdown(
        """
        <div style='text-align: center; padding-bottom: 20px;'>
            <h1 style='color: #F4B400; margin-bottom: 0;'>Financial Path Planner</h1>
            <p style='color: gray; font-size: 18px;'>Strategize your investment in higher education.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Main Input Form ---
    with st.container(border=True):
        with st.form("calc", border=False):
            st.markdown("### Academic Investment")
            col1, col2 = st.columns(2)
            
            tuition = col1.number_input("Total Tuition Program Cost (€)")
            fees = col2.number_input("Mandatory Fees / Books / Insurance (€)")

            st.divider()

            st.markdown("### Lifestyle & Living")
            col3, col4 = st.columns(2)
            
            living = col3.number_input("Estimated Monthly Living Cost (€)")
            months = col4.number_input("Study Duration (Months)")

            st.divider()

            st.markdown("### Funding & Offsets")
            c_s1, c_s2 = st.columns([2, 1])
            scholarship = c_s1.slider("Tuition Scholarship Award (%)", 0, 100, 0)
            
            part_time = c_s2.number_input("Monthly Income Offset (€)")

            st.divider()

            st.markdown("### Currency Conversion")
            col_ex1, col_ex2 = st.columns([1, 1])

            def _fmt(n: str) -> str:
                if n == PLACEHOLDER:
                    return "Select a currency…"
                sym = (symbol_map.get(n, "") or "").strip()
                return f"{n} ({sym})" if sym else n

            currency_options = [PLACEHOLDER] + currency_list

            currency_name = col_ex1.selectbox(
                "Local Currency",
                currency_options,
                index=0,  # start with no currency selected
                format_func=_fmt,
                key="calc_currency",
            )

            exchange = col_ex2.number_input(
                "Exchange Rate",
                format="%.4f",
                disabled=False,
                help=(
                    "Optional. Pick a currency if you want conversion."
                    if currency_name == PLACEHOLDER
                    else f"How much is 1 Euro worth in {currency_name}?"
                ),
                key="calc_exchange",
            )

            submitted = st.form_submit_button("Generate Financial Breakdown", use_container_width=True)

    # --- Calculation Logic & Results ---
    if submitted:
        scholarship_val = tuition * (scholarship / 100)
        tuition_net = tuition - scholarship_val + fees
        living_gross = living * months
        income_offset = part_time * months
        # Prevent negative living costs
        living_net = max(0, living_gross - income_offset)

        total_eur = round(tuition_net + living_net, 2)

        # Local currency display logic
        local_label = "Total (Local)"
        local_display = "—"

        if currency_name != PLACEHOLDER:
            local_label = f"Total ({currency_name})"
            if exchange > 0:
                total_local = round(total_eur * exchange, 2)
                curr_symbol = (symbol_map.get(currency_name, "") or "").strip()
                local_display = f"{curr_symbol}{total_local:,.2f}" if curr_symbol else f"{total_local:,.2f}"
            else:
                local_display = "Set exchange rate"

        # --- Visual Output ---
        st.markdown("---")
        st.subheader("Financial Summary")

        m1, m2, m3 = st.columns(3)
        m1.metric("Net Academic Cost", f"€{tuition_net:,.0f}")
        m2.metric("Total Investment (€)", f"€{total_eur:,.2f}")
        m3.metric(local_label, local_display)

        col_res1, col_res2 = st.columns([1, 1.2])

        with col_res1:
            st.markdown("#### 📝 Itemized Costs")
            summary_data = {
                "Description": ["Base Tuition", "Scholarship", "Mandatory Fees", "Gross Living Cost", "Income Offset"],
                "Amount (€)": [
                    f"€{tuition:,.0f}",
                    f"-€{scholarship_val:,.0f}",
                    f"€{fees:,.0f}",
                    f"€{living_gross:,.0f}",
                    f"-€{income_offset:,.0f}",
                ],
            }
            st.table(pd.DataFrame(summary_data))

        with col_res2:
            monthly_invest = (total_eur / months) if months > 0 else 0
            st.info(
                f"**Strategic Insight:**\n\n"
                f"Over a **{months}-month** period, your effective monthly investment is **€{monthly_invest:,.2f}**. "
                f"Your scholarship reduces your total burden by **€{scholarship_val:,.0f}**."
            )