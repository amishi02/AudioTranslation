/**
 * Centralized frontend environment.
 * See frontend/frontend/.env.example and AGENTS.md.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const WS_URL =
  import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/v1/translate";

/**
 * Derive WS URL from API base when VITE_WS_URL is not set.
 * Upgrades http:// -> ws://, https:// -> wss://.
 */
export function getWsUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  try {
    const url = new URL(API_BASE_URL);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = "/ws/v1/translate";
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return WS_URL;
  }
}
