/**
 * API helpers — health + capabilities.
 * Calls FastAPI GET /health, /health/ready, /api/v1/capabilities
 * and normalizes ErrorResponse envelope.
 */
import {
  API_BASE_URL,
  CAPABILITIES_PATH,
  HEALTH_PATH,
  HEALTH_READY_PATH,
} from "../config/environment.js";

async function fetchJson(path) {
  const url = `${API_BASE_URL}${path}`;
  let res;
  try {
    res = await fetch(url);
  } catch (e) {
    throw new Error(`Unable to connect to translation service: ${e.message}`, { cause: e });
  }
  let data;
  try {
    data = await res.json();
  } catch {
    throw new Error(`Invalid response from ${path}`);
  }
  if (!res.ok) {
    // Backend returns ErrorResponse { error, code, message }
    const msg = data?.message || data?.error || `Request failed: ${res.status}`;
    const err = new Error(msg);
    err.code = data?.code || "UNKNOWN";
    err.status = res.status;
    err.details = data;
    throw err;
  }
  return data;
}

export function fetchHealth() {
  return fetchJson(HEALTH_PATH);
}

export function fetchReady() {
  return fetchJson(HEALTH_READY_PATH);
}

export function fetchCapabilities() {
  return fetchJson(CAPABILITIES_PATH);
}
