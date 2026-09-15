/**
 * Main Application Bootstrapper and View Controller for HANDVO.
 */

class ApplicationController {
  constructor() {
    this.currentView = 'comm';

    // UI elements
    this.tabComm = document.getElementById('tab-comm');
    this.tabVision = document.getElementById('tab-vision');
    this.tabEmergency = document.getElementById('tab-emergency');
    this.btnCamToggle = document.getElementById('btn-toggle-camera');
    this.lblCamBtn = document.getElementById('lbl-cam-btn');

    this.badgeCam = document.getElementById('badge-camera');
    this.txtCam = document.getElementById('txt-cam-status');
    this.badgeTrack = document.getElementById('badge-tracking');
    this.txtTrack = document.getElementById('txt-track-status');
    this.badgePinch = document.getElementById('badge-pinch');
    this.txtPinch = document.getElementById('txt-pinch-status');

    this.canvas = document.getElementById('camera-canvas');
    this.canvasCtx = this.canvas ? this.canvas.getContext('2d') : null;
    this.visionOverlay = document.getElementById('vision-overlay-msg');

    this.valX = document.getElementById('val-x');
    this.valY = document.getElementById('val-y');
    this.valPinch = document.getElementById('val-pinch');
    this.valHand = document.getElementById('val-hand');

    this._bindNavigation();
    this._bindVisionStreaming();
  }

  _bindNavigation() {
    this.tabComm?.addEventListener('click', () => this.switchView('comm'));
    this.tabVision?.addEventListener('click', () => this.switchView('vision'));
    this.tabEmergency?.addEventListener('click', () => this.switchView('emergency'));

    this.btnCamToggle?.addEventListener('click', () => {
      const isOnline = this.btnCamToggle.classList.contains('active');
      window.VisionWS.sendCommand(isOnline ? 'STOP_CAMERA' : 'START_CAMERA');
    });
  }

  switchView(viewName) {
    this.currentView = viewName;
    document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));

    if (viewName === 'comm') {
      document.getElementById('view-comm')?.classList.add('active');
      this.tabComm?.classList.add('active');
    } else if (viewName === 'vision') {
      document.getElementById('view-vision')?.classList.add('active');
      this.tabVision?.classList.add('active');
    } else if (viewName === 'emergency') {
      document.getElementById('view-emergency')?.classList.add('active');
      this.tabEmergency?.classList.add('active');
    }
  }

  _bindVisionStreaming() {
    window.VisionWS.onStatusChange = (connected) => {
      if (connected) {
        this.txtCam.textContent = 'Camera Ready';
        this.badgeCam.classList.add('active');
      } else {
        this.txtCam.textContent = 'Server Offline';
        this.badgeCam.classList.remove('active');
      }
    };

    window.VisionWS.onFrameData = (packet) => {
      this._handleVisionPacket(packet);
    };

    window.VisionWS.connect();
  }

  _handleVisionPacket(data) {
    // 1. Telemetry and cursor update
    let x = window.innerWidth / 2;
    let y = window.innerHeight / 2;

    if (data.norm_x !== undefined && data.norm_y !== undefined) {
      x = data.norm_x * window.innerWidth;
      y = data.norm_y * window.innerHeight;
    }

    const isValid = !!data.tracking_valid;
    const isPinched = !!data.is_pinched;
    const handedness = data.handedness || 'Right';

    window.CursorEngine.updatePosition(x, y, isValid, isPinched);

    // 2. Status Badges Update
    if (isValid) {
      this.txtTrack.textContent = `${handedness.toUpperCase()} HAND`;
      this.badgeTrack.classList.add('active');
    } else {
      this.txtTrack.textContent = 'NO HAND DETECTED';
      this.badgeTrack.classList.remove('active');
    }

    if (isPinched) {
      this.txtPinch.textContent = 'PINCH ACTIVE';
      this.badgePinch.classList.add('active');
    } else {
      this.txtPinch.textContent = 'PINCH IDLE';
      this.badgePinch.classList.remove('active');
    }

    // 3. Update Camera Toggle button state
    if (data.camera_active) {
      this.btnCamToggle?.classList.add('active');
      if (this.lblCamBtn) this.lblCamBtn.textContent = 'Stop Camera';
      this.txtCam.textContent = 'Camera Active';
      if (this.visionOverlay) this.visionOverlay.style.display = 'none';
    } else {
      this.btnCamToggle?.classList.remove('active');
      if (this.lblCamBtn) this.lblCamBtn.textContent = 'Start Camera';
      this.txtCam.textContent = 'Camera Ready';
      if (this.visionOverlay) this.visionOverlay.style.display = 'block';
    }

    // 4. Update Telemetry Card
    if (this.valX) this.valX.textContent = Math.round(x);
    if (this.valY) this.valY.textContent = Math.round(y);
    if (this.valPinch) this.valPinch.textContent = data.pinch_distance ? data.pinch_distance.toFixed(3) : '0.000';
    if (this.valHand) this.valHand.textContent = handedness;

    // 5. Draw Skeleton & Video on Canvas if on Vision tab
    if (this.currentView === 'vision' && this.canvasCtx) {
      this._drawSkeleton(data.landmarks || [], data.image);
    }
  }

  _drawSkeleton(landmarks, imageSrc) {
    if (!this.canvasCtx || !this.canvas) return;
    const ctx = this.canvasCtx;
    const w = this.canvas.width;
    const h = this.canvas.height;

    if (imageSrc) {
      if (!this._cachedImg) this._cachedImg = new Image();
      this._cachedImg.onload = () => {
        ctx.drawImage(this._cachedImg, 0, 0, w, h);
        this._renderLandmarksOverlay(ctx, w, h, landmarks);
      };
      this._cachedImg.src = imageSrc;
    } else {
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, w, h);
      this._renderLandmarksOverlay(ctx, w, h, landmarks);
    }
  }

  _renderLandmarksOverlay(ctx, w, h, landmarks) {
    if (!landmarks || landmarks.length === 0) return;

    // MediaPipe Hand Connection Pairs
    const connections = [
      [0, 1], [1, 2], [2, 3], [3, 4],       // Thumb
      [0, 5], [5, 6], [6, 7], [7, 8],       // Index
      [5, 9], [9, 10], [10, 11], [11, 12],  // Middle
      [9, 13], [13, 14], [14, 15], [15, 16],// Ring
      [13, 17], [17, 18], [18, 19], [19, 20],// Pinky
      [0, 17]                               // Palm base
    ];

    // Draw skeleton bone connection lines
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.75)';
    ctx.lineWidth = 3;
    connections.forEach(([i, j]) => {
      if (landmarks[i] && landmarks[j]) {
        ctx.beginPath();
        ctx.moveTo(landmarks[i].x * w, landmarks[i].y * h);
        ctx.lineTo(landmarks[j].x * w, landmarks[j].y * h);
        ctx.stroke();
      }
    });

    // Draw landmark joints
    landmarks.forEach((pt, idx) => {
      const px = pt.x * w;
      const py = pt.y * h;
      ctx.beginPath();
      if ([4, 8, 12, 16, 20].includes(idx)) {
        ctx.fillStyle = '#f59e0b';
        ctx.arc(px, py, 6, 0, Math.PI * 2);
      } else {
        ctx.fillStyle = '#38bdf8';
        ctx.arc(px, py, 4, 0, Math.PI * 2);
      }
      ctx.fill();
    });
  }
}

// Boot application when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  window.AppController = new ApplicationController();
  window.CommBoard?.renderCategories();
  window.CommBoard?.renderPhraseCards();
  window.PredictionEngine?.updatePredictions('', 'common');
});
