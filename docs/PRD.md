# Product Requirements Document (PRD) — HANDVO

## 1. Executive Summary
**HANDVO** is an open-source, 100% offline, privacy-first Assistive and Augmentative Communication (AAC) system engineered for individuals with motor or vocal impairments. Using standard consumer webcams, HANDVO tracks 21 3D hand landmarks in real time, converting finger pointing, pinch gestures, and spatial dwelling into accessible speech.

## 2. Target Users & Needs
- **Users with ALS, Motor Neurone Disease, Stroke, or Cerebral Palsy** who retain hand/finger mobility.
- **Speech Impaired Individuals** needing fast, non-verbal vocalization in multiple languages (English, Hindi, Marathi).
- **Caregivers and Medical Staff** seeking low-cost, plug-and-play communication setups without specialized hardware.

## 3. Core Requirements & Interactions
- **Vision Pipeline**: Real-time 21 3D hand landmark tracking via MediaPipe at ~30 FPS on standard CPUs.
- **Pointing & Cursor**: Index fingertip position mapped to screen coordinates with One-Euro velocity-adaptive jitter filtering.
- **Activation Modes**:
  - *Spatial Dwell*: 800ms dwell with visual progress indicator.
  - *Air Pinch Trigger*: Instant click trigger via thumb-to-index pinch contact.
- **Communication Board**: Categorized grids, instant message composition, backspace, clear, and local TTS synthesis.
- **Localization**: Multi-lingual offline phrase sets (English, Hindi, Marathi).

## 4. Non-Functional Requirements
- **100% Local Execution**: No external cloud API calls or network requirements.
- **Low Latency**: Under 40ms end-to-end processing pipeline latency.
- **Cross-Platform**: Windows, macOS, and Linux compatibility via Qt6 / PySide6.
