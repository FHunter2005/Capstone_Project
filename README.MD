# MasterMatch

**Your personal AI advisor for Master’s degrees in Portugal.**

## Overview

MasterMatch is an AI-powered application designed to streamline the search for Master's degree programs. By leveraging **Retrieval-Augmented Generation (RAG)**, it connects students with factual, data-driven academic advice.

Unlike generic chatbots, MasterMatch combines a specialized vector database of university programs with personal user context. Users can upload their CVs, and the system uses this data along with background, preference city, and budget to provide highly personalized recommendations, tuition estimates, and location visualization.

## Features

- **AI Academic Advisor:** A conversational agent powered by **Google Gemini** that provides factual answers about programs, curriculum, and requirements.
- **CV Analysis:** Users can upload a PDF CV; the system extracts the text to tailor recommendations based on professional experience and academic background.
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
pip install -r requirements.txt ?????
```
3. Set up environment variables:

Create a `.env` file in the root directory and add the following keys (replace with your own credentials):


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

**Complete Profile**: Navigate to the Profile tab. You can either fill in the questionnaire manually or upload your CV (PDF) for automatic extraction.

**Chat:** Go to the Chat tab and ask questions like "Find me a Marketing Maste.

**Visualize:** Use the Map tab to see where the recommended universities are located.

*Add screenshots or GIFs here to visually demonstrate your application's key features*

## Deployment

**Live Application:** [\[GitHub Repository\]](https://github.com/FHunter2005/Capstone_Project.git)

**Deployment Platform:** [Streamlit Cloud / Render / Vercel / etc.]

Instructions for deploying your own instance (if applicable).

## Project Structure

```
Project/
├── ai/    
│    ├── ai_client.py            # Gemini Client Wrapper
│    └── models.ipynb            # Model experiments
├── backend/
│     └── main.py                # FastAPI Backend Entry Point
├── extras/
│     ├── data/
│     └── photos/
├── services/
│     ├── auth_service.py        # User Management & Auth
│     ├── db_service.py          # MongoDB Connection
│     └── location_service.py    # Maps Logic
├── tools/                       # Utility functions
│     └── agent_tools.py         # AI Function Calling Tools
├── utils/
│     ├── config.py              # Config loader
│     ├── observability.py       # Langfuse setup
│     └── web_scrapping.ipynb
├── docs/
│   └── ARCHITECTURE.md          # Architecture decisions and diagrams Team
├── app.py                       # Streamlit Frontend Entry Point
├── calculator.py                # Budget Calculator Logic
├── map_tab.py                   # Map Visualization Logic
├── requirements.txt             # Project Dependencies
├── .env.example                 # Template for environment variables
└── README.md                    # This file
```

**Note:** Component-level READMEs (e.g., `services/README.md`, `tools/README.md`) are recommended if those components need detailed explanation.

## Team

- Duarte Fernandes — Team Lead & Backend Developer
- Filipe Caçador — Data Engineer & Domain Research Lead
- David Carrilho — Backend Developer
- Duarte Oliveira — Frontend Developer
---
