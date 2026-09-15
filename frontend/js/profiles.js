/**
 * Caregiver Profile Manager for HANDVO.
 */

class ProfileManager {
  constructor() {
    this.modal = document.getElementById('modal-profiles');
    this.btnClose = document.getElementById('btn-close-profiles');
    this.btnOpen = document.getElementById('btn-active-profile');
    this.listContainer = document.getElementById('profiles-list-container');
    this.btnNew = document.getElementById('btn-new-profile');
    this.btnExport = document.getElementById('btn-export-profile');
    this.inputImport = document.getElementById('input-import-profile');
    this.lblProfileName = document.getElementById('lbl-profile-name');

    this._bindEvents();
  }

  _bindEvents() {
    this.btnOpen?.addEventListener('click', () => this.open());
    this.btnClose?.addEventListener('click', () => this.close());
    this.btnNew?.addEventListener('click', () => this.createNewProfile());
    this.btnExport?.addEventListener('click', () => this.exportProfile());
    this.inputImport?.addEventListener('change', (e) => this.importProfile(e));
  }

  open() {
    this.modal?.classList.remove('hidden');
    this.loadProfiles();
  }

  close() {
    this.modal?.classList.add('hidden');
  }

  async loadProfiles() {
    try {
      const res = await fetch(window.getApiUrl('/api/profiles'));
      if (res.ok) {
        const profiles = await res.json();
        this.renderProfilesList(profiles);
      }
    } catch (e) {
      console.warn("Could not load profiles:", e);
    }
  }

  renderProfilesList(profiles) {
    if (!this.listContainer) return;
    this.listContainer.innerHTML = '';

    profiles.forEach(p => {
      const item = document.createElement('div');
      item.className = `profile-item ${p.is_active ? 'active' : ''}`;
      item.innerHTML = `
        <div>
          <strong>${p.name}</strong> ${p.is_active ? '<span style="color:var(--accent-cyan); font-size:11px;">(Active)</span>' : ''}
          <div style="font-size:11px; color:var(--text-muted);">Dwell: ${p.dwell_time}s | Lang: ${p.language.toUpperCase()}</div>
        </div>
        <div style="display:flex; gap:6px;">
          ${!p.is_active ? `<button class="action-btn btn-sm btn-select-p" style="padding:4px 10px; font-size:11px;">Activate</button>` : ''}
          <button class="action-btn btn-sm btn-dup-p" style="padding:4px 10px; font-size:11px;">Duplicate</button>
        </div>
      `;

      item.querySelector('.btn-select-p')?.addEventListener('click', () => this.activateProfile(p.id));
      item.querySelector('.btn-dup-p')?.addEventListener('click', () => this.duplicateProfile(p.id, p.name));

      this.listContainer.appendChild(item);
    });
  }

  async activateProfile(profileId) {
    try {
      const res = await fetch(window.getApiUrl(`/api/profiles/${profileId}/activate`), { method: 'POST' });
      if (res.ok) {
        const profile = await res.json();
        if (this.lblProfileName) this.lblProfileName.textContent = profile.name;
        window.Settings?.loadSettings();
        this.loadProfiles();
      }
    } catch (e) {
      console.warn("Activate failed:", e);
    }
  }

  async createNewProfile() {
    const name = prompt("Enter New Profile Name:", "New User");
    if (!name) return;

    try {
      const res = await fetch(window.getApiUrl('/api/profiles'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim() })
      });
      if (res.ok) {
        this.loadProfiles();
      }
    } catch (e) {
      console.warn("Create failed:", e);
    }
  }

  async duplicateProfile(id, name) {
    try {
      const res = await fetch(window.getApiUrl(`/api/profiles/${id}/duplicate`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ new_name: `${name} (Copy)` })
      });
      if (res.ok) {
        this.loadProfiles();
      }
    } catch (e) {
      console.warn("Duplicate failed:", e);
    }
  }

  async exportProfile() {
    try {
      const res = await fetch(window.getApiUrl('/api/profiles/active/export'));
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `handvo_profile_export.json`;
        a.click();
      }
    } catch (e) {
      console.warn("Export failed:", e);
    }
  }

  async importProfile(e) {
    const file = e.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (evt) => {
      try {
        const jsonContent = evt.target.result;
        const res = await fetch(window.getApiUrl('/api/profiles/import'), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: jsonContent
        });
        if (res.ok) {
          alert("Profile successfully imported!");
          this.loadProfiles();
        }
      } catch (err) {
        alert("Failed to import profile JSON");
      }
    };
    reader.readAsText(file);
  }
}

window.Profiles = new ProfileManager();
