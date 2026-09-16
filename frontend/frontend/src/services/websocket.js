/**
 * WebSocket stub — Phase 3.
 * Real implementation arrives in Phase 4 (services/websocket.js + hooks/useWebSocket.js).
 * Keeps WebSocket logic out of components per AGENTS.md.
 */

// eslint-disable-next-line no-unused-vars
export function createWebSocketClient(wsUrl, { onEvent, onError, onBinary } = {}) {
  return {
    connect() {
      // stub — no real WS yet
      if (onError) onError(new Error("WebSocket not yet implemented (Phase 4)"));
      return null;
    },
    sendJson() {},
    sendAudio() {},
    disconnect() {},
    get status() {
      return "disconnected";
    },
  };
}
