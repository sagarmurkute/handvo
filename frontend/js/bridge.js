/**
 * Frontend–Backend Communication Layer Bridge for HANDVO.
 * 
 * Provides a unified API contract and event-driven bridge connecting all
 * HTML5/CSS/JS screens with the Python backend services (WebSocket, REST, or Qt WebChannel).
 */

class HANDVOBridgeClient {
  constructor() {
    this._listeners = new Map();
    this.isQtWebChannel = false;
    this.qtChannel = null;

    this._initTransport();
  }

  /**
   * Initialize bridge transport (Qt WebChannel if embedded, or WebSocket/REST).
   */
  _initTransport() {
    // Check if Qt WebChannel is injected in window
    if (typeof QWebChannel !== 'undefined' && window.qt && window.qt.webChannelTransport) {
      try {
        new QWebChannel(window.qt.webChannelTransport, (channel) => {
          this.qtChannel = channel.objects.handvo_bridge || channel.objects.bridge;
          this.isQtWebChannel = true;
          console.log("[HANDVO Bridge] Connected via Qt WebChannel transport");
          this.emit('bridge:ready', { transport: 'qt_webchannel' });
        });
      } catch (e) {
        console.warn("[HANDVO Bridge] Qt WebChannel init failed, falling back to WebSocket/REST:", e);
      }
    } else {
      console.log("[HANDVO Bridge] Connected via WebSocket / REST transport");
      // Fire ready event on next tick
      setTimeout(() => this.emit('bridge:ready', { transport: 'websocket_rest' }), 0);
    }
  }

  // -------------------------------------------------------------
  // Event Emitter Pattern (Subscribe / Unsubscribe / Emit)
  // -------------------------------------------------------------

  /**
   * Subscribe to a bridge event.
   * @param {string} event - Event name (e.g. 'cursor:update', 'dwell:complete')
   * @param {Function} callback - Event handler function
   */
  on(event, callback) {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set());
    }
    this._listeners.get(event).add(callback);
  }

  /**
   * Unsubscribe from a bridge event.
   * @param {string} event
   * @param {Function} callback
   */
  off(event, callback) {
    if (this._listeners.has(event)) {
      this._listeners.get(event).delete(callback);
    }
  }

  /**
   * Emit an event internally across frontend components.
   * @param {string} event
   * @param {any} data
   */
  emit(event, data) {
    if (this._listeners.has(event)) {
      this._listeners.get(event).forEach((cb) => {
        try {
          cb(data);
        } catch (e) {
          console.error(`[HANDVO Bridge] Error in handler for event '${event}':`, e);
        }
      });
    }
  }

  // -------------------------------------------------------------
  // URL & Endpoint Resolvers
  // -------------------------------------------------------------

  getApiUrl(path) {
    if (!path.startsWith('/')) path = '/' + path;
    const isFile = window.location.protocol === 'file:';
    if (isFile || !window.location.host) {
      return `http://127.0.0.1:8000${path}`;
    }
    return path;
  }

  getWsUrl(path = '/ws/vision') {
    const isFile = window.location.protocol === 'file:';
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = (!isFile && window.location.host) ? window.location.host : '127.0.0.1:8000';
    return `${protocol}//${host}${path}`;
  }

  // -------------------------------------------------------------
  // Vision, Camera & Hand Tracking API
  // -------------------------------------------------------------

  startCamera() {
    window.VisionWS?.sendCommand('START_CAMERA');
    this.emit('camera:state_changed', { active: true });
  }

  stopCamera() {
    window.VisionWS?.sendCommand('STOP_CAMERA');
    this.emit('camera:state_changed', { active: false });
  }

  sendCursorUpdate(packet) {
    this.emit('cursor:update', packet);
  }

  // -------------------------------------------------------------
  // Dwell Progress & Selection API
  // -------------------------------------------------------------

  sendDwellProgress(targetId, progress, isCompleted = false) {
    const payload = { targetId, progress, isCompleted, timestamp: Date.now() };
    this.emit('dwell:progress', payload);
    if (isCompleted) {
      this.emit('dwell:complete', payload);
    }
  }

  // -------------------------------------------------------------
  // AAC Board & Communication API
  // -------------------------------------------------------------

  notifyPhraseSelected(phraseText, categoryId) {
    const payload = { phrase: phraseText, category: categoryId, timestamp: Date.now() };
    this.emit('aac:phrase_selected', payload);
    return payload;
  }

  notifySentenceUpdated(currentSentence) {
    const payload = { sentence: currentSentence, timestamp: Date.now() };
    this.emit('aac:sentence_updated', payload);
    return payload;
  }

  // -------------------------------------------------------------
  // Text-To-Speech (TTS) API
  // -------------------------------------------------------------

  async speakText(text, interrupt = false) {
    if (!text || !text.trim()) return;
    this.emit('speech:request', { text, interrupt });

    try {
      const res = await fetch(this.getApiUrl('/api/speech/speak'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim(), interrupt: interrupt })
      });
      if (res.ok) {
        this.emit('speech:started', { text });
        return true;
      }
    } catch (e) {
      console.warn("[HANDVO Bridge] Offline speech fallback:", e);
    }

    // Web Speech API fallback
    if ('speechSynthesis' in window) {
      if (interrupt) window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text.trim());
      utterance.onstart = () => this.emit('speech:started', { text });
      utterance.onend = () => this.emit('speech:finished', { text });
      window.speechSynthesis.speak(utterance);
      return true;
    }
    return false;
  }

  async getVoices() {
    try {
      const res = await fetch(this.getApiUrl('/api/speech/voices'));
      if (res.ok) {
        const data = await res.json();
        return data.voices || [];
      }
    } catch (e) {
      console.warn("[HANDVO Bridge] Could not fetch voices:", e);
    }
    return [];
  }

  // -------------------------------------------------------------
  // Smart Next-Word Prediction API
  // -------------------------------------------------------------

  async getPredictions(sentence = '', category = 'common') {
    try {
      const url = this.getApiUrl(`/api/predictions?sentence=${encodeURIComponent(sentence)}&category=${encodeURIComponent(category)}`);
      const res = await fetch(url);
      if (res.ok) {
        const data = await res.json();
        this.emit('prediction:updated', { predictions: data.predictions || [] });
        return data.predictions || [];
      }
    } catch (e) {
      console.warn("[HANDVO Bridge] Using local prediction priors:", e);
    }
    return [];
  }

  async learnSelection(prevSentence, selectedPhrase, categoryId) {
    try {
      await fetch(this.getApiUrl('/api/predictions/learn'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prev_sentence: prevSentence,
          selected_token: selectedPhrase,
          category_id: categoryId,
        })
      });
      this.emit('prediction:learned', { prevSentence, selectedPhrase, categoryId });
    } catch (e) {
      // Silent offline fallback
    }
  }

  // -------------------------------------------------------------
  // Caregiver Profiles & Settings API
  // -------------------------------------------------------------

  async getActiveProfile() {
    try {
      const res = await fetch(this.getApiUrl('/api/profiles/active'));
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("[HANDVO Bridge] Could not load active profile:", e);
    }
    return null;
  }

  async saveActiveProfile(profileData) {
    try {
      const res = await fetch(this.getApiUrl('/api/profiles/active'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileData)
      });
      if (res.ok) {
        this.emit('settings:saved', profileData);
        return await res.json();
      }
    } catch (e) {
      console.warn("[HANDVO Bridge] Could not save active profile:", e);
    }
    return null;
  }

  async getProfiles() {
    try {
      const res = await fetch(this.getApiUrl('/api/profiles'));
      if (res.ok) return await res.json();
    } catch (e) {
      console.warn("[HANDVO Bridge] Could not fetch profiles:", e);
    }
    return [];
  }

  async activateProfile(profileId) {
    try {
      const res = await fetch(this.getApiUrl(`/api/profiles/${profileId}/activate`), { method: 'POST' });
      if (res.ok) {
        const p = await res.json();
        this.emit('profile:active_changed', p);
        return p;
      }
    } catch (e) {
      console.warn("[HANDVO Bridge] Could not activate profile:", e);
    }
    return null;
  }

  // -------------------------------------------------------------
  // Emergency Mode API
  // -------------------------------------------------------------

  async getEmergencyActions() {
    try {
      const res = await fetch(this.getApiUrl('/api/emergency/actions'));
      if (res.ok) {
        const data = await res.json();
        return data.actions || [];
      }
    } catch (e) {
      console.warn("[HANDVO Bridge] Could not fetch emergency actions:", e);
    }
    return [];
  }

  triggerEmergency(action) {
    this.emit('emergency:triggered', action);
    const text = action.speech_text || action.label;
    this.speakText(text, true);
  }
}

// Instantiate global singleton bridge instance
window.HANDVOBridge = new HANDVOBridgeClient();
