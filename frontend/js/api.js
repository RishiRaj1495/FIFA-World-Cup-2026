/**
 * Thin API client. Every call to the backend goes through here so the
 * base URL, error handling, and JSON parsing live in exactly one place.
 */
const API = (() => {
  const BASE_URL = window.FAN_CONCIERGE_API_BASE || "http://localhost:8000";

  async function request(path, options = {}) {
    const response = await fetch(`${BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const body = await response.json();
        detail = body.detail ? JSON.stringify(body.detail) : detail;
      } catch (_) {
        /* response had no JSON body; keep statusText */
      }
      throw new Error(`Request to ${path} failed (${response.status}): ${detail}`);
    }
    return response.json();
  }

  return {
    sendChatMessage(payload) {
      return request("/api/chat", {
        method: "POST",
        body: JSON.stringify(payload),
      });
    },
    getCrowdStatus() {
      return request("/api/crowd-status");
    },
    getAccessibilityInfo(need) {
      return request(`/api/accessibility-info?need=${encodeURIComponent(need)}`);
    },
  };
})();
