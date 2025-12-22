# MasterMatch

**Your personal AI advisor for Master’s degrees in Portugal.**

## Overview

MasterMatch is an AI-powered application designed to streamline the search for Master's degree programs. By leveraging **Retrieval-Augmented Generation (RAG)**, it connects students with factual, data-driven academic advice.

Unlike generic chatbots, MasterMatch combines a specialized vector database of university programs with personal user context. Users can upload their CVs, and the system uses this data—along with background, preference city, and budget—to provide highly personalized recommendations, tuition estimates, and location visualization.

## Features

- **AI Academic Advisor:** A conversational agent powered by **Google Gemini** that provides factual answers about programs, curriculum, and requirements.
- **Smart CV Analysis:** Users can upload a PDF CV; the system extracts the text to tailor recommendations based on professional experience and academic background.
- **Vector Search (RAG):** Utilizes **MongoDB Atlas Vector Search** to semantically match user queries with real program data, reducing hallucinations.
- **University Map:** Interactive map visualization showing the exact locations of universities using Google Maps data.
- **Student Budget Calculator:** A built-in tool to help users estimate the total cost of their education.
- **Favorites Masters:** Users can save programs to a personalized list for easy comparison.
- **Secure Authentication:** User registration and login system to save chat history and preferences.

## Tech Stack
**Backend:**
- **Python 3.13.9**
- **FastAPI:** Powers the REST API backend, managing secure user logins and preparing the necessary profile data for the AI.
- **Google Gemini API:** `gemini-flash-latest` for reasoning and `text-embedding-004` for embeddings.

**Frontend:**
- **Streamlit:** Provides the interactive web interface, managing session state and UI components.

**Database:**
- **MongoDB Atlas:** Stores user profiles, chat logs, and the Master's collection with Vector Search indices.

**AI & Observability:**
- **Langfuse:** used for tracing agent steps, monitoring latency, and debugging tool calls.
- **RAG Architecture:** Custom implementation using agentic tool calling.

## Architecture

## Installation & Setup
### Prerequisites
- Python 3.10 or higher
- A MongoDB Atlas Cluster (with Vector Search enabled)
- API Keys for Google Gemini and Langfuse

### Installation Steps
1. Clone the repository:
```bash
git clone [https://github.com/FHunter2005/Capstone_Project.git]
cd MasterMatch
```
2. Install dependencies:
```bash
uv sync ?????
```
3. Set up environment variables:
```bash
Create a `.env` file in the root directory and add the following keys (replace with your own credentials):
```

**Required environment variables:**
```
GOOGLE_API_KEY=your_google_key_here
LANGFUSE_SECRET_KEY=your_langfuse_secret
LANGFUSE_PUBLIC_KEY=your_langfuse_public
LANGFUSE_BASE_URL=https://cloud.langfuse.com
LANGFUSE_TRACING_ENABLED=true
LANGFUSE_TRACING_ENVIRONMENT=dev
MONGO_URI=your_mongodb_uri
MONGO_DB=Capstone_Project
BACKEND_BASE_URL=http://127.0.0.1:8000
```

4. Run the application:

Terminal 1 (Backend):
```bash
uvicorn backend.main:app --reload --port 8000
```
Terminal 2 (Frontend)
```bash
uv run streamlit run app.py
```

## Usage

**Register/Login:** Create an account to start a session.

![Login Screen](assets/Login.jpeg)

**Complete Profile**: Navigate to the Profile tab. You can either fill in the questionnaire manually or upload your CV (PDF) for automatic extraction.

**Chat:** Go to the Chat tab and ask questions like "Find me a Marketing Master in Lisbon under 5000€".

**Visualize:** Use the Map tab to see where the recommended universities are located.

*Add screenshots or GIFs here to visually demonstrate your application's key features*

## Deployment

**Live Application:** [Your deployed URL]

**Deployment Platform:** [Streamlit Cloud / Render / Vercel / etc.]

Instructions for deploying your own instance (if applicable).

## Project Structure

```
project-root/
├── app.py                 # Main application entry point
├── services/              # Business logic layer
├── tools/                 # Function calling tools
├── utils/                 # Utility functions
├── docs/
│   └── ARCHITECTURE.md    # Architecture decisions and explanations
├── requirements.txt       # Dependencies
├── .env.example          # Environment variable template
└── README.md             # This file
```

**Note:** Component-level READMEs (e.g., `services/README.md`, `tools/README.md`) are recommended if those components need detailed explanation.

## Team

- Team Member 1 - [Role/Responsibilities]
- Team Member 2 - [Role/Responsibilities]
- Team Member 3 - [Role/Responsibilities]
- Team Member 4 - [Role/Responsibilities]

## License

[Your chosen license - MIT, Apache, etc. - not necessary]

---

## What Makes a Good README?

Your README should answer:
- **What** does this application do?
- **Why** does it exist / what problem does it solve?
- **How** do I run it locally?
- **Who** built it?

Keep it clear, organized, and professional. This is often the first thing evaluators and potential users will see.