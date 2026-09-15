# HANDVO — Hand-Tracking & Gesture Assistive Communication System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-38bdf8?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-0284c7?style=for-the-badge&logo=qt&logoColor=white" alt="PySide6 GUI" />
  <img src="https://img.shields.io/badge/Vision-MediaPipe%20Hands%20%26%20OpenCV-10b981?style=for-the-badge&logo=opencv&logoColor=white" alt="Hand Tracking" />
  <img src="https://img.shields.io/badge/License-MIT-a855f7?style=for-the-badge" alt="MIT License" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-8b5cf6?style=for-the-badge" alt="Platform" />
  <img src="https://img.shields.io/badge/Privacy-100%25%20Offline%20%26%20Local-f59e0b?style=for-the-badge" alt="Offline & Private" />
</p>

---

## 🌟 Overview

**HANDVO** is an Assistive and Augmentative Communication (AAC) desktop application engineered for individuals with speech and motor impairments. Using a standard consumer webcam, HANDVO tracks 21 3D hand landmarks in real time, converting finger pointing, pinch gestures, and spatial dwelling into accessible speech and communication actions.

100% offline, private, and runs locally on standard hardware without requiring specialized eye-tracking or motion-capture sensors.

---

## ✨ Key Features

* ✋ **21 3D Hand Landmark Tracking**: Real-time hand skeletal tracking powered by Google MediaPipe Hand Landmarker.
* 👆 **Index Tip Cursor Control**: Precise pointing using index fingertip coordinates.
* 🎯 **Velocity-Adaptive One-Euro Filter**: Jitter-free stabilization when holding steady with instantaneous responsiveness during motion.
* 🤏 **Air-Pinch Gesture Detection**: Detects pinch contact between thumb and index finger for instantaneous trigger selection.
* ⏳ **Spatial Dwell Selection**: Smooth progressive dwell activation (800ms dwell with 600ms cooldown protection).
* 💬 **Accessible Communication Board**: Categorized phrase cards (*Common, Needs, Feelings, People, Places, Actions*) with offline Text-to-Speech (TTS).
* 🖥️ **Modern PySide6 GUI**: High-contrast, dark-mode accessible user interface with live visual dwell feedback rings.

---

## 📁 Project Structure

```text
HANDVO/
├── app/
│   ├── __init__.py                  # Package metadata
│   ├── main.py                      # Application entry point
│   ├── config.py                    # Settings (camera index, window dimensions)
│   ├── communication/               # AAC phrase & category state manager
│   │   ├── __init__.py
│   │   └── communication_board.py   # State management, categories, and phrases
│   ├── gestures/                    # Hand gesture recognition & cursor smoothing
│   │   ├── __init__.py
│   │   ├── pinch_detector.py        # Thumb-index pinch distance calculation
│   │   └── hand_cursor.py           # Index finger smoothing & window clamping
│   ├── interaction/                 # Dwell & gesture selection subsystem
│   │   ├── __init__.py
│   │   └── dwell_selector.py        # Dwell state machine & hit testing
│   ├── ui/                          # PySide6 graphical user interface
│   │   ├── __init__.py
│   │   ├── main_window.py           # Dashboard & camera view switcher
│   │   ├── communication_widget.py  # Communication Board UI
│   │   ├── gaze_button.py           # Accessible button with dwell arcs
│   │   └── cursor_overlay.py        # Transparent hand cursor overlay
│   └── vision/                      # Computer vision pipeline
│       ├── __init__.py
│       ├── camera.py                # OpenCV camera capture
│       └── hand_detector.py         # MediaPipe Hand Landmarker engine
├── assets/                          # Models and static assets
│   └── models/hand_landmarker.task  # MediaPipe HandLandmarker bundle
├── tests/                           # Unit tests
│   ├── __init__.py
│   ├── test_hand_detection.py
│   ├── test_pinch.py
│   ├── test_dwell_selector.py
│   └── test_communication_board.py
├── pyproject.toml                   # Project metadata and build configuration
├── requirements.txt                 # Dependencies
├── LICENSE                          # MIT License
└── README.md                        # Documentation
```

---

## 🚀 Getting Started

### Prerequisites
* **Python 3.12+**
* Webcam / USB Camera

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/sagarmurkute/handvo.git
   cd handvo
   ```

2. **Set up a virtual environment**:
   ```bash
   # Windows (PowerShell)
   py -3.12 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running HANDVO

```bash
python -m app.main
```

### Running Tests

```bash
pytest tests/ -v
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE) - see the LICENSE file for details.
