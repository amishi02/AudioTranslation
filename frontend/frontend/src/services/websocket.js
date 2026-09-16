/**
 * WebSocket client — Phase 4 real implementation.
 * Keeps WebSocket logic out of components per AGENTS.md.
 */
export function createWebSocketClient(wsUrl, { onEvent, onError, onBinary } = {}) {
  let ws = null;
  let status = "disconnected";

  const client = {
    connect() {
      if (ws && ws.readyState === WebSocket.OPEN) return ws;
      status = "connecting";
      ws = new WebSocket(wsUrl);
      ws.binaryType = "arraybuffer";

      ws.onopen = () => {
        status = "connected";
      };

      ws.onmessage = async (event) => {
        const data = event.data;
        // Binary: ArrayBuffer or Blob
        if (data instanceof ArrayBuffer) {
          if (onBinary) onBinary(data);
          return;
        }
        if (data instanceof Blob) {
          if (onBinary) {
            const buf = await data.arrayBuffer();
            onBinary(buf);
          }
          return;
        }
        // JSON text
        if (typeof data === "string") {
          try {
            const json = JSON.parse(data);
            if (onEvent) onEvent(json);
          } catch (e) {
            if (onError) onError(e);
          }
          return;
        }
      };

      ws.onerror = () => {
        status = "error";
        if (onError) onError(new Error("WebSocket error"));
      };

      ws.onclose = () => {
        status = "disconnected";
      };

      return ws;
    },

    sendJson(obj) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify(obj));
      }
    },

    sendAudio(buffer) {
      if (ws && ws.readyState === WebSocket.OPEN) {
        // buffer is ArrayBuffer or Uint8Array
        ws.send(buffer);
      }
    },

    disconnect() {
      if (ws) {
        try {
          ws.close();
        } catch {
          // ignore close error
        }
        ws = null;
        status = "disconnected";
      }
    },

    get status() {
      return status;
    },

    get ws() {
      return ws;
    },
  };

  return client;
}
