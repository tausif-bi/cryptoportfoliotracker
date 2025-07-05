import axios from 'axios';

const API_URL = 'http://localhost:5000';

class PriceService {
  constructor() {
    this.priceCache = {};
    this.updateInterval = null;
  }

  // Fetch current price from Binance public API (no auth needed)
  async fetchPriceFromBinance(symbol) {
    try {
      // Convert symbol format (BTC/USDT -> BTCUSDT)
      const binanceSymbol = symbol.replace('/', '');
      
      const response = await axios.get(
        `https://api.binance.com/api/v3/ticker/24hr?symbol=${binanceSymbol}`
      );
      
      if (response.data) {
        return {
          symbol: symbol,
          price: parseFloat(response.data.lastPrice),
          change24h: parseFloat(response.data.priceChangePercent),
          volume24h: parseFloat(response.data.quoteVolume),
          high24h: parseFloat(response.data.highPrice),
          low24h: parseFloat(response.data.lowPrice),
          timestamp: Date.now()
        };
      }
    } catch (error) {
      console.error(`Error fetching price for ${symbol}:`, error.message);
      return null;
    }
  }

  // Fetch multiple prices at once
  async fetchMultiplePrices(symbols) {
    const prices = {};
    
    // Fetch all prices in parallel
    const promises = symbols.map(async (symbol) => {
      const priceData = await this.fetchPriceFromBinance(symbol);
      if (priceData) {
        prices[symbol] = priceData;
      }
    });
    
    await Promise.all(promises);
    
    // Update cache
    this.priceCache = { ...this.priceCache, ...prices };
    
    return prices;
  }

  // Start periodic price updates
  startPriceUpdates(symbols, callback, interval = 30000) {
    // Initial fetch
    this.fetchMultiplePrices(symbols).then(prices => {
      callback(prices);
    });
    
    // Set up periodic updates
    this.updateInterval = setInterval(async () => {
      const prices = await this.fetchMultiplePrices(symbols);
      callback(prices);
    }, interval);
    
    return () => this.stopPriceUpdates();
  }

  // Stop price updates
  stopPriceUpdates() {
    if (this.updateInterval) {
      clearInterval(this.updateInterval);
      this.updateInterval = null;
    }
  }

  // Get cached price
  getCachedPrice(symbol) {
    return this.priceCache[symbol] || null;
  }
}

export default new PriceService();