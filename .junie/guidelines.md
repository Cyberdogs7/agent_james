# Project Guidelines

## Testing Information
- **Local tests will not work for this application.**
- Do not waste tokens creating tests or trying to run them.
- Verification should be done manually or through other means specified by the user.

## Architecture Overview
The project is a multimodal AI assistant (A.D.A V2) consisting of:
- **Frontend**: Electron + React + Three.js + MediaPipe Gestures.
- **Backend**: Python 3.11 + FastAPI + Socket.IO.
- **Key Components**:
    - `ada.py`: Gemini Live API integration.
    - `web_agent.py`: Playwright-based browser automation.
    - `cad_agent.py`: CAD generation using `build123d`.
    - `printer_agent.py`: 3D printing integration (OrcaSlicer + Moonraker/OctoPrint).
    - `kasa_agent.py`: Smart home control (TP-Link Kasa).
    - `authenticator.py`: Face authentication using MediaPipe.
    - `project_manager.py`: Persistent project context management.

## Key Technologies
- **AI/ML**: Google Gemini 2.5 Native Audio, MediaPipe (Hand Tracking, Face Landmarker).
- **Frontend**: Electron, React, Three.js, Tailwind CSS, Vite.
- **Backend**: Python, FastAPI, Socket.IO, Playwright, build123d.
- **Communication**: Socket.IO for real-time frontend-backend communication.

## Development Notes
- The application uses a "Minority Report" style UI with gesture controls.
- It supports real-time voice interaction with interrupt handling.
- 3D models are generated as STL files and can be viewed in the frontend using Three.js or sent to a 3D printer.
- Persistent memory is managed via file-based JSON storage.
