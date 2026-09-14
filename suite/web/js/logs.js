/**
 * Debug Log Console & Real-Time Log Viewer for MLPMP Full Suite.
 */

class LogViewer {
  constructor() {
    this.modal = document.getElementById('log-modal');
    this.container = document.getElementById('log-entries');
    this.autoScrollCheckbox = document.getElementById('log-autoscroll');
    this.pollInterval = null;
  }

  open() {
    if (this.modal) {
      this.modal.classList.add('open');
      this.refresh();
      if (!this.pollInterval) {
        this.pollInterval = setInterval(() => this.refresh(), 2000);
      }
    }
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('open');
      if (this.pollInterval) {
        clearInterval(this.pollInterval);
        this.pollInterval = null;
      }
    }
  }

  async refresh() {
    try {
      const data = await window.api.get('/api/logs');
      if (!data || !data.logs || !this.container) return;

      this.container.innerHTML = '';
      data.logs.forEach((entry) => {
        const row = document.createElement('div');
        row.className = 'log-entry';

        const time = document.createElement('span');
        time.className = 'log-time';
        time.textContent = `[${entry.timestamp}]`;

        const lvl = document.createElement('span');
        lvl.className = `log-lvl ${entry.level}`;
        lvl.textContent = `[${entry.level}]`;

        const msg = document.createElement('span');
        msg.className = 'log-msg';
        msg.textContent = entry.message;

        row.appendChild(time);
        row.appendChild(lvl);
        row.appendChild(msg);
        this.container.appendChild(row);
      });

      if (this.autoScrollCheckbox && this.autoScrollCheckbox.checked) {
        this.container.scrollTop = this.container.scrollHeight;
      }
    } catch (e) {
      console.warn('Failed refreshing logs:', e);
    }
  }

  async clear() {
    try {
      await window.api.post('/api/logs/clear');
      this.refresh();
      window.toast.info('Debug log cleared.');
    } catch (e) {
      console.error(e);
    }
  }
}

window.logViewer = new LogViewer();
