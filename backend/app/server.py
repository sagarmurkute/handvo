"""FastAPI Backend Server and WebSocket Vision Streamer for HANDVO."""

import asyncio
from contextlib import asynccontextmanager
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import cv2
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.communication.emergency_model import EmergencyManager
from app.communication.prediction import SmartPredictionEngine
from app.communication.speech import SpeechEngine
from app.database.database import Database
from app.database.models import EmergencyAction, UserProfile
from app.database.profile_repository import ProfileRepository
from app.gestures.cursor import HandCursorManager
from app.gestures.dwell import DwellSelector
from app.gestures.pinch import PinchDetector
from app.vision.camera import Camera
from app.vision.hand_detector import HandDetector

FRONTEND_DIR = Path(__file__).resolve().parent.parent.parent / "frontend"


class ServerState:
    def __init__(self):
        self.db = Database()
        self.repo = ProfileRepository(self.db)
        self.speech_engine = SpeechEngine()
        self.prediction_engine = SmartPredictionEngine()
        self.emergency_mgr = EmergencyManager(repository=self.repo, speech_engine=self.speech_engine)

        self.camera = Camera(device_index=0)
        self.hand_detector = HandDetector()
        self.cursor_manager = HandCursorManager()
        self.pinch_detector = PinchDetector()
        self.is_camera_running = False


state = ServerState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown
    if state.camera.is_opened:
        state.camera.release()
    state.hand_detector.close()
    state.speech_engine.shutdown()


app = FastAPI(title="HANDVO Backend API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------------------------------------
# REST Request/Response Models
# -------------------------------------------------------------
class SpeakRequest(BaseModel):
    text: str
    interrupt: bool = False


class LearnRequest(BaseModel):
    prev_sentence: str
    selected_token: str
    category_id: str = "common"


class ProfileCreateRequest(BaseModel):
    name: str


class DuplicateRequest(BaseModel):
    new_name: str


# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@app.get("/api/profiles")
def get_profiles():
    return state.repo.get_all_profiles(include_archived=False)


@app.get("/api/profiles/active")
def get_active_profile():
    return state.repo.get_active_profile()


@app.post("/api/profiles")
def create_profile(req: ProfileCreateRequest):
    new_p = UserProfile(name=req.name)
    return state.repo.create_profile(new_p)


@app.put("/api/profiles/active")
def update_active_profile(profile_data: Dict[str, Any]):
    active = state.repo.get_active_profile()
    for k, v in profile_data.items():
        if hasattr(active, k):
            setattr(active, k, v)
    state.repo.save_profile(active)
    state.speech_engine.set_rate(active.tts_rate)
    state.speech_engine.set_volume(active.tts_volume)
    if active.voice_id:
        state.speech_engine.set_voice(active.voice_id)
    return active


@app.post("/api/profiles/{profile_id}/activate")
def activate_profile(profile_id: int):
    p = state.repo.activate_profile(profile_id)
    if not p:
        raise HTTPException(status_code=404, detail="Profile not found")
    return p


@app.post("/api/profiles/{profile_id}/duplicate")
def duplicate_profile(profile_id: int, req: DuplicateRequest):
    cloned = state.repo.duplicate_profile(profile_id, req.new_name)
    if not cloned:
        raise HTTPException(status_code=404, detail="Profile not found")
    return cloned


@app.get("/api/profiles/active/export")
def export_active_profile():
    active = state.repo.get_active_profile()
    return json.loads(state.repo.export_profile_json(active.id))


@app.post("/api/profiles/import")
def import_profile(data: Dict[str, Any]):
    json_str = json.dumps(data)
    return state.repo.import_profile_json(json_str)


@app.get("/api/emergency/actions")
def get_emergency_actions():
    actions = state.emergency_mgr.load_actions(enabled_only=True)
    return {"actions": [a.__dict__ for a in actions]}


@app.post("/api/speech/speak")
def speak_text(req: SpeakRequest):
    state.speech_engine.speak(req.text, interrupt=req.interrupt)
    return {"status": "ok", "spoken": req.text}


@app.get("/api/speech/voices")
def get_voices():
    voices = state.speech_engine.get_available_voices()
    return {"voices": [v.__dict__ for v in voices]}


@app.get("/api/predictions")
def get_predictions(sentence: str = "", category: str = "common", limit: int = 5):
    active = state.repo.get_active_profile()
    candidates = state.prediction_engine.get_predictions(
        current_sentence=sentence,
        active_category_id=category,
        limit=limit,
        profile_id=active.id or 1,
    )
    return {
        "predictions": [
            {"text": c.text, "label": c.label, "accent_color": c.accent_color}
            for c in candidates
        ]
    }


@app.post("/api/predictions/learn")
def learn_prediction(req: LearnRequest):
    active = state.repo.get_active_profile()
    state.prediction_engine.learn_selection(
        prev_sentence=req.prev_sentence,
        selected_phrase=req.selected_token,
        category_id=req.category_id,
        profile_id=active.id or 1,
    )
    return {"status": "learned"}


# -------------------------------------------------------------
# WebSocket Vision & Gesture Streaming
# -------------------------------------------------------------
@app.websocket("/ws/vision")
async def websocket_vision_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Automatically start camera on client connection
    if not state.camera.is_opened:
        state.is_camera_running = state.camera.open()

    try:
        while True:
            # Check for client commands with a non-blocking timeout
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=0.033)
                cmd_data = json.loads(msg)
                cmd = cmd_data.get("command")
                if cmd == "START_CAMERA" and not state.camera.is_opened:
                    state.is_camera_running = state.camera.open()
                elif cmd == "STOP_CAMERA" and state.camera.is_opened:
                    state.camera.release()
                    state.is_camera_running = False
            except asyncio.TimeoutError:
                pass

            if not state.is_camera_running or not state.camera.is_opened:
                packet = {
                    "camera_active": False,
                    "tracking_valid": False,
                    "cursor_x": 0,
                    "cursor_y": 0,
                    "is_pinched": False,
                }
                await websocket.send_text(json.dumps(packet))
                await asyncio.sleep(0.1)
                continue

            success, frame = state.camera.read_frame()
            if not success or frame is None:
                await asyncio.sleep(0.033)
                continue

            h, w = frame.shape[:2]
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            hands = state.hand_detector.detect(rgb)

            primary = hands[0] if len(hands) > 0 else None
            landmarks_list = []

            if primary and primary.is_valid:
                # 1920x1080 normalized mapping space
                cursor_pos = state.cursor_manager.update(primary, 1920, 1080)
                pinch_res = state.pinch_detector.detect(primary)

                landmarks_list = [{"x": pt.x, "y": pt.y, "z": pt.z} for pt in primary.landmarks]

                packet = {
                    "camera_active": True,
                    "tracking_valid": cursor_pos.is_valid,
                    "norm_x": float(cursor_pos.pixel_x) / 1920.0,
                    "norm_y": float(cursor_pos.pixel_y) / 1080.0,
                    "raw_x": cursor_pos.pixel_x,
                    "raw_y": cursor_pos.pixel_y,
                    "is_pinched": pinch_res.is_pinched,
                    "pinch_distance": pinch_res.distance,
                    "handedness": primary.handedness,
                    "landmarks": landmarks_list,
                }
            else:
                cursor_pos = state.cursor_manager.update(None, 1920, 1080)
                packet = {
                    "camera_active": True,
                    "tracking_valid": False,
                    "norm_x": 0.5,
                    "norm_y": 0.5,
                    "is_pinched": False,
                    "landmarks": [],
                }

            await websocket.send_text(json.dumps(packet))
            await asyncio.sleep(0.01)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print("WebSocket vision exception:", e)


# -------------------------------------------------------------
# Static Frontend Mount
# -------------------------------------------------------------
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
