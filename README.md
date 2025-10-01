# ConvAI Dungeon Master

An AI-powered Dungeons & Dragons Dungeon Master application that uses conversational AI to narrate adventures, manage game rules, and track character state.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Endpoints](#api-endpoints)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

ConvAI Dungeon Master is a research project developed at Fontys University of Applied Sciences that combines Large Language Models with traditional tabletop RPG mechanics. The system acts as an intelligent Dungeon Master, interpreting player actions, adjudicating rules, and generating narrative responses.

**Team:**
- Sjoerd de Man
- Lonn van Bokhorst
- Mark de Graaf

**Institution:** Fontys University of Applied Sciences, FICT  
**Research Group:** Interaction Design

## ✨ Features

- **Dynamic Narrative Generation:** Uses Groq's Llama 3.1 to generate compelling, context-aware story descriptions.
- **Intent Recognition:** Understands player intentions (e.g., casting a spell, attacking, moving) from natural language.
- **D&D 5e Rules Adjudication:**
  - **Spellcasting:** Validates if spells are known, prepared, and if spell slots are available. Correctly handles cantrips.
  - **Combat Rolls:** Performs automatic dice rolls for attacks (1d20 + modifiers) and damage (e.g., 1d4, 8d6).
  - **Critical Hits/Misses:** Recognizes natural 20s and 1s on attack rolls.
- **Interactive UI:**
  - **Character Sheet Display:** Shows all character stats, skills, spells, and equipment.
  - **Live Action Summary:** A real-time log that displays the mechanical outcomes of your actions, including dice rolls, spell checks, and damage dealt.
  - **NPC Health Tracker:** Automatically tracks enemy health with visual health bars when they enter combat.
- **Intelligent DM Clarifications:** If an action is ambiguous (e.g., casting a spell without a target), the DM will ask a direct question to clarify before proceeding.
- **Conversation Management:** Maintains a history of the conversation to ensure coherent and context-aware responses.

## 🏗️ Architecture

### Backend (Python/Flask)

The backend is built with Flask and follows a modular architecture:

```
┌─────────────┐
│   Frontend  │
│  (Browser)  │
└──────┬──────┘
       │ HTTP/JSON
┌──────▼──────┐
│   Flask     │
│   Server    │
├─────────────┤
│ app.py      │◄────┐
│             │     │
│ orchestrator│     │ Dependencies
│   .py       │     │
│             │     │
│ rules_engine│     │
│   .py       │     │
└──────┬──────┘     │
       │            │
   ┌───▼────────────▼──┐
   │  Groq LLM API     │
   │  (llama-3.1-8b)   │
   └───────────────────┘
```

**Key Components:**

1. **app.py**: Main Flask application
   - Route handlers (`/chat`, `/character`)
   - Data loading (knowledge base, character sheet)
   - CORS configuration
   - Error handling and logging

2. **orchestrator.py**: Intent recognition system
   - Uses LLM to classify player actions
   - Extracts structured data (spell names, targets, etc.)
   - Returns JSON-formatted intent data

3. **rules_engine.py**: Game rules validation
   - Spellcasting validation (known spells, spell slots, etc.)
   - Extensible for other D&D mechanics

4. **character.json**: Character state
   - Complete D&D 5e character sheet in JSON format
   - Easily editable for different characters

5. **knowledge_base/**: D&D 5e ruleset
   - 16 JSON files covering all aspects of D&D 5e
   - Used for rule lookups and validation

### Frontend (HTML/CSS/JavaScript)

Simple, clean interface built with:
- **Bulma CSS**: Responsive framework for layout
- **jQuery**: DOM manipulation and AJAX requests
- **Vanilla JS**: Chat functionality and character sheet display

## 🚀 Installation

### Prerequisites

- Python 3.11 or higher
- pip (Python package manager)
- A Groq API key ([get one here](https://groq.com))

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/convai-dungeon-master.git
   cd convai-dungeon-master
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate the virtual environment**
   - Windows (Git Bash):
     ```bash
     source venv/Scripts/activate
     ```
   - Windows (CMD):
     ```cmd
     venv\Scripts\activate.bat
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r backend/requirements.txt
   ```

5. **Configure environment variables**
   
   Create a `.env` file in the `backend/` directory:
   ```bash
   cd backend
   touch .env
   ```
   
   Add your Groq API key:
   ```
   GROQ_API_KEY=your_api_key_here
   ```

6. **Run the server**
   ```bash
   python backend/app.py
   ```
   
   The server will start on `http://127.0.0.1:5000`

7. **Open the frontend**
   
   Open `index.html` in your web browser. For best results, serve it through a local web server:
   ```bash
   # Using Python's built-in server
   python -m http.server 5500
   ```
   
   Then navigate to `http://127.0.0.1:5500`

## 💻 Usage

### Starting an Adventure

1. Open the application in your browser
2. The character sheet for "Eldrin" (the default character) will load on the left
3. The chat interface appears on the right with a welcome message

### Playing the Game

Simply type what you want your character to do:

- **General actions**: "I search the room for traps"
- **Spellcasting**: "I cast Magic Missile at the goblin"
- **Combat**: "I attack the orc with my quarterstaff"
- **Interaction**: "I try to persuade the guard"

The AI will:
1. Interpret your intent
2. Check relevant rules
3. Generate a narrative response

### Customizing Your Character

Edit `backend/character.json` to create your own character. The file contains a complete D&D 5e character sheet in JSON format.

## 📁 Project Structure

```
convai-dungeon-master/
├── backend/
│   ├── app.py                 # Main Flask application
│   ├── orchestrator.py        # Intent recognition
│   ├── rules_engine.py        # Rules adjudication
│   ├── character.json         # Character sheet data
│   ├── requirements.txt       # Python dependencies
│   ├── .env                   # Environment variables (not in git)
│   └── knowledge_base/        # D&D 5e rules (JSON files)
│       ├── 00 legal.json
│       ├── 01 races.json
│       ├── 02 classes.json
│       └── ... (16 files total)
│
├── static/
│   ├── css/
│   │   ├── bulma.min.css     # CSS framework
│   │   └── index.css          # Custom styles
│   ├── js/
│   │   └── index.js           # Frontend logic
│   └── images/
│       ├── favicon.ico        # Site icon
│       └── ... (app icons)
│
├── venv/                      # Virtual environment (not in git)
├── .gitignore                 # Git ignore rules
├── index.html                 # Main frontend page
├── README.md                  # This file
├── LICENSE                    # Project license
└── log.md                     # Development log
```

## 🔌 API Endpoints

### GET `/character`

Returns the current character sheet.

**Response:**
```json
{
  "name": "Eldrin",
  "class": "Wizard",
  "level": 1,
  "race": "High Elf",
  "ability_scores": { ... },
  "skills": { ... },
  "spellcasting": { ... },
  ...
}
```

### POST `/chat`

Sends a player message and receives a narrative response.

**Request:**
```json
{
  "message": "I cast Magic Missile at the goblin"
}
```

**Response:**
```json
{
  "response": "Eldrin raises his hand and three glowing darts of magical force streak toward the goblin...",
  "character_name": "Eldrin",
  "character_portrait": "https://..."
}
```

**Error Response:**
```json
{
  "error": "Description of the error"
}
```

## 🛠️ Development

### Running in Development Mode

The Flask server runs in debug mode by default, which enables:
- Automatic reloading on code changes
- Detailed error pages
- Enhanced logging

### Logging

Logs are written to the console with timestamps:
```
2025-10-01 13:31:42 - INFO - Processing message: I cast fireball
2025-10-01 13:31:42 - INFO - Intent recognized: {'intent': 'cast_spell', ...}
```

### Adding New Rules

1. Add validation logic to `backend/rules_engine.py`
2. Update `backend/orchestrator.py` to recognize the new intent type
3. Add corresponding knowledge base entries if needed

### Customizing the AI

Edit the system prompt in `backend/app.py`:
```python
conversation_history = [
    {
        "role": "system",
        "content": "Your custom DM personality and instructions..."
    }
]
```

## 🤝 Contributing

This is an academic research project. Contributions are welcome!

### Guidelines

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Style

- Python: Follow PEP 8
- JavaScript: Use ES6+ features
- Comments: Document complex logic

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built using [Groq](https://groq.com)'s fast LLM inference
- D&D 5e rules provided under the [Open Gaming License](https://dnd.wizards.com/resources/systems-reference-document)
- Based on the [Academic Project Page Template](https://github.com/eliahuhorwitz/Academic-project-page-template)
- Bulma CSS Framework

## 📞 Contact

For questions or collaboration inquiries:
- Sjoerd de Man
- Lonn van Bokhorst - [LinkedIn](https://www.linkedin.com/in/lonnvanbokhorst/)
- Mark de Graaf - [LinkedIn](https://www.linkedin.com/in/mark-de-graaf-b630278/)

---

*Developed at Fontys University of Applied Sciences, Research Group on Interaction Design*
