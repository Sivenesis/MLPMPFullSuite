/**
 * Debug Log Console & Real-Time Log Viewer for MLPMP Full Suite.
 */

class LogViewer {
  constructor() {
    this.modal = document.getElementById('log-modal');
    this.container = document.getElementById('log-entries');
    this.autoScrollCheckbox = document.getElementById('log-autoscroll');
    this.pollInterval = null;
    this._lastLogsSignature = null;
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

      // Avoid re-rendering DOM if logs haven't changed (preserves user selection / scroll)
      const count = data.logs.length;
      const lastEntry = count > 0 ? data.logs[count - 1] : null;
      const signature = `${count}:${lastEntry ? lastEntry.timestamp + '|' + lastEntry.message : ''}`;
      if (signature === this._lastLogsSignature) {
        return;
      }
      this._lastLogsSignature = signature;

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

  selectAll() {
    if (!this.container) return;

    // Highlight / select all log text in container
    const range = document.createRange();
    range.selectNodeContents(this.container);
    const selection = window.getSelection();
    if (selection) {
      selection.removeAllRanges();
      selection.addRange(range);
    }

    // Also attempt copying to clipboard if supported
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(this.container.innerText).catch(() => {});
      }
    } catch (e) {
      // Ignore clipboard permission errors; selection range is already active
    }

    window.toast.info('All logs selected (Ctrl+C to copy).');
  }

  async saveToFile() {
    try {
      const res = await window.api.post('/api/logs/save', {});
      if (res && res.success) {
        window.toast.success(res.message || 'Saved to log.txt near start.bat!');
        // Refresh to show the save event logged
        this._lastLogsSignature = null;
        this.refresh();
      } else {
        window.toast.error(res?.error || 'Failed to save log.txt');
      }
    } catch (e) {
      console.error('Failed saving logs to log.txt:', e);
    }
  }

  async clear() {
    try {
      await window.api.post('/api/logs/clear');
      this._lastLogsSignature = null;
      this.refresh();
      window.toast.info('Debug log cleared.');
    } catch (e) {
      console.error(e);
    }
  }
}

window.logViewer = new LogViewer();
