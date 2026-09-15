# HANDVO — Hand-Tracking & Gesture Assistive Communication System (Starter Template)

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12+-38bdf8?style=for-the-badge&logo=python&logoColor=white" alt="Python Version" />
  <img src="https://img.shields.io/badge/GUI-PySide6%20%2F%20Qt6-0284c7?style=for-the-badge&logo=qt&logoColor=white" alt="PySide6 GUI" />
  <img src="https://img.shields.io/badge/Vision-MediaPipe%20Hands%20%26%20OpenCV-10b981?style=for-the-badge&logo=opencv&logoColor=white" alt="Hand Tracking" />
  <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20macOS-8b5cf6?style=for-the-badge" alt="Platform" />
  <img src="https://img.shields.io/badge/Privacy-100%25%20Offline%20%26%20Local-f59e0b?style=for-the-badge" alt="Offline & Private" />
</p>

---

## 🌟 Overview

**HANDVO** is an Assistive and Augmentative Communication (AAC) desktop application blueprint engineered for individuals who can use hand gestures, finger pointing, or subtle hand movements to communicate. 

Using standard consumer webcams, HANDVO tracks 21 3D hand landmarks in real time, converting finger pointing, pinch gestures, and spatial dwelling into accessible communication actions.

*(Note: This is a standalone template project design adapted from the EYEVO architecture).*

---

## ✨ Core Pipeline & Features

### ✋ 1. Hand & Finger Landmark Tracking
* **21 3D Hand Landmarks**: Powered by Google MediaPipe Hand Landmarker.
* **Index Tip Tracking**: Uses Index Finger Tip (Landmark `8`) and MCP joint (Landmark `5`) for high-precision cursor control.
* **Pinch & Air-Click Detection**: Euclidean distance between Thumb Tip (`4`) and Index Tip (`8`) to detect air taps/clicks without dwelling if desired.

### 🖱️ 2. Virtual Hand Cursor
* **Velocity-Adaptive One-Euro Filter**: Silences jitter when holding hand still, with immediate responsiveness during fast hand movements.
* **Non-Intrusive Virtual Cursor**: Operates within the application window without hijacking the OS mouse.

### ⏳ 3. Gesture & Dwell Selection Engine
* **Spatial Dwell**: Point index finger at any target button for 800ms to activate.
* **Air Pinch Trigger**: Alternatively, pinch thumb and index finger together to click instantly.
* **Cooldown Protection**: 600ms debouncing window preventing accidental repeated triggers.

### 💬 4. Accessible Communication Board
* **Category Tabs**: `Common`, `Needs`, `Feelings`, `People`, `Places`, `Actions`.
* **Action Tools**: `🔊 Speak`, `⌫ Delete Last`, `␣ Space`, and `🗑 Clear All`.
* **Spacious UI Layout**: Large, high-contrast target cards with live radial progress feedback.

---

## 📁 Recommended Project Structure

```text
HANDVO/
├── app/
│   ├── __init__.py                  # Package metadata
│   ├── main.py                      # Application entry point
│   ├── config.py                    # Settings (camera index, resolutions)
│   ├── communication/               # Communication Board subsystem
│   │   ├── __init__.py
│   │   └── communication_board.py   # State management, categories, and phrases
│   ├── gestures/                    # Hand gesture recognition & cursor
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
├── requirements.txt                 # Dependencies
└── README.md                        # Documentation
```

---

## 💻 Sample Code: Hand Landmark Extractor

```python
"""Sample hand tracking module for HANDVO using MediaPipe Tasks."""

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

class HandDetector:
    INDEX_TIP = 8
    THUMB_TIP = 4
    WRIST = 0

    def __init__(self, model_path: str = "assets/models/hand_landmarker.task"):
        base_options = python.BaseOptions(model_asset_path=model_path)
        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            num_hands=1,
            min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.landmarker = vision.HandLandmarker.create_from_options(options)

    def extract_index_cursor(self, frame_rgb):
        """Returns normalized (x, y) coordinates of the index fingertip."""
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        result = self.landmarker.detect(mp_image)
        if result.hand_landmarks:
            landmarks = result.hand_landmarks[0]
            tip = landmarks[self.INDEX_TIP]
            return True, (tip.x, tip.y)
        return False, (0.5, 0.5)
```

---

## ⚡ Quick Start

1. Install dependencies:
   ```bash
   pip install opencv-python mediapipe PySide6 numpy
   ```
2. Download MediaPipe Hand Landmarker model:
   ```bash
   curl -o assets/models/hand_landmarker.task https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
   ```
3. Run:
   ```bash
   python -m app.main
   ```

---

## 📄 License
MIT License
