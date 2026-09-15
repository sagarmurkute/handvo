# System Architecture — HANDVO

## Modular Design & Separation of Concerns

```
                  ┌──────────────────────┐
                  │    Camera Capture    │
                  └──────────┬───────────┘
                             │ (BGR Frame)
                             ▼
                  ┌──────────────────────┐
                  │     MediaPipe        │
                  │   Hand Landmarker    │
                  └──────────┬───────────┘
                             │ (21 3D Landmarks)
                             ▼
               ┌────────────────────────────┐
               │    Gesture & Cursor Engine │
               │   • One-Euro Filter        │
               │   • Pinch Distance Metric  │
               │   • Dwell State Machine    │
               └─────────────┬──────────────┘
                             │ (Cursor PX & Events)
                             ▼
               ┌────────────────────────────┐
               │       PySide6 GUI          │
               │   • Communication Grid     │
               │   • Visual Dwell Arc Ring  │
               │   • Floating Cursor Overlay│
               └─────────────┬──────────────┘
                             │ (Action Trigger)
                             ▼
               ┌────────────────────────────┐
               │      Speech Engine         │
               │   • pyttsx3 Local TTS      │
               └────────────────────────────┘
```

## Module Ownership & Boundary Isolation Rules

| Module | Owns | Never Knows About |
|---|---|---|
| **vision** | Hand landmarks & skeletal joint points | UI buttons & Qt widgets |
| **gestures** | Cursor position, pinch distance, dwell timers | Camera capture implementation |
| **communication**| Words, categories, sentence tokens | MediaPipe or CV coordinate math |
| **ui** | Rendering widgets, cards, overlays | CV calculations & landmark parsing |
| **database** | Profiles, preferences, custom phrases | Gesture logic & camera state |
