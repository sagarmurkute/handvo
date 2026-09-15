# Research Notes & Technical Foundations — HANDVO

## 1. Hand Tracking: MediaPipe Hand Landmarker
- Uses a machine learning pipeline composed of a palm detection model and a hand landmark model predicting 21 3D points in real time.
- Operates at ~30 FPS on standard single-thread x86/ARM CPU without requiring dedicated GPU.

## 2. Jitter Reduction: 1-Euro Filter
- Developed by Géry Casiez et al. (2012), the One-Euro filter uses speed-adaptive cutoff frequencies to solve the trade-off between jitter at low velocities and lag at high velocities.
- Parameters:
  - `min_cutoff = 1.2 Hz` (minimizes trembling when still)
  - `beta = 0.04` (eliminates latency during fast hand swipes)

## 3. Pinch Detection Distance Normalization
- Raw pixel Euclidean distance between Landmark 4 (Thumb tip) and Landmark 8 (Index tip) varies with hand distance from webcam.
- Normalizing by palm scale (distance between Wrist `0` and Middle MCP `9`) makes pinch detection robust across varying distances from 30cm to 1.5m.
