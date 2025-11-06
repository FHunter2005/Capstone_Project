# Professional Contract Analyzer

This is a **complete, production-ready AI application** demonstrating professional architecture patterns.

## Project Structure

```
contract_analyzer/
├── app.py                      # Streamlit UI (entry point)
├── .env.example                # Environment template
├── README.md                   # This file
│
├── services/                   # Business logic layer
│   ├── __init__.py
│   ├── contract_service.py     # Contract domain logic
│   ├── document_service.py     # PDF processing
│   └── ai_service.py           # All Gemini API calls
│
├── tools/                      # Function calling tools
│   ├── __init__.py
│   ├── date_calculator.py      # Date calculations
│   └── amount_calculator.py    # Financial calculations
│
└── utils/                      # Shared utilities
    ├── __init__.py
    ├── tracing.py              # Langfuse configuration
    └── config.py               # Environment variables
```

## Architecture Principles

### 1. Separation of Concerns
- **UI Layer (`app.py`)**: Only handles display and user interaction
- **Service Layer (`services/`)**: Contains all business logic
- **AI Layer (`ai_service.py`)**: Isolated AI/LLM operations
- **Tools Layer (`tools/`)**: Precise calculations

### 2. Dependency Injection
- Services receive dependencies in constructor
- Easy to test with mock dependencies
- Easy to swap implementations

### 3. Observability
- Every important function has `@observe()` decorator
- Full trace visibility in Langfuse
- Debug production issues easily

### 4. Reusability
- Services can be imported and used anywhere
- No coupling to Streamlit
- Works in CLI, API, or other UIs

## Setup

### 1. Install Dependencies

```bash
uv add google-genai streamlit langfuse python-dotenv
```

### 2. Configure Environment

```bash
# Copy example and fill in your keys
cp .env.example .env

# Edit .env with your API keys
```

### 3. Run Application

```bash
uv run streamlit run app.py
```

## How It Works

### Data Flow Example

When a user uploads a contract PDF:

```
1. User uploads PDF in Streamlit UI (app.py)
        ↓
2. app.py calls: service.analyze_contract(file_bytes)
        ↓
3. ContractService.analyze_contract() orchestrates:
   a. doc_service.validate_pdf(file_bytes)
   b. ai_service.extract_structured(file_bytes, schema)
   c. date_calc.days_until(expiry_date)
   d. amount_calc.calculate_total_value(...)
        ↓
4. Returns enriched contract data
        ↓
5. app.py displays results
```

**Every step is traced in Langfuse!**

### Tracing Flow

With `@observe()` decorators, Langfuse shows:

```
analyze_contract (parent)
├── validate_pdf
├── extract_structured
│   └── Gemini API call (input, output, tokens, latency)
├── days_until
└── calculate_total_value
```

## Testing Services

Services can be tested independently:

```python
# test_contract_service.py
from services.contract_service import ContractService

def test_analyze_contract():
    service = ContractService()

    with open("test_contract.pdf", "rb") as f:
        result = service.analyze_contract(f.read())

    assert "parties" in result
    assert "expiration_date" in result
```

No Streamlit required!

## Reusing Services

Use services in different contexts:

```python
# CLI script
from services.contract_service import ContractService

service = ContractService()

with open("contract.pdf", "rb") as f:
    data = service.analyze_contract(f.read())

print(f"Parties: {data['parties']}")
```

```python
# API endpoint (FastAPI)
from fastapi import FastAPI, UploadFile
from services.contract_service import ContractService

app = FastAPI()
service = ContractService()

@app.post("/analyze")
async def analyze(file: UploadFile):
    content = await file.read()
    return service.analyze_contract(content)
```

## Adding New Features

### Add a New Service

1. Create file in `services/`
2. Add `@observe()` to important methods
3. Import and use in other services or UI

### Add a New Tool

1. Create file in `tools/`
2. Add `@observe()` to functions
3. Use in service layer

### Extend UI

1. Keep business logic in services
2. UI only handles display and user input
3. Call service methods

## Key Takeaways

### ✅ Benefits of This Architecture

- **Testable**: Services work without UI
- **Maintainable**: Clear separation makes changes easy
- **Observable**: See everything in Langfuse
- **Reusable**: Services work in any interface
- **Team-friendly**: Different files for different concerns
- **Scalable**: Easy to add features without breaking things

### ❌ What We Avoided

- Monolithic single-file apps
- UI mixed with business logic
- Repeated client initialization
- Hardcoded values everywhere
- No visibility into what's happening
- Untestable code

## Learning Resources

- [Clean Architecture](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Service Layer Pattern](https://martinfowler.com/eaaCatalog/serviceLayer.html)
- [Langfuse Docs](https://langfuse.com/docs)
- [Streamlit Docs](https://docs.streamlit.io)

## Next Steps

**Use this as a template for your team project!**

1. Copy this structure
2. Replace "contract" with your domain
3. Define your schemas and business logic
4. Build your UI
5. Add your domain-specific tools
6. Deploy to Streamlit Cloud

**You have everything you need to build professional AI applications!** 🚀
