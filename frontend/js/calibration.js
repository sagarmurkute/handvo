/**
 * Guided 5-Step Hand Calibration Wizard for HANDVO.
 */

class CalibrationWizard {
  constructor() {
    this.modal = document.getElementById('modal-calibration');
    this.btnClose = document.getElementById('btn-close-calibration');
    this.btnOpen = document.getElementById('btn-calibrate-hand');
    this.btnAction = document.getElementById('btn-calib-action');
    this.progressFill = document.getElementById('calib-progress-fill');
    this.stepTitle = document.getElementById('calib-step-title');
    this.stepDesc = document.getElementById('calib-step-desc');
    this.stepIndicators = document.querySelectorAll('.calibration-step-indicator .step');

    this.currentStep = 1;
    this.isSampling = false;
    this.samples = [];

    this.steps = [
      { num: 1, title: 'Step 1: Comfortable Resting Position', desc: 'Hold your hand in your natural, comfortable center position in front of the camera.' },
      { num: 2, title: 'Step 2: Movement Range (Edges)', desc: 'Move your hand slowly to the comfortable left, right, top, and bottom edges of your reach.' },
      { num: 3, title: 'Step 3: Dominant Hand Identification', desc: 'Raise your primary dominant hand (Left or Right) clearly in the camera view.' },
      { num: 4, title: 'Step 4: Pinch Distance Baseline', desc: 'Perform 3 natural index-thumb pinches to measure your baseline pinch depth.' },
      { num: 5, title: 'Step 5: Validation & Quality Score', desc: 'Calibration complete! Saving your personalized metrics to your user profile.' },
    ];

    this._bindEvents();
  }

  _bindEvents() {
    this.btnOpen?.addEventListener('click', () => this.open());
    this.btnClose?.addEventListener('click', () => this.close());
    this.btnAction?.addEventListener('click', () => this.onActionButton());
  }

  open() {
    this.currentStep = 1;
    this.isSampling = false;
    this._renderStep();
    this.modal?.classList.remove('hidden');
  }

  close() {
    this.modal?.classList.add('hidden');
  }

  _renderStep() {
    const s = this.steps[this.currentStep - 1];
    if (this.stepTitle) this.stepTitle.textContent = s.title;
    if (this.stepDesc) this.stepDesc.textContent = s.desc;
    if (this.btnAction) this.btnAction.textContent = this.currentStep === 5 ? 'Done' : 'Start Sampling';
    if (this.progressFill) this.progressFill.style.width = '0%';

    this.stepIndicators.forEach(el => {
      const stepNum = parseInt(el.dataset.step);
      el.classList.toggle('active', stepNum === this.currentStep);
    });
  }

  onActionButton() {
    if (this.currentStep === 5) {
      this.close();
      return;
    }

    if (this.isSampling) return;

    this.isSampling = true;
    this.btnAction.disabled = true;
    this.btnAction.textContent = 'Sampling...';

    let progress = 0;
    const interval = setInterval(() => {
      progress += 10;
      if (this.progressFill) this.progressFill.style.width = `${progress}%`;

      if (progress >= 100) {
        clearInterval(interval);
        this.isSampling = false;
        this.btnAction.disabled = false;
        this.currentStep++;
        this._renderStep();
      }
    }, 150);
  }
}

window.Calibration = new CalibrationWizard();
