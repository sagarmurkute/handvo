/**
 * Virtual Hand Cursor Manager & Pure Dwell Selection Engine in JavaScript.
 */

class HandCursorEngine {
  constructor() {
    this.cursorEl = document.getElementById('virtual-cursor');
    this.ringProgressEl = this.cursorEl ? this.cursorEl.querySelector('.ring-progress') : null;
    this.dotEl = this.cursorEl ? this.cursorEl.querySelector('.cursor-dot') : null;

    this.cursorX = window.innerWidth / 2;
    this.cursorY = window.innerHeight / 2;
    this.isValid = false;
    this.isPinched = false;

    // Dwell engine parameters
    this.dwellTimeSec = 0.80;
    this.cooldownSec = 0.60;
    this.currentTarget = null;
    this.dwellStartTime = 0;
    this.cooldownUntil = 0;
    this.isDwellLocked = false;

    this.circumference = 150.8; // 2 * PI * 24
    this._initMouseFallback();
  }

  _initMouseFallback() {
    // Mouse hover preview fallback for desktop testing
    window.addEventListener('mousemove', (e) => {
      if (!this.isValid) {
        this.updatePosition(e.clientX, e.clientY, true, false);
      }
    });
  }

  updatePosition(x, y, isValid, isPinched = false) {
    this.cursorX = x;
    this.cursorY = y;
    this.isValid = isValid;
    this.isPinched = isPinched;

    if (!this.cursorEl) return;

    if (!isValid) {
      this.cursorEl.classList.add('hidden');
      this._resetDwell();
      return;
    }

    this.cursorEl.classList.remove('hidden');
    this.cursorEl.style.left = `${x}px`;
    this.cursorEl.style.top = `${y}px`;

    if (isPinched) {
      this.cursorEl.classList.add('pinched');
    } else {
      this.cursorEl.classList.remove('pinched');
    }

    this._updateDwellEngine(x, y);
  }

  _updateDwellEngine(x, y) {
    const now = performance.now() / 1000;

    // In Cooldown state
    if (now < this.cooldownUntil) {
      this._setProgress(0);
      this.cursorEl.classList.add('cooldown');
      return;
    } else {
      this.cursorEl.classList.remove('cooldown');
    }

    // Hit test target element under (x, y)
    const el = document.elementFromPoint(x, y);
    const target = el ? el.closest('.gaze-target') : null;

    if (!target) {
      this._resetDwell();
      return;
    }

    // Target entered or focused
    if (this.currentTarget !== target) {
      this._resetDwell();
      this.currentTarget = target;
      this.dwellStartTime = now;
      target.classList.add('dwell-hover');
    } else {
      // Progressing dwell
      const elapsed = now - this.dwellStartTime;
      const progress = Math.min(1.0, elapsed / Math.max(0.1, this.dwellTimeSec));
      this._setProgress(progress);

      if (progress >= 1.0 && !this.isDwellLocked) {
        this._triggerSelection(target);
      }
    }
  }

  _setProgress(progress) {
    if (!this.ringProgressEl) return;
    const offset = this.circumference * (1 - progress);
    this.ringProgressEl.style.strokeDashoffset = offset;
  }

  _triggerSelection(target) {
    this.isDwellLocked = true;
    this._setProgress(1.0);

    // Visual pulse & audio feedback
    target.classList.add('dwell-complete');
    setTimeout(() => target.classList.remove('dwell-complete'), 350);
    window.AudioEngine.playSound('dwell');

    // Trigger click event
    target.click();

    // Enter cooldown
    const now = performance.now() / 1000;
    this.cooldownUntil = now + this.cooldownSec;
    this._resetDwell();
  }

  _resetDwell() {
    if (this.currentTarget) {
      this.currentTarget.classList.remove('dwell-hover');
      this.currentTarget = null;
    }
    this.dwellStartTime = 0;
    this.isDwellLocked = false;
    this._setProgress(0);
  }

  setAppearance(sizePx = 14, colorHex = '#38bdf8') {
    document.documentElement.style.setProperty('--cursor-color', colorHex);
    if (this.dotEl) {
      this.dotEl.style.width = `${sizePx}px`;
      this.dotEl.style.height = `${sizePx}px`;
    }
  }
}

window.CursorEngine = new HandCursorEngine();
