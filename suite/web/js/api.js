/**
 * REST API Client for MLPMP Full Suite.
 * Handles transient CSRF token acquisition, JSON serialization, and error handling.
 */

class ApiClient {
  constructor() {
    this.csrfToken = null;
    this.initPromise = this.fetchCsrfToken();
  }

  async fetchCsrfToken() {
    try {
      const res = await fetch('/api/csrf-token', { cache: 'no-store' });
      if (res.ok) {
        const data = await res.json();
        this.csrfToken = data.csrf_token;
      }
    } catch (e) {
      console.warn('Failed fetching CSRF token:', e);
    }
  }

  async ensureReady() {
    if (!this.csrfToken) {
      await this.initPromise;
    }
  }

  async get(endpoint) {
    await this.ensureReady();
    try {
      const res = await fetch(endpoint, {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
        cache: 'no-store',
      });
      if (!res.ok) {
        throw new Error(`HTTP Error ${res.status}: ${res.statusText}`);
      }
      return await res.json();
    } catch (err) {
      window.toast.error(`Request failed: ${err.message}`);
      throw err;
    }
  }

  async post(endpoint, body = {}) {
    await this.ensureReady();
    try {
      const res = await fetch(endpoint, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          'X-Suite-Token': this.csrfToken || '',
        },
        body: JSON.stringify(body),
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || data.message || `HTTP Error ${res.status}`);
      }
      return data;
    } catch (err) {
      window.toast.error(`Operation failed: ${err.message}`);
      throw err;
    }
  }
}

window.api = new ApiClient();
