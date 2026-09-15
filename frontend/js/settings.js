/**
 * Accessibility & Personalization Settings Suite for HANDVO.
 */

class SettingsManager {
  constructor() {
    this.modal = document.getElementById('modal-settings');
    this.btnClose = document.getElementById('btn-close-settings');
    this.btnDone = document.getElementById('btn-save-settings');
    this.btnOpen = document.getElementById('btn-open-settings');

    // Tab buttons
    this.tabButtons = document.querySelectorAll('.settings-tab-btn');
    this.tabPanels = document.querySelectorAll('.settings-tab-content');

    // Controls
    this.sliderDwell = document.getElementById('slider-dwell');
    this.lblDwell = document.getElementById('val-dwell-time');
    this.sliderCooldown = document.getElementById('slider-cooldown');
    this.lblCooldown = document.getElementById('val-cooldown-time');
    this.sliderSmoothing = document.getElementById('slider-smoothing');
    this.lblSmoothing = document.getElementById('val-smoothing');
    this.selectHand = document.getElementById('select-hand');

    this.sliderCursorSize = document.getElementById('slider-cursor-size');
    this.lblCursorSize = document.getElementById('val-cursor-size');
    this.selectTheme = document.getElementById('select-theme');
    this.selectScale = document.getElementById('select-scale');
    this.chkReducedMotion = document.getElementById('chk-reduced-motion');
    this.colorChips = document.querySelectorAll('.color-chip');

    this.selectVoice = document.getElementById('select-voice');
    this.sliderRate = document.getElementById('slider-speech-rate');
    this.lblRate = document.getElementById('val-speech-rate');
    this.sliderVol = document.getElementById('slider-speech-vol');
    this.lblVol = document.getElementById('val-speech-vol');
    this.chkDwellSound = document.getElementById('chk-dwell-sound');
    this.btnTestVoice = document.getElementById('btn-test-voice');
    this.selectLang = document.getElementById('select-language');

    this.currentProfile = null;
    this._bindEvents();
    this.loadSettings();
  }

  _bindEvents() {
    this.btnOpen?.addEventListener('click', () => this.open());
    this.btnClose?.addEventListener('click', () => this.close());
    this.btnDone?.addEventListener('click', () => this.close());

    window.addEventListener('keydown', (e) => {
      if (e.key === 'F2') {
        e.preventDefault();
        this.toggle();
      }
    });

    // Tab switching
    this.tabButtons.forEach(btn => {
      btn.addEventListener('click', () => {
        const tabId = btn.dataset.tab;
        this.tabButtons.forEach(b => b.classList.toggle('active', b === btn));
        this.tabPanels.forEach(p => p.classList.toggle('active', p.id === tabId));
      });
    });

    // Live slider changes
    this.sliderDwell?.addEventListener('input', (e) => {
      const val = (e.target.value / 100).toFixed(2);
      this.lblDwell.textContent = `${val}s`;
      window.CursorEngine.dwellTimeSec = parseFloat(val);
      this.saveLive();
    });

    this.sliderCooldown?.addEventListener('input', (e) => {
      const val = (e.target.value / 100).toFixed(2);
      this.lblCooldown.textContent = `${val}s`;
      window.CursorEngine.cooldownSec = parseFloat(val);
      this.saveLive();
    });

    this.sliderSmoothing?.addEventListener('input', (e) => {
      const val = (e.target.value / 10).toFixed(1);
      this.lblSmoothing.textContent = `${val}x`;
      this.saveLive();
    });

    this.sliderCursorSize?.addEventListener('input', (e) => {
      const val = e.target.value;
      this.lblCursorSize.textContent = `${val}px`;
      window.CursorEngine.setAppearance(val, this.currentProfile?.cursor_color || '#38bdf8');
      this.saveLive();
    });

    this.colorChips.forEach(chip => {
      chip.addEventListener('click', () => {
        const color = chip.dataset.color;
        if (this.currentProfile) this.currentProfile.cursor_color = color;
        window.CursorEngine.setAppearance(this.sliderCursorSize.value, color);
        this.saveLive();
      });
    });

    this.selectTheme?.addEventListener('change', (e) => {
      document.documentElement.setAttribute('data-theme', e.target.value);
      this.saveLive();
    });

    this.selectScale?.addEventListener('change', (e) => {
      document.documentElement.setAttribute('data-scale', e.target.value);
      this.saveLive();
    });

    this.selectLang?.addEventListener('change', (e) => {
      const lang = e.target.value;
      window.CommBoard?.setLanguage(lang);
      const txtBadge = document.getElementById('txt-lang-badge');
      if (txtBadge) {
        txtBadge.textContent = lang === 'hi' ? '🌐 हिंदी' : (lang === 'mr' ? '🌐 मराठी' : '🌐 English');
      }
      this.saveLive();
    });

    this.sliderRate?.addEventListener('input', (e) => {
      this.lblRate.textContent = `${e.target.value} WPM`;
      this.saveLive();
    });

    this.sliderVol?.addEventListener('input', (e) => {
      this.lblVol.textContent = `${e.target.value}%`;
      this.saveLive();
    });

    this.chkDwellSound?.addEventListener('change', (e) => {
      window.AudioEngine.soundEnabled = e.target.checked;
      this.saveLive();
    });

    this.btnTestVoice?.addEventListener('click', () => {
      const lang = this.selectLang?.value || 'en';
      const sample = lang === 'hi' ? 'नमस्ते, हैंडवो वाक् संश्लेषण ठीक से काम कर रहा है।'
        : (lang === 'mr' ? 'नमस्कार, हँडव्हो आवाज प्रणाली व्यवस्थित सुरू आहे.'
        : 'Hello, HANDVO text to speech synthesis is working properly.');
      window.AudioEngine.speak(sample);
    });
  }

  open() { this.modal?.classList.remove('hidden'); }
  close() { this.modal?.classList.add('hidden'); }
  toggle() { this.modal?.classList.toggle('hidden'); }

  async loadSettings() {
    try {
      const res = await fetch(window.getApiUrl('/api/profiles/active'));
      if (res.ok) {
        this.currentProfile = await res.json();
        this._populateUI(this.currentProfile);
      }
      this.loadVoices();
    } catch (e) {
      console.warn("Could not load active profile from backend:", e);
    }
  }

  async loadVoices() {
    if (!this.selectVoice) return;
    try {
      const res = await fetch(window.getApiUrl('/api/speech/voices'));
      if (res.ok) {
        const data = await res.json();
        this.selectVoice.innerHTML = '';
        (data.voices || []).forEach(v => {
          const opt = document.createElement('option');
          opt.value = v.id;
          opt.textContent = `🗣️ ${v.name}`;
          if (this.currentProfile && this.currentProfile.voice_id === v.id) {
            opt.selected = true;
          }
          this.selectVoice.appendChild(opt);
        });
      }
    } catch (e) {
      console.warn("Could not load voices:", e);
    }
  }

  _populateUI(p) {
    if (!p) return;
    if (this.sliderDwell) {
      this.sliderDwell.value = p.dwell_time * 100;
      this.lblDwell.textContent = `${p.dwell_time.toFixed(2)}s`;
      window.CursorEngine.dwellTimeSec = p.dwell_time;
    }
    if (this.sliderCooldown) {
      this.sliderCooldown.value = p.cooldown_time * 100;
      this.lblCooldown.textContent = `${p.cooldown_time.toFixed(2)}s`;
      window.CursorEngine.cooldownSec = p.cooldown_time;
    }
    if (this.selectTheme) {
      this.selectTheme.value = p.theme || 'dark';
      document.documentElement.setAttribute('data-theme', p.theme || 'dark');
    }
    if (this.selectScale) {
      this.selectScale.value = p.ui_scale || 'medium';
      document.documentElement.setAttribute('data-scale', p.ui_scale || 'medium');
    }
    if (this.selectLang) {
      this.selectLang.value = p.language || 'en';
      window.CommBoard?.setLanguage(p.language || 'en');
    }
    if (this.chkDwellSound) {
      this.chkDwellSound.checked = p.dwell_sound !== false;
      window.AudioEngine.soundEnabled = p.dwell_sound !== false;
    }

    window.CursorEngine?.setAppearance(p.cursor_size || 14, p.cursor_color || '#38bdf8');
  }

  async saveLive() {
    if (!this.currentProfile) return;
    this.currentProfile.dwell_time = parseFloat(this.sliderDwell.value) / 100;
    this.currentProfile.cooldown_time = parseFloat(this.sliderCooldown.value) / 100;
    this.currentProfile.theme = this.selectTheme.value;
    this.currentProfile.ui_scale = this.selectScale.value;
    this.currentProfile.language = this.selectLang.value;
    this.currentProfile.dwell_sound = this.chkDwellSound.checked;

    try {
      await fetch(window.getApiUrl('/api/profiles/active'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(this.currentProfile)
      });
    } catch (e) {
      // Offline fallback silent
    }
  }
}

window.Settings = new SettingsManager();
