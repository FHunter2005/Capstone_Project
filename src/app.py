"""
Professional Contract Analyzer - Main Application

This is the UI layer - handles ONLY user interaction and display.
All business logic is in services.

Run with: uv run streamlit run Week_8/examples/03_professional_structure/app.py

Project Structure:
app.py               <- You are here (UI only)
services/
  contract_service.py  <- Contract domain logic
  document_service.py  <- PDF processing
  ai_service.py        <- All Gemini API calls
tools/
  date_calculator.py   <- Date calculations
  amount_calculator.py <- Financial calculations
utils/
  tracing.py           <- Langfuse configuration
  config.py            <- Environment variables
"""

import streamlit as st
from services.contract_service import ContractService
from utils.tracing import init_tracing
from utils.config import load_config

# ============================================================================
# UI CONFIGURATION
# ============================================================================

st.set_page_config(
    page_title="Contract Analyzer Pro",
    page_icon="📄",
    layout="wide"
)

# Initialize tracing and config
init_tracing()
config = load_config()

# ============================================================================
# SERVICE INITIALIZATION
# ============================================================================

@st.cache_resource  # ✅ Cache service initialization
def get_service():
    """Initialize contract service once."""
    return ContractService(model=config.get("MODEL", "gemini-2.5-flash-lite"))

service = get_service()

# ============================================================================
# UI COMPONENTS
# ============================================================================

def render_header():
    """Render page header."""
    st.title("📄 Contract Analyzer Pro")
    st.caption("Professional architecture with full observability")

def render_expiry_alert(days: int):
    """Render expiry status alert."""
    if days < 0:
        st.error(f"⚠️ Contract expired {abs(days)} days ago!")
    elif days < 30:
        st.warning(f"⚠️ Expiring soon: {days} days remaining")
    elif days < 90:
        st.info(f"ℹ️ Expires in {days} days")
    else:
        st.success(f"✅ Active for {days} more days")

def render_sidebar():
    """Render sidebar with settings and info."""
    with st.sidebar:
        st.header("⚙️ Settings")

        st.info(f"Model: {config.get('MODEL')}")
        st.success("✅ Tracing enabled")

        st.divider()

        if st.button("🗑️ Clear Session", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

        st.divider()

        with st.expander("🏗️ Architecture Info"):
            st.markdown("""
            **Clean Architecture:**
            - ✅ Separated layers (UI, Services, AI, Tools)
            - ✅ All operations traced
            - ✅ Testable components
            - ✅ Reusable services
            - ✅ Team-friendly structure

            **Files:**
            - `app.py` - UI only
            - `services/` - Business logic
            - `tools/` - Calculations
            - `utils/` - Configuration

            **Check Langfuse dashboard for traces!**
            """)

def render_contract_info(data: dict):
    """Render contract information display."""
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("📋 Contract Details")
        st.json({
            "parties": data.get("parties", []),
            "effective_date": data.get("effective_date"),
            "expiration_date": data.get("expiration_date")
        })

    with col2:
        st.subheader("💰 Payment Terms")
        st.json({
            "amount": data.get("payment_amount"),
            "frequency": data.get("payment_frequency"),
            "total_value": data.get("total_value")
        })

    # Expiry status
    if data.get('days_until_expiry') is not None:
        render_expiry_alert(data['days_until_expiry'])

    # Key obligations
    if data.get('key_obligations'):
        st.subheader("📝 Key Obligations")
        for i, obligation in enumerate(data['key_obligations'], 1):
            st.write(f"{i}. {obligation}")

def render_chat_interface(contract_data: dict):
    """Render chat interface for questions."""
    st.subheader("💬 Ask Questions")

    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Chat input
    if question := st.chat_input("Ask about this contract"):
        # Display user message
        with st.chat_message("user"):
            st.write(question)
        st.session_state.messages.append({"role": "user", "content": question})

        # Get AI response from service
        with st.chat_message("assistant"):
            with st.spinner("Analyzing..."):
                try:
                    answer = service.answer_question(question, contract_data)
                    st.write(answer)
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": answer
                    })
                except Exception as e:
                    st.error(f"Error: {e}")

def render_calculations(contract_data: dict):
    """Render calculation tools."""
    st.subheader("🧮 Contract Analytics")

    col1, col2, col3 = st.columns(3)

    with col1:
        if contract_data.get('total_value'):
            st.metric(
                "Total Value",
                f"${contract_data['total_value']:,.2f}"
            )

    with col2:
        if contract_data.get('days_until_expiry') is not None:
            st.metric(
                "Days Until Expiry",
                contract_data['days_until_expiry'],
                delta=None,
                delta_color="inverse"
            )

    with col3:
        if contract_data.get('renewal_date'):
            st.metric(
                "Renewal Date",
                contract_data['renewal_date']
            )

# ============================================================================
# MAIN APPLICATION FLOW
# ============================================================================

def main():
    """Main application logic - coordinates UI flow."""
    render_header()
    render_sidebar()

    # File upload
    uploaded = st.file_uploader(
        "Upload Contract PDF",
        type=['pdf'],
        help="Upload a PDF contract for analysis"
    )

    if uploaded:
        # Show analysis in tabs
        tab1, tab2, tab3 = st.tabs(["📊 Analysis", "💬 Q&A", "📈 Analytics"])

        with tab1:
            # Analyze contract if not in session
            if "contract_data" not in st.session_state:
                with st.spinner("🔍 Analyzing contract..."):
                    try:
                        # Service handles everything
                        contract_data = service.analyze_contract(uploaded.read())
                        st.session_state.contract_data = contract_data
                        st.success("✅ Analysis complete!")
                    except Exception as e:
                        st.error(f"❌ Error analyzing contract: {e}")
                        st.stop()

            # Display contract info
            render_contract_info(st.session_state.contract_data)

        with tab2:
            # Chat interface
            if "contract_data" in st.session_state:
                render_chat_interface(st.session_state.contract_data)
            else:
                st.info("Upload and analyze a contract first")

        with tab3:
            # Analytics
            if "contract_data" in st.session_state:
                render_calculations(st.session_state.contract_data)
            else:
                st.info("Upload and analyze a contract first")

    else:
        # Welcome screen
        st.info("👆 Upload a contract PDF to get started")

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("""
            ### ✨ Features
            - 📄 **Smart PDF Analysis** - Extract key information automatically
            - 💬 **Interactive Q&A** - Ask questions about your contracts
            - 🧮 **Automatic Calculations** - Dates, values, and deadlines
            - 📊 **Contract Analytics** - Visualize important metrics
            """)

        with col2:
            st.markdown("""
            ### 🏗️ Professional Architecture
            - ✅ **Layered Design** - Clean separation of concerns
            - ✅ **Fully Traced** - All operations visible in Langfuse
            - ✅ **Testable** - Services can be tested independently
            - ✅ **Maintainable** - Easy to understand and extend
            """)

        st.divider()

        st.markdown("""
        ### 🚀 How It Works

        1. **Upload** a contract PDF
        2. **AI analyzes** and extracts structured data
        3. **Ask questions** in natural language
        4. **Get insights** with automatic calculations

        **All operations are traced for debugging and monitoring!**
        """)

if __name__ == "__main__":
    main()
