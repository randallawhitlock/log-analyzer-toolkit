/**
 * Service for handling WebSocket connections for live log tailing.
 */
export class LiveLogService {
    constructor(baseUrl) {
        this.baseUrl = baseUrl.replace('http', 'ws'); // Convert http(s) to ws(s)
        this.socket = null;
        this.listeners = [];
    }

    /**
     * Connect to the WebSocket endpoint.
     * @param {string} filePath - Absolute path to the log file.
     * @param {string} [filter] - Optional regex filter.
     */
    connect(filePath, filter = null) {
        if (this.socket) {
            this.disconnect();
        }

        const params = new URLSearchParams({ file: filePath });
        if (filter) {
            params.append('filter', filter);
        }

        const url = `${this.baseUrl}/realtime/ws/logs/tail?${params.toString()}`;
        console.log(`Connecting to WebSocket: ${url}`);

        this.socket = new WebSocket(url);

        this.socket.onopen = () => {
            console.log('WebSocket connected');
            this._notify({ type: 'status', payload: 'connected' });
        };

        this.socket.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                if (data.error) {
                    this._notify({ type: 'error', payload: data.error });
                } else {
                    this._notify({ type: 'log', payload: data });
                }
            } catch (e) {
                console.error('Error parsing WebSocket message:', e);
            }
        };

        this.socket.onerror = (error) => {
            console.error('WebSocket error:', error);
            this._notify({ type: 'error', payload: 'Connection error' });
        };

        this.socket.onclose = () => {
            console.log('WebSocket disconnected');
            this._notify({ type: 'status', payload: 'disconnected' });
        };
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
