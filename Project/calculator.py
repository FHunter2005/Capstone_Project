# calculator.py
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd
import streamlit as st


def _find_currencies_file() -> Optional[Path]:
    """
    Search common project locations for a currencies file.
    Supports:
      - csv/currencies_clean.csv
      - Project/extras/data/Currencies.csv
      - extras/data/Currencies.csv
      - and a few other common variants
    """
    filenames = ["currencies_clean.csv", "Currencies.csv", "currencies.csv"]

    here = Path(__file__).resolve().parent
    cwd = Path.cwd().resolve()

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
                if p in checked:
                    continue
                checked.add(p)
                if p.exists():
                    return p
    return None


def _load_currencies(path: Path) -> Tuple[pd.DataFrame, list, dict]:
    """
    Loads currencies into:
      - df with columns: name, symbol
      - currency_list
      - symbol_map
    Handles weird CSVs like:
      columns: ['_id', 'name,symbol'] where 'name,symbol' contains "UAE Dirham,د.إ"
    """
    df = pd.read_csv(path, dtype=str, encoding="utf-8-sig", sep=None, engine="python").fillna("")
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Case 1: already correct
    if "name" in df.columns and "symbol" in df.columns:
        pass

    # Case 2: single combined column name "name,symbol"
    elif "name,symbol" in df.columns:
        split = df["name,symbol"].astype(str).str.split(",", n=1, expand=True)
        df["name"] = split[0].astype(str).str.strip()
        df["symbol"] = split[1].fillna("").astype(str).str.strip()

    # Case 3: sometimes it might be "name;symbol"
    elif "name;symbol" in df.columns:
        split = df["name;symbol"].astype(str).str.split(";", n=1, expand=True)
        df["name"] = split[0].astype(str).str.strip()
        df["symbol"] = split[1].fillna("").astype(str).str.strip()

    # Case 4: two columns but wrong headers → assume first is name, second is symbol
    elif df.shape[1] >= 2:
        df = df.rename(columns={df.columns[0]: "name", df.columns[1]: "symbol"})

    else:
        raise ValueError(f"CSV must have currencies info, but columns are: {list(df.columns)}")

    df["name"] = df["name"].astype(str).str.strip()
    df["symbol"] = df["symbol"].astype(str).str.strip()

    df = df[df["name"] != ""].drop_duplicates(subset=["name"], keep="first")

    currency_list = df["name"].tolist()
    symbol_map = dict(zip(df["name"], df["symbol"]))

    if not currency_list:
        raise ValueError("No currencies loaded (name column is empty after cleaning).")

    return df, currency_list, symbol_map


def render_price_calculator():
    PLACEHOLDER = "__none__"

    currencies_path = _find_currencies_file()

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
            tuition = col1.number_input("Total Tuition Program Cost (€)", 0, 200000, 0, 500)
            fees = col2.number_input("Mandatory Fees / Books / Insurance (€)", 0, 10000, 0, 50)

            st.divider()

            st.markdown("### Lifestyle & Living")
            col3, col4 = st.columns(2)
            living = col3.number_input("Estimated Monthly Living Cost (€)", 0, 5000, 0, 50)
            months = col4.number_input("Study Duration (Months)", 0, 60, 0, 1)

            st.divider()

            st.markdown("### Funding & Offsets")
            c_s1, c_s2 = st.columns([2, 1])
            scholarship = c_s1.slider("Tuition Scholarship Award (%)", 0, 100, 0)
            part_time = c_s2.number_input("Monthly Income Offset (€)", 0, 5000, 0, 50)

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
    min_value=0.0,
    value=0.0,
    format="%.4f",
    disabled=False,  # ✅ always editable inside a form
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
        living_net = max(0, living_gross - income_offset)

        total_eur = round(tuition_net + living_net, 2)

        # Local currency display (only if selected + exchange > 0)
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
