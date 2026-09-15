/**
 * Smart next-word prediction chips engine for HANDVO AAC.
 */

class SmartPredictionEngine {
  constructor() {
    this.container = document.getElementById('prediction-chips-container');
    this.defaultPriors = {
      common: ['please', 'thank you', 'yes', 'no', 'help'],
      needs: ['water', 'food', 'medicine', 'bathroom', 'rest'],
      feelings: ['good', 'pain', 'happy', 'tired', 'sad'],
      people: ['doctor', 'nurse', 'family', 'caregiver'],
      places: ['home', 'hospital', 'room', 'outside'],
      actions: ['eat', 'drink', 'sit', 'walk', 'help'],
    };
  }

  async updatePredictions(currentSentence = '', categoryId = 'common') {
    if (!this.container) return;

    let candidates = [];
    try {
      const response = await fetch(`/api/predictions?sentence=${encodeURIComponent(currentSentence)}&category=${encodeURIComponent(categoryId)}`);
      if (response.ok) {
        const data = await response.json();
        candidates = data.predictions || [];
      }
    } catch (e) {
      // Local fallback
      candidates = this._getLocalPredictions(currentSentence, categoryId);
    }

    if (candidates.length === 0) {
      candidates = this._getLocalPredictions(currentSentence, categoryId);
    }

    this.renderChips(candidates);
  }

  _getLocalPredictions(sentence, category) {
    const s = sentence.trim().toLowerCase();
    if (!s) {
      return (this.defaultPriors[category] || this.defaultPriors.common).slice(0, 5);
    }

    if (s.endsWith('i need') || s === 'i need') {
      return ['water', 'help', 'doctor', 'medicine', 'food'];
    } else if (s.endsWith('i am') || s === 'i am') {
      return ['happy', 'in pain', 'tired', 'cold', 'hungry'];
    } else if (s.endsWith('i want') || s === 'i want') {
      return ['to rest', 'to go home', 'to eat', 'water', 'to sleep'];
    } else if (s.endsWith('please') || s === 'please') {
      return ['help me', 'call doctor', 'bring water', 'sit me up'];
    }

    return (this.defaultPriors[category] || this.defaultPriors.common).slice(0, 5);
  }

  renderChips(candidates) {
    this.container.innerHTML = '';
    candidates.forEach((cand, idx) => {
      const text = typeof cand === 'string' ? cand : (cand.text || cand.label);
      const chip = document.createElement('button');
      chip.className = 'pred-chip gaze-target';
      chip.dataset.dwellId = `pred_${idx}`;
      chip.textContent = text;
      chip.addEventListener('click', () => {
        if (window.CommBoard) {
          window.CommBoard.addToken(text);
          this.learn(window.CommBoard.getCurrentSentence(), text, window.CommBoard.activeCategory);
        }
      });
      this.container.appendChild(chip);
    });
  }

  async learn(prevSentence, selectedToken, categoryId) {
    try {
      await fetch('/api/predictions/learn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prev_sentence: prevSentence,
          selected_token: selectedToken,
          category_id: categoryId,
        })
      });
    } catch (e) {
      // Offline fallback silent
    }
  }
}

window.PredictionEngine = new SmartPredictionEngine();
