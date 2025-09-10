# Development Log for ConvAI Dungeon Master

This log tracks the development of the ConvAI Dungeon Master project.

## Session 1: Initial Setup and Interface

**Date:** 2025-09-10

**Team:** Lonn van Bokhorst (Master), Young Padawan (AI Assistant)

### Changes:

1.  **Refactored `index.html`:**

    - **Rationale:** The initial HTML file was an academic project template. It was heavily modified to serve as the front-end for our Dungeon Master application.
    - Removed academic sections like "Abstract", "Results", "Discussion", "Conclusion", and "BibTeX".
    - Updated the title to "ConvAI Dungeon Master".
    - Changed author information to reflect the project team: Sjoerd van der Lee, Lonn van Bokhorst, and Mark de Graaf.
    - Added a welcoming introduction for the user.
    - Added a chat interface section for user interaction with the DM.

2.  **Styled the Chat Interface in `static/css/index.css`:**

    - **Rationale:** To make the chat interface visually appealing and functional.
    - Added CSS rules for the chat container, message bubbles (for user and DM), and the input area.

3.  **Added Chat Logic in `static/js/index.js`:**
    - **Rationale:** To bring the chat interface to life.
    - Added JavaScript to handle sending and displaying messages in the chat window.
    - Currently, it includes a placeholder response from the DM.

### Next Steps:

- Connect the front-end interface to a backend language model to generate dynamic DM responses.

## Session 2: Backend Setup & Troubleshooting

**Date:** 2025-09-10

**Team:** Sjoerd van der Lee (Master), AI Assistant (Padawan)

### Changes:

1.  **Created a Python Backend with Flask:**
    - **Rationale:** To create a server that can run the AI model and manage the game's state, separating the logic from the frontend presentation.
    - Created `backend/` directory.
    - Added `backend/app.py` with a basic Flask server.
    - Added `backend/requirements.txt` to manage Python dependencies.

2.  **Troubleshot Dependency Issues:**
    - **Problem 1: `ModuleNotFoundError`**: The initial server launch failed because Python couldn't find the Flask library. This was due to an incorrect installation into the project's virtual environment.
    - **Problem 2: `ImportError`**: After fixing the installation, a new error appeared due to a version conflict between `Flask` and its dependency `Werkzeug`.
    - **Solution:** Pinned the `Werkzeug` version in `requirements.txt` to a version known to be compatible with our version of `Flask` (`Werkzeug<3.0.0`) and reinstalled the dependencies.

### Next Steps:

- Integrate the Groq API to connect the backend to a Large Language Model.

## Session 3: AI Integration & Model Troubleshooting

**Date:** 2025-09-10

**Team:** Sjoerd van der Lee (Master), AI Assistant (Padawan)

### Changes:

1.  **Integrated Groq API for AI Storytelling:**
    - **Rationale:** To replace the static backend response with dynamic, AI-generated content, bringing the Dungeon Master to life.
    - Added `groq` and `python-dotenv` to `requirements.txt`.
    - Overhauled `backend/app.py` to connect to the Groq API, manage conversation history, and use a system prompt to guide the AI's behavior.

2.  **Troubleshot API and Model Compatibility Issues:**
    - **Problem 1: `TypeError` on Server Start**: A new dependency conflict between the `groq` and `httpx` libraries prevented the server from starting.
    - **Solution 1:** Pinned the `httpx` version to `0.27.0` in `requirements.txt`.
    - **Problem 2: `model_decommissioned` Error**: The initial models chosen (`llama3-8b-8192` and `llama3-70b-8192`) were no longer supported by the Groq API.
    - **Solution 2:** Researched the currently available models and updated `app.py` to use `llama-3.1-8b-instant`.

### Next Steps:

- Begin **Phase 4: Adding Memory**, which will involve implementing state management for the player's character sheet (e.g., stats, inventory, health).
