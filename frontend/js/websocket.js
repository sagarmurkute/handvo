/**
 * WebSocket client connecting to the HANDVO Python Vision & Gesture backend.
 */

class VisionWebSocketClient {
  constructor() {
    this.ws = null;
    this.isConnected = false;
    this.onFrameData = null;
    this.onStatusChange = null;
    this.reconnectTimer = null;
  }

  connect() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host || '127.0.0.1:8000';
    const wsUrl = `${protocol}//${host}/ws/vision`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        this.isConnected = true;
        if (this.onStatusChange) this.onStatusChange(true);
        console.log("Connected to HANDVO Vision WebSocket Server");
      };

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (this.onFrameData) {
            this.onFrameData(data);
          }
        } catch (e) {
          console.error("Error parsing vision packet:", e);
        }
      };

      this.ws.onclose = () => {
        this.isConnected = false;
        if (this.onStatusChange) this.onStatusChange(false);
        this._scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.warn("WebSocket error:", err);
        this.ws.close();
      };
    } catch (e) {
      console.warn("WebSocket connection failure:", e);
      this._scheduleReconnect();
    }
  }

  _scheduleReconnect() {
    if (this.reconnectTimer) clearTimeout(this.reconnectTimer);
    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, 2000);
  }

  sendCommand(command, payload = {}) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ command, ...payload }));
    }
  }
}

window.VisionWS = new VisionWebSocketClient();
