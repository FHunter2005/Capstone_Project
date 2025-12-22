# MasterMatch Architecture & Technical Decisions

This document explains how the MasterMatch application is built, how the code is organized, and why we made specific technical choices.

## 1. High-Level Architecture

MasterMatch follows a **Client-Server Architecture**. This means the application is split into two independent parts:
1.  **The Client (Frontend):** The visual interface the user interacts with.
2.  **The Server (Backend):** The logic that runs in the background, handling data and AI.

This separation ensures the code is clean, organized, and scalable.

## 2. System Layers

The system is divided into four distinct layers, each with a specific job:

### **A. Presentation Layer (Frontend)**
* **Technology:** Streamlit (`app.py`)
* **What it does:** This is the "Face" of the application. It captures what the user types, handles the login screen, and displays the chat messages and university cards.
* **Role:** It does not make decisions; it simply displays data sent by the backend.

### **B. Service Layer (Backend)**
* **Technology:** FastAPI (`backend/main.py`)
* **What it does:** This is the "Traffic Controller". It receives messages from the frontend and decides what to do with them.
* **Role:** It manages user security (checking passwords) and prepares the data before sending it to the AI.

### **C. Intelligence Layer (AI)**
* **Technology:** Google Gemini 1.5 Flash (`ai_client.py`)
* **What it does:** This is the "Reasoning Engine". It understands the user's natural language questions.
* **Role:** It decides *when* to search the database. For example, if a user asks for "Marketing Masters," the AI knows it needs to use a tool to look up real data.

### **D. Data Layer (Storage)**
* **Technology:** MongoDB Atlas (`db_service.py`)
* **What it does:** This is the "Long-Term Memory".
* **Role:** It stores two types of data:
    1.  **User Data:** Profiles, passwords, and chat history.
    2.  **Vector Data:** Mathematical representations of university programs, allowing the AI to search by meaning (Semantic Search) rather than just keywords.

---

## 3. Code Organization & Modules

To keep the project clean, we organized the code into specific folders based on their function:

### `services/` (The Core Logic)
This folder contains the main business logic.
* **`auth_service.py`:** Handles everything related to users—registering new accounts, logging in, and hashing passwords for security.
* **`db_service.py`:** The central place for database connections. All code that reads or writes to MongoDB lives here.
* **`location_service.py`:** Converts university names into map coordinates for the "Visualize" tab.

### `tools/` (AI Actions)
* **`agent_tools.py`:** These are the "skills" we gave the AI. This file contains the function that allows Gemini to actually search our MongoDB database for master's degrees.

### `utils/` (Helpers)
* **`observability.py`:** Sets up **Langfuse**. This helps us track and debug the AI's "thought process" in real-time.
* **`config.py`:** Loads sensitive passwords (API Keys) securely from the environment file so they aren't hardcoded.

---

## 4. Key Technical Decisions & Justifications

### 1. Retrieval-Augmented Generation (RAG)
**Decision:** We connected the AI to a database of real master's programs.
* **Why?** A standard AI (like ChatGPT) hallucinates facts. It doesn't know the specific tuition fees or locations of Portuguese universities. By retrieving real data from MongoDB and feeding it to the AI, we ensure the answers are factual and accurate.

### 2. Dynamic Context Injection
**Decision:** We automatically insert the user's profile into every chat message hidden from view.
* **Why?** If a student with a 5000€ budget asks "What should I study?", a generic AI gives generic advice. Our system injects "User Budget: 5000€" into the prompt *before* the AI sees it. This forces the AI to give personalized advice without the user having to repeat themselves.

### 3. Separation of Frontend and Backend
**Decision:** We didn't write everything in one big Streamlit file. We built a separate API.
* **Why?** This is a professional standard. It keeps the user interface snappy because the heavy processing happens on the server. It also allows us to easily swap the frontend later (e.g., for a mobile app) without rewriting the logic.

---

## 5. Data Flow: Lifecycle of a Chat Request

Here is what happens step-by-step when a user sends a message:

1.  **User Input:** The user types "Find marketing masters" in the Streamlit app.
2.  **API Call:** Streamlit sends this text to the FastAPI backend.
3.  **Context Loading:** The backend looks up the user's profile (e.g., "Budget: 5000€, GPA: 15") in MongoDB.
4.  **AI Reasoning:** The backend sends the user's text + their profile to Google Gemini.
5.  **Tool Execution:** Gemini realizes it needs data and triggers the `search_masters` tool.
6.  **Database Search:** The system performs a Vector Search in MongoDB to find the best matching programs.
7.  **Final Answer:** Gemini combines the search results into a natural language response (e.g., "I found these 3 programs...").
8.  **Display:** Streamlit shows the text and renders the program cards.