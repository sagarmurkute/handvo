/**
 * AAC Communication Board Model and UI Renderer for HANDVO.
 */

class CommunicationBoard {
  constructor() {
    this.tokens = [];
    this.activeCategory = 'common';
    this.language = 'en';

    this.txtComposed = document.getElementById('composed-text');
    this.lblWordCount = document.getElementById('lbl-word-count');
    this.categoriesContainer = document.getElementById('category-tabs-container');
    this.phrasesContainer = document.getElementById('phrase-cards-container');

    this._initVocabularies();
    this._bindControls();
  }

  _initVocabularies() {
    this.vocabularies = {
      en: {
        categories: [
          { id: 'common', name: 'Common', icon: '⭐', color: '#38bdf8' },
          { id: 'needs', name: 'Needs', icon: '🚰', color: '#22c55e' },
          { id: 'feelings', name: 'Feelings', icon: '❤️', color: '#ec4899' },
          { id: 'people', name: 'People', icon: '👥', color: '#f59e0b' },
          { id: 'places', name: 'Places', icon: '🏠', color: '#8b5cf6' },
          { id: 'actions', name: 'Actions', icon: '🏃', color: '#06b6d4' },
        ],
        items: {
          common: [
            { id: 'yes', label: 'Yes', text: 'Yes', icon: '✅' },
            { id: 'no', label: 'No', text: 'No', icon: '❌' },
            { id: 'please', label: 'Please', text: 'Please', icon: '🙏' },
            { id: 'thank_you', label: 'Thank You', text: 'Thank you', icon: '🌸' },
            { id: 'hello', label: 'Hello', text: 'Hello', icon: '👋' },
            { id: 'goodbye', label: 'Goodbye', text: 'Goodbye', icon: '👋' },
            { id: 'help', label: 'Help', text: 'I need help', icon: '🆘' },
            { id: 'ok', label: 'OK', text: 'OK', icon: '👌' },
          ],
          needs: [
            { id: 'water', label: 'Water', text: 'I need water', icon: '💧' },
            { id: 'food', label: 'Food', text: 'I am hungry, I need food', icon: '🍲' },
            { id: 'bathroom', label: 'Bathroom', text: 'I need the bathroom', icon: '🚻' },
            { id: 'medicine', label: 'Medicine', text: 'I need my medicine', icon: '💊' },
            { id: 'rest', label: 'Rest / Sleep', text: 'I want to rest and sleep', icon: '🛏️' },
            { id: 'blanket', label: 'Blanket', text: 'I need a blanket, I am cold', icon: '🧣' },
          ],
          feelings: [
            { id: 'happy', label: 'Happy', text: 'I am feeling happy', icon: '😊' },
            { id: 'sad', label: 'Sad', text: 'I feel sad', icon: '😢' },
            { id: 'tired', label: 'Tired', text: 'I am very tired', icon: '🥱' },
            { id: 'pain', label: 'In Pain', text: 'I am experiencing pain', icon: '⚡' },
            { id: 'scared', label: 'Scared / Anxious', text: 'I feel scared and anxious', icon: '😨' },
            { id: 'good', label: 'Good', text: 'I am feeling good', icon: '👍' },
          ],
          people: [
            { id: 'doctor', label: 'Doctor', text: 'Please call the doctor', icon: '👨‍⚕️' },
            { id: 'nurse', label: 'Nurse', text: 'Please call the nurse', icon: '👩‍⚕️' },
            { id: 'family', label: 'Family', text: 'I want to see my family', icon: '👨‍👩‍👧' },
            { id: 'friend', label: 'Friend', text: 'I want to talk to my friend', icon: '🤝' },
            { id: 'caregiver', label: 'Caregiver', text: 'I need the caregiver', icon: '🧑‍🦽' },
          ],
          places: [
            { id: 'home', label: 'Home', text: 'I want to go home', icon: '🏠' },
            { id: 'hospital', label: 'Hospital', text: 'I am at the hospital', icon: '🏥' },
            { id: 'room', label: 'My Room', text: 'I want to go to my room', icon: '🚪' },
            { id: 'outside', label: 'Outside', text: 'I want to go outside for fresh air', icon: '🌳' },
          ],
          actions: [
            { id: 'eat', label: 'Eat', text: 'I want to eat', icon: '🍽️' },
            { id: 'drink', label: 'Drink', text: 'I want to drink', icon: '🥤' },
            { id: 'sit', label: 'Sit Up', text: 'Please help me sit up', icon: '🪑' },
            { id: 'stand', label: 'Stand Up', text: 'Please help me stand up', icon: '🧍' },
            { id: 'walk', label: 'Walk', text: 'I want to go for a walk', icon: '🚶' },
            { id: 'stop', label: 'Stop', text: 'Please stop', icon: '🛑' },
          ]
        }
      },
      hi: {
        categories: [
          { id: 'common', name: 'सामान्य', icon: '⭐', color: '#38bdf8' },
          { id: 'needs', name: 'ज़रूरतें', icon: '🚰', color: '#22c55e' },
          { id: 'feelings', name: 'भावनाएँ', icon: '❤️', color: '#ec4899' },
          { id: 'people', name: 'लोग', icon: '👥', color: '#f59e0b' },
          { id: 'places', name: 'स्थान', icon: '🏠', color: '#8b5cf6' },
          { id: 'actions', name: 'क्रियाएँ', icon: '🏃', color: '#06b6d4' },
        ],
        items: {
          common: [
            { id: 'yes', label: 'हाँ (Yes)', text: 'हाँ', icon: '✅' },
            { id: 'no', label: 'नहीं (No)', text: 'नहीं', icon: '❌' },
            { id: 'please', label: 'कृपया (Please)', text: 'कृपया', icon: '🙏' },
            { id: 'thank_you', label: 'धन्यवाद (Thanks)', text: 'धन्यवाद', icon: '🌸' },
            { id: 'hello', label: 'नमस्ते (Hello)', text: 'नमस्ते', icon: '👋' },
            { id: 'help', label: 'मदद (Help)', text: 'मुझे मदद चाहिए', icon: '🆘' },
          ],
          needs: [
            { id: 'water', label: 'पानी (Water)', text: 'मुझे पानी चाहिए', icon: '💧' },
            { id: 'food', label: 'खाना (Food)', text: 'मुझे भूख लगी है, खाना चाहिए', icon: '🍲' },
            { id: 'bathroom', label: 'शौचालय (Washroom)', text: 'मुझे शौचालय जाना है', icon: '🚻' },
            { id: 'medicine', label: 'दवा (Medicine)', text: 'मुझे मेरी दवा चाहिए', icon: '💊' },
            { id: 'rest', label: 'आराम (Rest)', text: 'मुझे आराम करना है', icon: '🛏️' },
          ],
          feelings: [
            { id: 'happy', label: 'खुश (Happy)', text: 'मैं बहुत खुश हूँ', icon: '😊' },
            { id: 'pain', label: 'दर्द (Pain)', text: 'मुझे दर्द हो रहा है', icon: '⚡' },
            { id: 'tired', label: 'थका हुआ (Tired)', text: 'मैं बहुत थक गया हूँ', icon: '🥱' },
            { id: 'scared', label: 'डर (Scared)', text: 'मुझे डर लग रहा है', icon: '😨' },
          ],
          people: [
            { id: 'doctor', label: 'डॉक्टर (Doctor)', text: 'डॉक्टर को बुलाइए', icon: '👨‍⚕️' },
            { id: 'family', label: 'परिवार (Family)', text: 'मुझे परिवार से मिलना है', icon: '👨‍👩‍👧' },
          ],
          places: [
            { id: 'home', label: 'घर (Home)', text: 'मुझे घर जाना है', icon: '🏠' },
            { id: 'hospital', label: 'अस्पताल (Hospital)', text: 'अस्पताल', icon: '🏥' },
          ],
          actions: [
            { id: 'eat', label: 'खाना खाना (Eat)', text: 'मुझे खाना खाना है', icon: '🍽️' },
            { id: 'drink', label: 'पीना (Drink)', text: 'मुझे पीना है', icon: '🥤' },
          ]
        }
      },
      mr: {
        categories: [
          { id: 'common', name: 'सामान्य', icon: '⭐', color: '#38bdf8' },
          { id: 'needs', name: 'गरजा', icon: '🚰', color: '#22c55e' },
          { id: 'feelings', name: 'भावना', icon: '❤️', color: '#ec4899' },
          { id: 'people', name: 'लोक', icon: '👥', color: '#f59e0b' },
          { id: 'places', name: 'ठिकाणे', icon: '🏠', color: '#8b5cf6' },
          { id: 'actions', name: 'कृती', icon: '🏃', color: '#06b6d4' },
        ],
        items: {
          common: [
            { id: 'yes', label: 'होय (Yes)', text: 'होय', icon: '✅' },
            { id: 'no', label: 'नाही (No)', text: 'नाही', icon: '❌' },
            { id: 'please', label: 'कृपया (Please)', text: 'कृपया', icon: '🙏' },
            { id: 'thank_you', label: 'धन्यवाद (Thanks)', text: 'धन्यवाद', icon: '🌸' },
            { id: 'hello', label: 'नमस्कार (Hello)', text: 'नमस्कार', icon: '👋' },
            { id: 'help', label: 'मदत (Help)', text: 'मला मदतीची गरज आहे', icon: '🆘' },
          ],
          needs: [
            { id: 'water', label: 'पाणी (Water)', text: 'मला पाणी हवे आहे', icon: '💧' },
            { id: 'food', label: 'जेवण (Food)', text: 'मला भूक लागली आहे, जेवण हवे आहे', icon: '🍲' },
            { id: 'bathroom', label: 'स्वच्छतागृह (Toilet)', text: 'मला स्वच्छतागृहात जायचे आहे', icon: '🚻' },
            { id: 'medicine', label: 'औषध (Medicine)', text: 'मला माझे औषध हवे आहे', icon: '💊' },
          ],
          feelings: [
            { id: 'happy', label: 'आनंदी (Happy)', text: 'मी आनंदी आहे', icon: '😊' },
            { id: 'pain', label: 'वेदना (Pain)', text: 'मला खूप वेदना होत आहेत', icon: '⚡' },
            { id: 'tired', label: 'थकलो (Tired)', text: 'मी खूप थकलो आहे', icon: '🥱' },
          ],
          people: [
            { id: 'doctor', label: 'डॉक्टर (Doctor)', text: 'कृपया डॉक्टरना बोलवा', icon: '👨‍⚕️' },
            { id: 'family', label: 'कुटुंब (Family)', text: 'मला कुटुंबाला भेटायचे आहे', icon: '👨‍👩‍👧' },
          ],
          places: [
            { id: 'home', label: 'घर (Home)', text: 'मला घरी जायचे आहे', icon: '🏠' },
          ],
          actions: [
            { id: 'eat', label: 'जेवणे (Eat)', text: 'मला जेवायचे आहे', icon: '🍽️' },
            { id: 'drink', label: 'पिणे (Drink)', text: 'मला पाणी प्यायचे आहे', icon: '🥤' },
          ]
        }
      }
    };
  }

  _bindControls() {
    document.getElementById('btn-speak')?.addEventListener('click', () => this.speakSentence());
    document.getElementById('btn-space')?.addEventListener('click', () => this.addToken(' '));
    document.getElementById('btn-delete')?.addEventListener('click', () => this.deleteLastToken());
    document.getElementById('btn-clear')?.addEventListener('click', () => this.clearSentence());
  }

  setLanguage(langCode) {
    if (this.vocabularies[langCode]) {
      this.language = langCode;
      this.renderCategories();
      this.renderPhraseCards();
    }
  }

  renderCategories() {
    if (!this.categoriesContainer) return;
    this.categoriesContainer.innerHTML = '';

    const vocab = this.vocabularies[this.language] || this.vocabularies.en;
    vocab.categories.forEach(cat => {
      const btn = document.createElement('button');
      btn.className = `cat-tab-btn gaze-target ${cat.id === this.activeCategory ? 'active' : ''}`;
      btn.dataset.dwellId = `cat_${cat.id}`;
      btn.innerHTML = `<span class="cat-icon">${cat.icon}</span> ${cat.name}`;
      btn.addEventListener('click', () => {
        this.activeCategory = cat.id;
        this.renderCategories();
        this.renderPhraseCards();
      });
      this.categoriesContainer.appendChild(btn);
    });
  }

  cycleCategory(delta = 1) {
    const vocab = this.vocabularies[this.language] || this.vocabularies.en;
    const cats = vocab.categories || [];
    if (cats.length === 0) return;
    const currentIdx = cats.findIndex(c => c.id === this.activeCategory);
    let nextIdx = (currentIdx + delta) % cats.length;
    if (nextIdx < 0) nextIdx += cats.length;
    this.activeCategory = cats[nextIdx].id;
    this.renderCategories();
    this.renderPhraseCards();
    window.PredictionEngine?.updatePredictions(this.getCurrentSentence(), this.activeCategory);
    window.AudioEngine?.playSound('click');
  }

  renderPhraseCards() {
    if (!this.phrasesContainer) return;
    this.phrasesContainer.innerHTML = '';

    const vocab = this.vocabularies[this.language] || this.vocabularies.en;
    const items = vocab.items[this.activeCategory] || vocab.items.common || [];

    items.forEach(item => {
      const card = document.createElement('button');
      card.className = 'phrase-card gaze-target';
      card.dataset.dwellId = `card_${item.id}`;
      card.innerHTML = `
        <span class="card-icon">${item.icon}</span>
        <span class="card-label">${item.label}</span>
        <span class="card-subtitle">${item.text}</span>
      `;
      card.addEventListener('click', () => {
        this.addToken(item.text);
        if (window.PredictionEngine) {
          window.PredictionEngine.learn(this.getCurrentSentence(), item.text, this.activeCategory);
        }
      });
      this.phrasesContainer.appendChild(card);
    });
  }

  addToken(text) {
    this.tokens.push(text);
    this._updateSentenceDisplay();
  }

  deleteLastToken() {
    if (this.tokens.length > 0) {
      this.tokens.pop();
      this._updateSentenceDisplay();
    }
  }

  clearSentence() {
    this.tokens = [];
    this._updateSentenceDisplay();
    window.AudioEngine.playSound('clear');
  }

  getCurrentSentence() {
    return this.tokens.join(' ').trim();
  }

  _updateSentenceDisplay() {
    const text = this.getCurrentSentence();
    if (this.txtComposed) {
      if (text) {
        this.txtComposed.textContent = text;
        this.txtComposed.className = 'active-text';
      } else {
        this.txtComposed.textContent = 'Point hand cursor or click on cards below to compose a sentence...';
        this.txtComposed.className = 'placeholder-text';
      }
    }

    const wordCount = this.tokens.filter(t => t.trim()).length;
    if (this.lblWordCount) {
      this.lblWordCount.textContent = `${wordCount} ${wordCount === 1 ? 'Word' : 'Words'}`;
    }

    if (window.PredictionEngine) {
      window.PredictionEngine.updatePredictions(text, this.activeCategory);
    }
  }

  speakSentence() {
    const text = this.getCurrentSentence();
    if (text) {
      window.AudioEngine.speak(text);
    }
  }
}

window.CommBoard = new CommunicationBoard();
