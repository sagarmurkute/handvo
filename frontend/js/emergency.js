/**
 * Dedicated Emergency Mode controller for HANDVO.
 */

class EmergencyController {
  constructor() {
    this.emergencyView = document.getElementById('view-emergency');
    this.cardsContainer = document.getElementById('emergency-cards-container');
    this.lblSpoken = document.getElementById('emergency-spoken-text');
    this.btnExit = document.getElementById('btn-exit-emergency');

    this.defaultActions = [
      { id: 1, label: 'Call Help', speech_text: 'Emergency! Please help me immediately!', icon: '🚨', color: '#ef4444' },
      { id: 2, label: 'I Need a Doctor', speech_text: 'I need a doctor right now!', icon: '👨‍⚕️', color: '#dc2626' },
      { id: 3, label: "I'm in Pain", speech_text: 'I am experiencing severe pain!', icon: '⚡', color: '#f97316' },
      { id: 4, label: "I Can't Breathe", speech_text: 'I cannot breathe, please help me quickly!', icon: '🫁', color: '#b91c1c' },
      { id: 5, label: 'Yes', speech_text: 'Yes', icon: '✅', color: '#22c55e' },
      { id: 6, label: 'No', speech_text: 'No', icon: '❌', color: '#64748b' },
    ];

    this._bindEvents();
    this.renderEmergencyCards();
  }

  _bindEvents() {
    this.btnExit?.addEventListener('click', () => {
      window.AppController?.switchView('comm');
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'F1') {
        e.preventDefault();
        const isEmergency = this.emergencyView?.classList.contains('active');
        window.AppController?.switchView(isEmergency ? 'comm' : 'emergency');
      }
    });
  }

  async renderEmergencyCards() {
    if (!this.cardsContainer) return;
    this.cardsContainer.innerHTML = '';

    let actions = this.defaultActions;
    try {
      const res = await fetch('/api/emergency/actions');
      if (res.ok) {
        const data = await res.json();
        if (data.actions && data.actions.length > 0) {
          actions = data.actions;
        }
      }
    } catch (e) {
      // Use default actions
    }

    actions.forEach((act) => {
      const card = document.createElement('button');
      card.className = 'emergency-card gaze-target';
      card.dataset.dwellId = `emg_${act.id}`;
      card.style.borderColor = act.color || '#ef4444';
      card.innerHTML = `
        <span class="card-icon">${act.icon || '🚨'}</span>
        <span class="card-label">${act.label}</span>
      `;
      card.addEventListener('click', () => {
        this.triggerEmergency(act);
      });
      this.cardsContainer.appendChild(card);
    });
  }

  triggerEmergency(action) {
    const text = action.speech_text || action.label;
    if (this.lblSpoken) {
      this.lblSpoken.textContent = `"${text}"`;
    }
    window.AudioEngine.playSound('emergency');
    window.AudioEngine.speak(text, true); // High-priority interrupt
  }
}

window.Emergency = new EmergencyController();
