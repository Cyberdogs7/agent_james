# Agent James - Advanced AI Assistant

![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue?logo=python)
![React](https://img.shields.io/badge/React-18.2-61DAFB?logo=react)
![Electron](https://img.shields.io/badge/Electron-28-47848F?logo=electron)
![LLM](https://img.shields.io/badge/LLM-OpenRouter%20%7C%20LM%20Studio%20%7C%20Ollama-green)
![License](https://img.shields.io/badge/License-MIT-green)

> **Agent James**

Agent James is a sophisticated AI assistant designed for multimodal interaction. It combines hybrid LLMs (OpenRouter / LM Studio / Ollama) with local/hybrid voice (STT→LLM→TTS), computer vision, gesture control, and 3D CAD generation in an Electron desktop application.

---

## 🌟 Capabilities at a Glance

| Feature | Description | Technology |
|---------|-------------|------------|
| **🗣️ Hybrid Voice** | Text chat + optional STT/TTS (Kokoro / ElevenLabs) | STT→LLM→TTS pipeline |
| **🧊 Parametric CAD** | Editable 3D model generation from voice prompts | `build123d` → STL |
| **🖨️ 3D Printing** | Slicing and wireless print job submission | OrcaSlicer + Moonraker/OctoPrint |
| **🖐️ Minority Report UI** | Gesture-controlled window manipulation | MediaPipe Hand Tracking |
| **👁️ Face Authentication** | Secure local biometric login | MediaPipe Face Landmarker |
| **🌐 Web Agent** | Autonomous browser automation | Playwright + Chromium |
| **🏠 Smart Home** | Voice control for TP-Link Kasa devices | `python-kasa` |
| **📁 Project Memory** | Persistent context across sessions | File-based JSON storage |

### 🖐️ Gesture Control Details

Agent James' "Minority Report" interface uses your webcam to detect hand gestures:

| Gesture | Action |
|---------|--------|
| 🤏 **Pinch** | Confirm action / click |
| ✋ **Open Palm** | Release the window |
| ✊ **Close Fist** | "Select" and grab a UI window to drag it |

> **Tip**: Enable the video feed window to see the hand tracking overlay.

---

## 🏗️ Architecture Overview

```mermaid
graph TB
    subgraph Frontend ["Frontend (Electron + React)"]
        UI[React UI]
        THREE[Three.js 3D Viewer]
        GESTURE[MediaPipe Gestures]
        SOCKET_C[Socket.IO Client]
    end
    
    subgraph Backend ["Backend (Python 3.11 + FastAPI)"]
        SERVER[server.py<br/>Socket.IO Server]
        JAMES[agent_james.py<br/>Hybrid LLM + voice pipeline]
        WEB[web_agent.py<br/>Playwright Browser]
        CAD[cad_agent.py<br/>CAD + build123d]
        PRINTER[printer_agent.py<br/>3D Printing + OrcaSlicer]
        KASA[kasa_agent.py<br/>Smart Home]
        AUTH[authenticator.py<br/>MediaPipe Face Auth]
        PM[project_manager.py<br/>Project Context]
    end
    
    UI --> SOCKET_C
    SOCKET_C <--> SERVER
    SERVER --> JAMES
    JAMES --> WEB
    JAMES --> CAD
    JAMES --> KASA
    SERVER --> AUTH
    SERVER --> PM
    SERVER --> PRINTER
    CAD -->|STL file| THREE
    CAD -->|STL file| PRINTER
```

---

## ⚡ TL;DR Quick Start (Experienced Developers)

### Dockerized Execution

You can build and run Agent James using Docker:

```bash
# Build the Docker image
docker compose build

# Run the Docker container
docker compose up
```

### Local Setup

<details>
<summary>Click to expand quick setup commands</summary>

```bash
# 1. Clone and enter
git clone https://github.com/Cyberdogs7/agent_james.git && cd agent_james

# 2. Create Python environment (Python 3.11)
conda create -n agent_james python=3.11 -y && conda activate agent_james
brew install portaudio  # macOS only (for PyAudio)
pip install -r requirements.txt
playwright install chromium

# 3. Setup frontend
npm install

# 4. Create .env file (see .env.example for hybrid LLM + voice options)
echo "OPENROUTER_API_KEY=your_key_here" > .env

# 5. Run!
conda activate agent_james && npm run dev
```

</details>

---

## 🛠️ Installation Requirements

### 🆕 Absolute Beginner Setup (Start Here)
If you have never coded before, follow these steps first!

**Step 1: Install Visual Studio Code (The Editor)**
- Download and install [VS Code](https://code.visualstudio.com/). This is where you will write code and run commands.

**Step 2: Install Anaconda (The Manager)**
- Download [Miniconda](https://docs.conda.io/en/latest/miniconda.html) (a lightweight version of Anaconda).
- This tool allows us to create isolated "playgrounds" (environments) for our code so different projects don't break each other.
- **Windows Users**: During install, check "Add Anaconda to my PATH environment variable" (even if it says not recommended, it makes things easier for beginners).

**Step 3: Install Git (The Downloader)**
- **Windows**: Download [Git for Windows](https://git-scm.com/download/win).
- **Mac**: Open the "Terminal" app (Cmd+Space, type Terminal) and type `git`. If not installed, it will ask to install developer tools—say yes.

**Step 4: Get the Code**
1. Open your terminal (or Command Prompt on Windows).
2. Type this command and hit Enter:
   ```bash
   git clone https://github.com/Cyberdogs7/agent_james.git
   ```
3. This creates a folder named `agent_james`.

**Step 5: Open in VS Code**
1. Open VS Code.
2. Go to **File > Open Folder**.
3. Select the `agent_james` folder you just downloaded.
4. Open the internal terminal: Press `Ctrl + ~` (tilde) or go to **Terminal > New Terminal**.

---

### ⚠️ Technical Prerequisites
Once you have the basics above, continue here.

### 1. System Dependencies

**MacOS:**
```bash
# Audio Input/Output support (PyAudio)
brew install portaudio
```

**Windows:**
- No additional system dependencies required!

### 2. Python Environment
Create a single Python 3.11 environment:

```bash
conda create -n agent_james python=3.11
conda activate agent_james

# Install all dependencies
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 3. Frontend Setup
Requires **Node.js 18+** and **npm**. Download from [nodejs.org](https://nodejs.org/) if not installed.

```bash
# Verify Node is installed
node --version  # Should show v18.x or higher

# Install frontend dependencies
npm install
```

### 4. 🔐 Face Authentication Setup
To use the secure voice features, Agent James needs to know what you look like.

1. Take a clear photo of your face (or use an existing one).
2. Rename the file to `reference.jpg`.
3. Drag and drop this file into the `agent_james/backend` folder.
4. (Optional) You can toggle this feature on/off in `settings.json` by changing `"face_auth_enabled": true/false`.

---

## ⚙️ Configuration (`settings.json`)

The system creates a `settings.json` file on first run. You can modify this to change behavior:

| Key | Type | Description |
| :--- | :--- | :--- |
| `face_auth_enabled` | `bool` | If `true`, blocks all AI interaction until your face is recognized via the camera. |
| `tool_permissions` | `obj` | Controls manual approval for specific tools. |
| `tool_permissions.generate_cad` | `bool` | If `true`, requires you to click "Confirm" on the UI before generating CAD. |
| `tool_permissions.run_web_agent` | `bool` | If `true`, requires confirmation before opening the browser agent. |
| `tool_permissions.write_file` | `bool` | **Critical**: Requires confirmation before the AI writes code/files to disk. |

---

## 🔧 Custom Server Port

By default, the backend server runs on port **8180**. You can customize this if you have a conflict.

1. Open your `.env` file.
2. Add the following lines:
   ```env
   # Change this to your desired port (e.g., 9000)
   SERVER_PORT=9000
   ```
4. Restart the application for changes to take effect.

---

### 5. 🖨️ 3D Printer Setup
Agent James can slice STL files and send them directly to your 3D printer.

**Supported Hardware:**
- **Klipper/Moonraker** (Creality K1, Voron, etc.)
- **OctoPrint** instances
- **PrusaLink** (Experimental)

**Step 1: Install Slicer**
Agent James uses **OrcaSlicer** (recommended) or PrusaSlicer to generate G-code.
1. Download and install [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer).
2. Run it once to ensure profiles are created.
3. Agent James automatically detects the installation path.

**Step 2: Connect Printer**
1. Ensure your printer and computer are on the **same Wi-Fi network**.
2. Open the **Printer Window** in Agent James (Cube icon).
3. Agent James automatically scans for printers using mDNS.
4. **Manual Connection**: If your printer isn't found, use the "Add Printer" button and enter the IP address (e.g., `192.168.1.50`).

---

### 6. 🔑 Hybrid LLM + Voice Setup (Gemini removed)
Agent James uses OpenRouter (cloud) or LM Studio / Ollama (local) for intelligence, plus local/hybrid STT→LLM→TTS for voice.

1. Copy `.env.example` to `.env` in the `agent_james` folder (same level as `README.md`).
2. Cloud (recommended): set `OPENROUTER_API_KEY` (+ optional `OPENROUTER_MODEL`). Get a key at https://openrouter.ai/keys.
3. Local fallback: run LM Studio (`http://localhost:1234/v1`) or Ollama (`http://localhost:11434`) — no key needed.
4. Voice (optional): leave `JAMES_STT_BACKEND=none` for text chat, or set `faster-whisper` for local STT; set `JAMES_TTS_BACKEND=auto` (ElevenLabs → Kokoro → Piper → none).

> **Note**: Keep keys private! Never commit your `.env` file to Git.

---

## 🚀 Running Agent James

You have two options to run the app. Ensure your `agent_james` environment is active!

### Option 1: The "Easy" Way (Single Terminal)
The app is smart enough to start the backend for you.
1. Open your terminal in the `agent_james` folder.
2. Activate your environment: `conda activate agent_james`
3. Run:
   ```bash
   npm run dev
   ```
4. The backend will start automatically in the background.

### Option 2: The "Developer" Way (Two Terminals)
Use this if you want to see the Python logs (recommended for debugging).

**Terminal 1 (Backend):**
```bash
conda activate agent_james
python backend/server.py
```

**Terminal 2 (Frontend):**
```bash
# Environment doesn't matter here, but keep it simple
npm run dev
```

---

## ✅ First Flight Checklist (Things to Test)

1. **Voice Check**: Say "Hello James". He should respond.
2. **Vision Check**: Look at the camera. If Face Auth is on, the lock screen should unlock.
3. **CAD Check**: Open the CAD window and say "Create a cube". Watch the logs.
4. **Web Check**: Open the Browser window and say "Go to Google".
5. **Smart Home**: If you have Kasa devices, say "Turn on the lights".

---

## ▶️ Commands & Tools Reference

### 🗣️ Voice Commands
- "Switch project to [Name]"
- "Create a new project called [Name]"
- "Turn on the [Room] light"
- "Make the light [Color]"
- "Pause audio" / "Stop audio"

### 🧊 3D CAD
- **Prompt**: "Create a 3D model of a hex bolt."
- **Iterate**: "Make the head thinner." (Requires previous context)
- **Files**: Saves to `projects/[ProjectName]/output.stl`.

### 🌐 Web Agent
- **Prompt**: "Go to Amazon and find a USB-C cable under $10."
- **Note**: The agent will auto-scroll, click, and type. Do not interfere with the browser window while it runs.

### 🖨️ Printing & Slicing
- **Auto-Discovery**: Agent James automatically finds printers on your network.
- **Slicing**: Click "Slice & Print" on any generated 3D model.
- **Profiles**: Agent James intelligently selects the correct OrcaSlicer profile based on your printer's name (e.g., "Creality K1").

---

## ❓ Troubleshooting FAQ

### Camera not working / Permission denied (Mac)
**Symptoms**: Error about camera access, or video feed shows black.

**Solution**:
1. Go to **System Preferences > Privacy & Security > Camera**.
2. Ensure your terminal app (e.g., Terminal, iTerm, VS Code) has camera access enabled.
3. Restart the app after granting permission.

---

### `OPENROUTER_API_KEY` / LLM not configured
**Symptoms**: Chat replies "LLM unavailable" or background healing stays silent.

**Solution**:
1. Make sure your `.env` file is in the root `agent_james` folder (not inside `backend/`).
2. Set `OPENROUTER_API_KEY` (cloud) or run LM Studio / Ollama locally. Format: `OPENROUTER_API_KEY=your_key` (no quotes, no spaces).
3. Restart the backend after editing the file.

---

### Voice realtime disabled
**Symptoms**: Notice "Voice realtime (Gemini Live) is disabled".

**Solution**:
Gemini Live was removed with `google-genai`. Text chat works via hybrid LLM. For voice, configure `JAMES_STT_BACKEND` (faster-whisper) and `JAMES_TTS_BACKEND` (auto → ElevenLabs/Kokoro/Piper) — see `.env.example` and `backend/voice_pipeline.py`.

---

## 📸 What It Looks Like

*Coming soon! Screenshots and demo videos will be added here.*

---

## 📂 Project Structure

```
agent_james/
├── backend/                    # Python server & AI logic
│   ├── agent_james.py          # Hybrid LLM + voice pipeline (AgentJames class)
│   ├── server.py               # FastAPI + Socket.IO server
│   ├── fleet_manager.py        # Fleet/orchestration + OpenCode tracking
│   ├── automation_engine.py    # Cron/schedules + monitors + self-heal
│   ├── memory_manager.py       # Vector + FTS5 memory
│   ├── cad_agent.py            # CAD generation orchestrator (currently disabled)
│   ├── printer_agent.py        # 3D printer discovery & slicing
│   ├── web_agent.py            # Playwright browser automation
│   ├── kasa_agent.py           # TP-Link smart home control
│   ├── authenticator.py        # MediaPipe face auth logic
│   ├── project_manager.py      # Project context management
│   ├── tools.py                # Tool definitions (OpenAI-compatible)
│   └── reference.jpg           # Your face photo (add this!)
├── src/                        # React frontend
│   ├── App.jsx                 # Main application component (~2248 lines)
│   ├── components/             # UI components (38 files: Chat, Fleet, WarRoom, Printer, Kasa, etc.)
│   └── index.css               # Global styles
├── electron/                   # Electron main process
│   └── main.js                 # Window & IPC setup
├── projects/                   # User project data (auto-created)
├── .env                        # API keys (create this!)
├── requirements.txt            # Python dependencies
├── package.json                # Node.js dependencies
└── README.md                   # You are here!
```

---

## ⚠️ Known Limitations

| Limitation | Details |
|------------|---------|
| **macOS & Windows** | Tested on macOS 14+ and Windows 10/11. Linux is untested. |
| **Camera Required** | Face auth and gesture control need a working webcam. |
| **LLM Quota** | Cloud LLM rate limits apply; heavy CAD iteration may hit limits — use local LM Studio/Ollama to avoid. |
| **Network Dependency** | Cloud LLMs need internet; fully offline mode needs local LLM + local STT/TTS. |
| **Voice Realtime** | Gemini Live removed; realtime STT→LLM→TTS streams in Phase 2 (text chat works now). |
| **Single User** | Face auth recognizes one person (the `reference.jpg`). |

---

## 🤝 Contributing

Contributions are welcome! Here's how:

1. **Fork** the repository.
2. **Create a branch**: `git checkout -b feature/amazing-feature`
3. **Commit** your changes: `git commit -m 'Add amazing feature'`
4. **Push** to the branch: `git push origin feature/amazing-feature`
5. **Open a Pull Request** with a clear description.

### Development Tips

- Run the backend separately (`python backend/server.py`) to see Python logs.
- Use `npm run dev` without Electron during frontend development (faster reload).
- The `projects/` folder contains user data—don't commit it to Git.

---

## 🔒 Security Considerations

| Aspect | Implementation |
|--------|----------------|
| **API Keys** | Stored in `.env`, never committed to Git. |
| **Face Data** | Processed locally, never uploaded. |
| **Tool Confirmations** | Write/CAD/Web actions can require user approval. |
| **No Cloud Storage** | All project data stays on your machine. |

> [!WARNING]
> Never share your `.env` file or `reference.jpg`. These contain sensitive credentials and biometric data.

---

## 🙏 Acknowledgments

- **[Kokoro](https://github.com/hexgrad/kokoro)** / **[ElevenLabs](https://elevenlabs.io/)** — Local/hybrid TTS for voice output
- **[faster-whisper](https://github.com/SYSTRAN/faster-whisper)** — Local STT option
- **[build123d](https://github.com/gumyr/build123d)** — Modern parametric CAD library
- **[MediaPipe](https://developers.google.com/mediapipe)** — Hand tracking, gesture recognition, and face authentication
- **[Playwright](https://playwright.dev/)** — Reliable browser automation

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built with 🤖 by Nazir Louis</strong><br>
  <em>Bridging AI, CAD, and Vision in a Single Interface</em>
</p>
