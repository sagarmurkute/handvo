# 📌 HANDVO Feature Roadmap & Bookmarked Capabilities

This document tracks completed milestones and bookmarks upcoming features ready for implementation.

---

## 🟢 Completed Milestones
- [x] **MediaPipe 21-Point 3D Hand Tracking**: Real-time 60 FPS landmark extraction.
- [x] **One-Euro Velocity-Adaptive Cursor Smoothing**: Zero jitter with high responsiveness.
- [x] **Pinch Gesture Detection**: Contact hysteresis between thumb tip and index fingertip.
- [x] **Gaze / Hand Dwell Selection Engine**: Configurable dwell timing with radial SVG progress animation.
- [x] **SQLite Offline Persistence**: Complete profile, prediction frequencies, and emergency action storage.
- [x] **Smart Next-Phrase Prediction Engine**: Context-aware, frequency-ranked next word chips.
- [x] **Multilingual AAC Communication Board**: English, Hindi (हिंदी), and Marathi (मराठी) support across 6 categories.
- [x] **High-Priority Emergency Mode**: Audio cue chimes with speech synthesis interrupt.
- [x] **Caregiver Profile System**: Profile cloning, switching, JSON export/import.
- [x] **Pure HTML5/CSS3/JavaScript Frontend**: Modern glassmorphic AAC dashboard.
- [x] **Unified Frontend–Backend Communication Bridge (`HANDVOBridge`)**: Standardized API contract for WebSocket, REST, and Qt WebChannel.
- [x] **Live Video Stream & Skeleton Bones**: Real-time camera canvas with glowing anatomical skeleton connections.

---

## 🔖 Bookmarked Features for Next Sessions

### 1. On-Screen AAC Virtual Keyboard (Spelling Mode)
- **Goal**: Enable users to spell arbitrary words, names, and sentences beyond predefined phrase cards.
- **Specifications**:
  - Full QWERTY / ABC layout with large dwell-accessible keys.
  - Number pad and common punctuation drawer.
  - Autocomplete word suggestions dynamically queried from the prediction engine.
  - Shift / Caps-Lock and space/backspace quick keys.

### 2. Caregiver Phrase & Category Builder
- **Goal**: Allow caregivers to customize the AAC communication board directly from the web interface.
- **Specifications**:
  - Add, edit, reorder, and remove custom phrases within categories.
  - Create new custom categories with custom icons and color schemes.
  - Drag-and-drop or dwell-reordering of cards.
  - Live persistence into SQLite `custom_phrases` table.

### 3. Interactive 9-Point Range & Calibration Remapping
- **Goal**: Maximize cursor reach for users with limited arm or hand mobility.
- **Specifications**:
  - 9-point visual target sampling across screen quadrants.
  - Polynomial / affine remapping matrix applied live to `(norm_x, norm_y)`.
  - Quality score metrics (Neutral centroid, active range, pinch precision).
  - Profile-isolated calibration storage in database.

### 4. Quick Action Bar & Dwell Pause / Sleep Mode
- **Goal**: Allow users to comfortably read the screen or rest without accidental clicks.
- **Specifications**:
  - Floating pause/resume toggle with eye-catching status indicator.
  - Sleep timer when hand is inactive or lowered out of view.
  - Audio alert when re-entering tracking field.
