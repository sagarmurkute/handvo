# Frontend–Backend Communication Layer & Bridge Contract

## 1. Overview
The **HANDVO Communication Layer** establishes a clean, decoupled API contract between the Python backend processing engine and the HTML5/CSS/JavaScript web interface.

Every UI screen (Communication Board, Vision Monitor, Emergency Mode, Settings & Personalization Suite, Caregiver Profiles, Calibration Wizard) interacts with the backend strictly through this standardized bridge.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        HTML5 / CSS / JS Frontend                       │
│  [Comm Board]  [Vision Monitor]  [Emergency]  [Settings]  [Profiles]   │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
                     window.HANDVOBridge (bridge.js)
                                     │
        ┌────────────────────────────┴────────────────────────────┐
        │                                                         │
   [WebSocket /ws/vision]                                    [REST API /api/*]
   (or Qt WebChannel Transport)                              (Async Endpoints)
        │                                                         │
        └────────────────────────────┬────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                          Python Backend Engine                         │
│  [MediaPipe Vision]  [Pinch/Dwell]  [Predictions]  [SQLite]  [TTS]     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Bridge API Contract (`window.HANDVOBridge`)

The JavaScript bridge (`frontend/js/bridge.js`) provides standard event-driven and promise-based APIs.

### 2.1 Events & Payloads

| Event Name | Direction | Payload Schema | Description |
|---|---|---|---|
| `cursor:update` | Backend ➔ Frontend | `{ camera_active, tracking_valid, norm_x, norm_y, is_pinched, pinch_distance, handedness, landmarks }` | Real-time 60fps tracking coordinates and hand skeleton. |
| `camera:state_changed` | Bidirectional | `{ active: boolean }` | Emitted when camera starts or stops. |
| `dwell:progress` | Frontend internal | `{ targetId, progress: 0.0..1.0, isCompleted: boolean, timestamp }` | Dispatched during gaze dwell hover. |
| `dwell:complete` | Frontend internal | `{ targetId, timestamp }` | Fired when dwell threshold (e.g., 0.8s) completes. |
| `aac:phrase_selected` | Frontend ➔ Bridge | `{ phrase: string, category: string, timestamp }` | Word or phrase selected from board. |
| `aac:sentence_updated` | Frontend ➔ Bridge | `{ sentence: string, timestamp }` | Composed sentence bar state. |
| `speech:request` | Frontend ➔ Backend | `{ text: string, interrupt: boolean }` | Dispatches offline speech synthesis. |
| `speech:started` | Backend ➔ Frontend | `{ text: string }` | Notifies when audio playback begins. |
| `prediction:updated` | Backend ➔ Frontend | `{ predictions: Array<{ text, label, accent_color }> }` | Smart prediction chips payload. |
| `settings:saved` | Frontend ➔ Backend | `{ dwell_time, cooldown_time, theme, ui_scale, ... }` | Accessibility settings persistence. |
| `profile:active_changed` | Backend ➔ Frontend | `{ id, name, is_active, ... }` | Profile activation notification. |
| `emergency:triggered` | Frontend ➔ Backend | `{ id, label, speech_text, icon, color }` | Emergency mode activation and voice alert. |

---

## 3. Communication Transports

1. **WebSocket Streaming (`/ws/vision`)**:
   - High-throughput bi-directional streaming for 60fps normalized cursor coordinates `(norm_x, norm_y)`, pinch distance, and 21 MediaPipe 3D joint landmarks.
   - Separate asynchronous `rx_handler` and `tx_handler` coroutines to prevent frame drops or timeouts.

2. **REST Endpoints (`/api/*`)**:
   - `GET /api/profiles`: List all caregiver user profiles.
   - `GET /api/profiles/active`: Retrieve current active profile settings.
   - `PUT /api/profiles/active`: Live-save accessibility preferences.
   - `POST /api/profiles/{id}/activate`: Switch active user profile.
   - `POST /api/profiles/{id}/duplicate`: Clone a profile.
   - `GET /api/profiles/active/export`: Export profile as JSON.
   - `POST /api/profiles/import`: Import profile from JSON backup.
   - `GET /api/predictions`: Query offline smart predictions for current sentence.
   - `POST /api/predictions/learn`: Record phrase frequency to SQLite for adaptive ranking.
   - `POST /api/speech/speak`: Trigger offline TTS via `pyttsx3`.
   - `GET /api/speech/voices`: List available system speech voices.
   - `GET /api/emergency/actions`: List high-priority emergency phrases.

3. **Qt WebChannel Compatibility (`QWebChannel`)**:
   - Automatically detected if running inside an embedded WebEngine view with `window.qt.webChannelTransport`.
   - Bridges directly without needing network ports.

---

## 4. Usage Example

```javascript
// Subscribe to cursor updates
window.HANDVOBridge.on('cursor:update', (data) => {
  console.log("Cursor position:", data.norm_x, data.norm_y);
});

// Trigger speech synthesis
await window.HANDVOBridge.speakText("I need help, please", true);

// Fetch smart predictions
const predictions = await window.HANDVOBridge.getPredictions("I am", "feelings");
```
