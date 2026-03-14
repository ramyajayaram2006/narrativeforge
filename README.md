# 📖 NarrativeForge

> **AI-powered story co-writer · 100% local · zero subscriptions · full creative control**

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.35-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)](https://streamlit.io)
[![Ollama](https://img.shields.io/badge/Ollama-Llama_3.2-4ADE80?style=flat-square)](https://ollama.com)
[![SQLite](https://img.shields.io/badge/SQLite-3-003B57?style=flat-square&logo=sqlite&logoColor=white)](https://sqlite.org)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat-square&logo=docker&logoColor=white)](https://docker.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=flat-square)](LICENSE)
[![Security](https://img.shields.io/badge/Security-bcrypt_·_IDOR_·_XSS_patched-4ADE80?style=flat-square)]()

NarrativeForge is a full-stack creative writing platform where writers co-author stories alongside a locally-running AI. Built end-to-end across a 3-milestone internship at **Infosys Springboard**, it evolved from a prototype with a mocked backend into a production-hardened narrative intelligence engine — without ever sending a word of your manuscript to a cloud server.

---

## ✨ Features at a Glance

| Feature | Description |
|---|---|
| **6 AI Writing Modes** | Continue, Paragraph, Smart Choice, Dialogue Scene, Plot Twist, Inner Monologue |
| **Persistent Story Memory** | Characters, scenes, and world notes injected into every prompt — AI remembers your cast |
| **Emotional Arc Visualiser** | Per-block sentiment analysis rendered as a live arc chart |
| **Character Relationship Map** | Interactive force-directed graph of all characters and their connections |
| **AI Writing Coach** | Structured prose feedback: Strengths, Weaknesses, Suggestions, Next Scene |
| **Cliché & Consistency Checker** | 30+ trope detector + overused words, repeated phrases, absent characters |
| **Story Snapshots** | Named version saves with one-click restore — git for fiction |
| **World Notes Lore Library** | Categorised notes: Lore, Magic System, Geography, History, Factions |
| **3-Format Export** | Flat `.docx`, chapter-structured `.docx`, and Markdown — all in-memory |
| **Live Session Tracker** | Real-time WPM, session word count, and elapsed time in the top bar |
| **Plot Arc Tracker** | 5-stage arc (Beginning → Resolution) with scene timeline |
| **Full-Text Story Search** | Keyword search across titles and all message content |
| **bcrypt Security** | Work factor 12, silent SHA-256 upgrade, brute-force lockout |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Streamlit Frontend                       │
│  app.py → auth.py → dashboard.py → workspace.py             │
└──────────────────────────┬──────────────────────────────────┘
                           │ 5-Layer Prompt
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    AI Pipeline (workspace.py)                │
│  Story-Only Classifier → Prompt Builder → Stream Handler    │
│  Emotional Arc · Cliché Detector · Writing Coach            │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP POST
                           ▼
              ┌────────────────────────┐
              │   Ollama REST API      │
              │   localhost:11434      │
              │   Llama 3.2 · 3B · 2GB│
              └────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                   SQLite (database.py)                       │
│  users · stories · characters · scenes · world_notes ·      │
│  snapshots  —  6 tables, parameterised throughout           │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
narrativeforge/
├── app.py           # Entry point. Session routing FSM
├── auth.py          # Login / sign-up. bcrypt. Brute-force lockout
├── dashboard.py     # Story library. Stats header. Full-text search
├── workspace.py     # AI pipeline. 6 modes. 7 sidebar tabs. Analytics
├── database.py      # All SQLite operations. 6 tables. IDOR-safe
├── styles.py        # CSS injected via st.markdown. 3 style layers
├── utils.py         # Session init. Ollama warm-up thread
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── landing.html     # Project landing page
```

---

## 🚀 Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/yourusername/narrativeforge.git
cd narrativeforge
docker compose up
```

Open [http://localhost:8501](http://localhost:8501)

> Ollama and Llama 3.2 are pulled automatically on first run.

### Option 2 — Local Python

**Prerequisites:** Python 3.11+, [Ollama](https://ollama.com) installed

```bash
# 1. Clone
git clone https://github.com/yourusername/narrativeforge.git
cd narrativeforge

# 2. Install dependencies
pip install -r requirements.txt

# 3. Pull the model (one-time, ~2GB)
ollama pull llama3.2

# 4. Start Ollama server (keep this terminal open)
ollama serve

# 5. In a new terminal, run the app
streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501)

---

## 🤖 AI Prompt Architecture

Every request sends a **5-layer structured prompt** to Llama 3.2:

```
Layer 1  System role + genre + tone
Layer 2  Writing Voice  — natural-language style directive from the writer
Layer 3  Character context — name, role, description, speaking style for all characters
Layer 4  Scene context — current scene title, location, narrative purpose
Layer 5  Last 10 messages + mode-specific directive
```

### Writing Modes

| Mode | Prompt Strategy |
|---|---|
| **Continue** | Complete unfinished sentence in 1-2 sentences |
| **Paragraph** | Write next paragraph in 3-5 sentences, honour all character descriptions |
| **Smart Choice** | Auto-detects incomplete input → routes to Continue or Paragraph |
| **Dialogue** | 6-10 line spoken exchange formatted as `Name: "line"`, per character voice |
| **Plot Twist** | 3-4 sentence earned revelation that recontextualises prior events |
| **Inner Monologue** | 3-5 sentence protagonist thoughts, first/close-third person, lyrical |

### Story-Only Classifier

A pure-Python classifier (no AI call) runs before every request in **microseconds**:

1. **Story keywords** — any match → `STORY` (overrides all other rules)
2. **Blocked prefixes** — 40+ patterns for math, code, health, factual queries → `REDIRECT`
3. **Default** — short prose without keywords → `STORY` (benefit of the doubt)

**Result:** 100% accuracy on 22-case test suite. Off-topic inputs return an instant redirect (< 100ms) without calling Llama 3.2.

---

## 🔒 Security

### Authentication
- **bcrypt** at work factor 12 (~250ms per hash) for all new accounts
- Silent **SHA-256 → bcrypt upgrade** on first login for legacy accounts
- **Brute-force lockout**: 5 failed attempts triggers a 60-second session lockout

### Data Integrity
- **IDOR protection**: all mutation endpoints (`delete_character`, `update_character`, `delete_scene`, `update_scene`) require matching `username` — cross-user access by guessing integer IDs is blocked
- **XSS prevention**: 16 `html.escape()` call sites covering all user-controlled HTML injection points
- **LLM output sanitisation**: `_strip_html()` applied to all streamed and non-streamed AI tokens before storage

### Privacy
- **Zero cloud**: no data transmitted externally at any point
- **Parameterised SQL**: no injection surface throughout `database.py`
- **Local SQLite**: your stories live in a single file on your own disk

---

## 📊 Story Health Dashboard

| Metric | Source |
|---|---|
| Average sentence length | `len(words) / len(sentences)` |
| Flesch-Kincaid reading level | Standard FK formula, grades 1–16 |
| Estimated reading time | 200 wpm baseline |
| Word frequency chart | Counter on stopword-filtered tokens |
| Emotional arc | Per-block +/- word scoring, rendered as bar chart |
| Cliché detection | 30+ pattern list, exact substring match |
| Consistency issues | Overused words · repeated trigrams · long sentences · absent characters |

All metrics computed locally. No AI calls required.

---

## 🐳 Docker Deployment

```yaml
# docker-compose.yml
version: "3.9"
services:
  app:
    build: .
    ports: ["8501:8501"]
    volumes: ["./narrativeforge.db:/app/narrativeforge.db"]
    depends_on: [ollama]
    environment:
      - NARRATIVEFORGE_MODEL=llama3.2

  ollama:
    image: ollama/ollama:latest
    ports: ["11434:11434"]
    volumes: ["ollama_data:/root/.ollama"]
    entrypoint: ["/bin/sh","-c","ollama serve & sleep 5 && ollama pull llama3.2 && wait"]

volumes:
  ollama_data:
```

---

## 🧪 Testing

Milestone 2 manual test suite (all passed):

| Test | Description | Result |
|---|---|---|
| T1 | Ollama responds on localhost:11434 | ✅ |
| T2 | User input produces non-empty AI response | ✅ |
| T3 | Prior story context reflected in next response | ✅ |
| T4 | Sci-Fi genre — genre-appropriate vocabulary | ✅ |
| T5 | Tone changed mid-story — AI adapts | ✅ |
| T6 | Ollama killed — specific error, no crash | ✅ |
| T7 | Exported .docx contains AI-generated text | ✅ |

Classifier test suite (Milestone 3): **22/22 inputs classified correctly**

---

## 🛣️ Roadmap

- [ ] SQLite FTS5 indexed full-text search (replace LIKE scan)
- [ ] Stricter classifier default — require ≥1 story keyword
- [ ] Cloud deployment (Streamlit Community Cloud)
- [ ] Multi-model support (OpenAI, Claude, Mistral) via env var
- [ ] Character dialogue auto-tagging for export formatting
- [ ] Collaborative mode (shared story sessions)

---

## 🏫 About

Built by **Ramya Jayaram** as part of the **Infosys Springboard Virtual Internship 2026**.

The project was developed across three structured milestones — UI architecture, AI backend integration, and narrative intelligence — followed by a self-initiated security audit and feature expansion.

**Tech stack:** Python · Streamlit · Ollama · Llama 3.2 · SQLite · bcrypt · python-docx · Docker

---

## 📄 License

MIT — free to use, modify, and distribute with attribution.
