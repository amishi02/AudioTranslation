/**
 * Centralized frontend environment.
 * See frontend/frontend/.env.example and AGENTS.md.
 */

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export const WS_URL =
  import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/v1/translate";

// Env-configurable paths — defaults match backend defaults
export const API_V1_PREFIX = import.meta.env.VITE_API_V1_PREFIX || "/api/v1";
export const HEALTH_PATH = import.meta.env.VITE_HEALTH_PATH || "/health";
export const HEALTH_READY_PATH =
  import.meta.env.VITE_HEALTH_READY_PATH || "/health/ready";
export const CAPABILITIES_PATH =
  import.meta.env.VITE_CAPABILITIES_PATH || "/api/v1/capabilities";
export const WS_V1_PATH =
  import.meta.env.VITE_WS_V1_PATH || "/ws/v1/translate";

export const APP_TITLE =
  import.meta.env.VITE_APP_TITLE || "Real-Time Audio Translation";

/**
 * Derive WS URL from API base when VITE_WS_URL is not set.
 * Upgrades http:// -> ws://, https:// -> wss://.
 */
export function getWsUrl() {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  try {
    const url = new URL(API_BASE_URL);
    url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
    url.pathname = WS_V1_PATH;
    url.search = "";
    url.hash = "";
    return url.toString();
  } catch {
    return WS_URL;
  }
}
