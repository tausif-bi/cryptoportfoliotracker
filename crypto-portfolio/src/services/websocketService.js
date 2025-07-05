import io from 'socket.io-client';
import { authService } from './authService';

class WebSocketService {
  constructor() {
    this.socket = null;
    this.connected = false;
    this.subscribers = new Map(); // symbol -> Set of callbacks
  }

  async connect() {
    // Only connect if logged in
    const token = await authService.getAccessToken();
    if (!token) {
      console.log('WebSocket: No auth token, skipping connection');
      return;
    }

    // Connect with auth token
    this.socket = io('http://localhost:5000', {
      query: { token },
      transports: ['websocket'],
      reconnection: true,
      reconnectionDelay: 1000,
      reconnectionAttempts: 5
    });

    // Connection events
    this.socket.on('connect', () => {
      console.log('WebSocket: Connected');
      this.connected = true;
    });

    this.socket.on('connected', (data) => {
      console.log('WebSocket: Authenticated', data);
    });

    this.socket.on('disconnect', () => {
      console.log('WebSocket: Disconnected');
      this.connected = false;
    });

    this.socket.on('error', (error) => {
      console.error('WebSocket: Error', error);
    });

    // Price update handler
    this.socket.on('price_update', (data) => {
      console.log('Price update:', data);
      this.notifySubscribers(data.symbol, data);
    });
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
    }
  }

  // Subscribe to price updates for symbols
  subscribeToPrices(symbols, callback) {
    if (!this.socket || !this.connected) {
      console.log('WebSocket: Not connected');
      return;
    }

    // Store callback for each symbol
    symbols.forEach(symbol => {
      if (!this.subscribers.has(symbol)) {
        this.subscribers.set(symbol, new Set());
      }
      this.subscribers.get(symbol).add(callback);
    });

    // Send subscription request
    this.socket.emit('subscribe_prices', { symbols });
    console.log('WebSocket: Subscribed to', symbols);
  }

  // Unsubscribe from price updates
  unsubscribeFromPrices(symbols, callback) {
    if (!this.socket) return;

    // Remove callback
    symbols.forEach(symbol => {
      const callbacks = this.subscribers.get(symbol);
      if (callbacks) {
        callbacks.delete(callback);
        if (callbacks.size === 0) {
          this.subscribers.delete(symbol);
        }
      }
    });

    // Send unsubscribe request
    this.socket.emit('unsubscribe_prices', { symbols });
  }

  // Get real-time portfolio summary
  getPortfolioSummary(callback) {
    if (!this.socket || !this.connected) {
      console.log('WebSocket: Not connected');
      return;
    }

    this.socket.emit('get_portfolio_summary');
    this.socket.once('portfolio_summary', callback);
  }

  // Notify all subscribers of a symbol
  notifySubscribers(symbol, data) {
    const callbacks = this.subscribers.get(symbol);
    if (callbacks) {
      callbacks.forEach(callback => callback(data));
    }
  }
}

export const websocketService = new WebSocketService();