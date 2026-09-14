/**
 * Bottom-Right Toast Notification Manager for MLPMP Full Suite.
 * Displays clean, stackable notifications for user actions and system events.
 */

class ToastManager {
  constructor() {
    this.container = document.getElementById('toast-container');
    if (!this.container) {
      this.container = document.createElement('div');
      this.container.id = 'toast-container';
      this.container.className = 'toast-container';
      document.body.appendChild(this.container);
    }
  }

  show(type, message, duration = 4500) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0];

    const content = document.createElement('div');
    content.className = 'toast-content';

    const timeEl = document.createElement('div');
    timeEl.className = 'toast-time';
    timeEl.textContent = `[${timeStr}]`;

    const msgEl = document.createElement('div');
    msgEl.className = 'toast-msg';
    msgEl.textContent = message;

    content.appendChild(timeEl);
    content.appendChild(msgEl);

    const closeBtn = document.createElement('button');
    closeBtn.className = 'toast-close';
    closeBtn.textContent = '×';
    closeBtn.onclick = () => toast.remove();

    toast.appendChild(content);
    toast.appendChild(closeBtn);

    this.container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        if (toast.parentElement) {
          toast.remove();
        }
      }, duration);
    }
  }

  success(msg) {
    this.show('success', msg);
  }

  error(msg) {
    this.show('error', msg, 6000);
  }

  warn(msg) {
    this.show('warn', msg, 5000);
  }

  info(msg) {
    this.show('info', msg);
  }
}

window.toast = new ToastManager();
