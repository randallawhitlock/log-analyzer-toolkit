/**
 * Service for handling WebSocket connections for live log tailing and replay.
 */
export class LiveLogService {
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace('http', 'ws'); // Convert http(s) to ws(s)
        this.socket = null;
        this.listeners = [];
    }

    /**
     * Connect to the tail WebSocket endpoint (watches for file appends).
     * @param {string} analysisId - Analysis UUID to tail.
     * @param {string} [filter] - Optional regex filter.
     */
    connect(analysisId, filter = null) {
        this._connectTo('/realtime/ws/logs/tail', analysisId, filter);
    }

    /**
     * Connect to the replay WebSocket endpoint (streams file with parsed output).
     * @param {string} analysisId - Analysis UUID to replay.
     * @param {string} [filter] - Optional regex filter.
     */
    connectReplay(analysisId, filter = null) {
        this._connectTo('/realtime/ws/logs/replay', analysisId, filter);
    }

    /**
     * Internal: connect to a specific WebSocket path.
     */
    _connectTo(path, analysisId, filter = null) {
        if (this.socket) {
            this.disconnect();
        }

        const params = new URLSearchParams({ analysis_id: analysisId });
        if (filter) {
            params.append('filter', filter);
        }

        const url = `${this.baseUrl}${path}?${params.toString()}`;

        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            this._notify({ type: 'status', payload: 'connected' });
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'error') {
                    this._notify({ type: 'error', payload: data.error });
                } else if (data.type === 'meta') {
                    this._notify({ type: 'meta', payload: data });
                } else if (data.type === 'complete') {
                    this._notify({ type: 'complete', payload: data });
                } else if (data.type === 'log') {
                    this._notify({ type: 'log', payload: data });
                } else if (data.error) {
                    // Legacy tail format
                    this._notify({ type: 'error', payload: data.error });
                } else {
                    // Legacy tail format (no type field)
                    this._notify({ type: 'log', payload: data });
                }
            } catch (e) {
                console.error('Error parsing WebSocket message:', e);
            }
        };

        this.socket.onerror = () => {
            this._notify({ type: 'error', payload: 'Connection error' });
        };

        this.socket.onclose = () => {
            this._notify({ type: 'status', payload: 'disconnected' });
        };
    }

    /**
     * Send a command to the replay WebSocket.
     * @param {string} cmd - Command name (play, pause, speed, jump)
     * @param {*} [value] - Optional value for the command
     */
    sendCommand(cmd, value = undefined) {
        if (this.socket && this.socket.readyState === WebSocket.OPEN) {
            const msg = { cmd };
            if (value !== undefined) {
                msg.value = value;
            }
            this.socket.send(JSON.stringify(msg));
        }
    }

    disconnect() {
        if (this.socket) {
            this.socket.close();
            this.socket = null;
        }
    }

    /**
     * Register a callback for events.
     * @param {Function} callback - Function to call with event data.
     */
    onMessage(callback) {
        this.listeners.push(callback);
    }

    /**
     * Remove a previously registered callback.
     * @param {Function} callback - The callback to remove.
     */
    offMessage(callback) {
        this.listeners = this.listeners.filter(l => l !== callback);
    }

    _notify(event) {
        this.listeners.forEach(listener => listener(event));
    }
}
