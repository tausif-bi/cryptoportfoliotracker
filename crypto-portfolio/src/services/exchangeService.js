import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { authService } from './authService';

class ExchangeService {
  constructor() {
    // Use environment variable for backend URL, with fallback
    this.baseURL = process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:5000/api';
    
    this.exchangeName = null;
    this.apiKey = null;
    this.apiSecret = null;
  }

  // Helper method to make authenticated requests
  async makeAuthenticatedRequest(url, data = {}, method = 'POST') {
    try {
      const fullUrl = url.startsWith('http') ? url : `${this.baseURL}${url}`;
      
      // Try authenticated request first
      if (authService.isLoggedIn()) {
        const response = await authService.authenticatedRequest(fullUrl, {
          method,
          headers: {
            'Content-Type': 'application/json',
          },
          body: method !== 'GET' ? JSON.stringify(data) : undefined,
        });
        return await response.json();
      } else {
        // Fallback to regular axios request for backward compatibility
        const response = await axios({
          method: method.toLowerCase(),
          url: fullUrl,
          data: method !== 'GET' ? data : undefined,
        });
        return response.data;
      }
    } catch (error) {
      console.error('Request error:', error);
      throw error;
    }
  }

  // Initialize exchange with API credentials
  async initializeExchange(exchangeName, apiKey, apiSecret, password = null) {
    try {
      // Save credentials locally
      const credentials = {
        exchangeName,
        apiKey,
        apiSecret,
        password,
      };
      
      await AsyncStorage.setItem('exchange_credentials', JSON.stringify(credentials));
      
      this.exchangeName = exchangeName;
      this.apiKey = apiKey;
      this.apiSecret = apiSecret;
      
      // Verify credentials with backend
      const response = await this.makeAuthenticatedRequest('/verify-exchange', {
        exchangeName,
        apiKey,
        apiSecret,
        password: password || undefined,  // Don't send null password
      });
      
      if (response.success) {
        return true;
      } else {
        throw new Error('Invalid credentials');
      }
    } catch (error) {
      console.error('Error initializing exchange:', error);
      // If backend is not available, save credentials anyway
      if (error.code === 'ECONNREFUSED' || error.message.includes('Network')) {
        return true; // Allow offline mode
      }
      throw error;
    }
  }

  // Load saved credentials
  async loadSavedCredentials() {
    try {
      const saved = await AsyncStorage.getItem('exchange_credentials');
      if (saved) {
        const credentials = JSON.parse(saved);
        this.exchangeName = credentials.exchangeName;
        this.apiKey = credentials.apiKey;
        this.apiSecret = credentials.apiSecret;
        return true;
      }
      return false;
    } catch (error) {
      console.error('Error loading credentials:', error);
      return false;
    }
  }

  // Fetch account balance from backend
  async fetchBalance() {
    try {
      const credentials = await this.getCredentials();
      if (!credentials) {
        throw new Error('No exchange configured');
      }

      const response = await this.makeAuthenticatedRequest('/fetch-balance', credentials);
      
      if (response.success) {
        return response.balance;
      }
      
      throw new Error('Failed to fetch balance');
    } catch (error) {
      console.error('Error fetching balance:', error);
      // Return mock data if backend is unavailable
      return this.getMockBalance();
    }
  }

  // Fetch trades history from backend
  async fetchTrades(symbol = null, since = null, limit = 50) {
    try {
      const credentials = await this.getCredentials();
      if (!credentials) {
        throw new Error('No exchange configured');
      }

      // Check if it's demo mode
      if (credentials.exchangeName === 'demo') {
        return this.getDemoTrades(limit);
      }

      const response = await axios.post(`${this.baseURL}/fetch-trades`, {
        ...credentials,
        symbol,
        since,
        limit,  // This will now properly pass the limit parameter
      });
      
      if (response.data.success) {
        return response.data.trades;
      }
      
      throw new Error('Failed to fetch trades');
    } catch (error) {
      console.error('Error fetching trades:', error);
      // Return mock data if backend is unavailable
      return this.getMockTrades();
    }
  }

  // Calculate portfolio statistics
  async calculatePortfolioStats() {
    try {
      const credentials = await this.getCredentials();
      if (!credentials) {
        // Return mock data if no exchange configured
        return this.getMockPortfolioStats();
      }

      // Check if it's demo mode
      if (credentials.exchangeName === 'demo') {
        return this.getDemoPortfolioStats();
      }

      const response = await axios.post(`${this.baseURL}/portfolio-stats`, credentials);
      
      if (response.data.success) {
        return response.data.stats;
      }
      
      throw new Error('Failed to calculate stats');
    } catch (error) {
      console.error('Error calculating portfolio stats:', error);
      // Return mock data if backend is unavailable
      return this.getMockPortfolioStats();
    }
  }

  // ============ P&L CALCULATION METHODS ============

  // Calculate realized P&L using FIFO method
  calculateRealizedPnL(trades) {
    const assetTrades = {};
    let totalRealizedPnL = 0;
    let tradeDetails = [];
    
    // Group trades by asset
    trades.forEach(trade => {
      const amount = trade?.quantity || trade?.amount || 0;
      const price = trade?.price || 0;
      const side = trade?.side;
      const cost = trade?.value || trade?.cost || (price * amount);
      
      // Infer symbol for demo data
      let symbol = trade?.symbol;
      if (!symbol) {
        if (price > 40000) symbol = 'BTC/USDT';
        else if (price > 2000 && price < 5000) symbol = 'ETH/USDT';
        else if (price > 100 && price < 1000) symbol = 'BNB/USDT';
        else if (price > 20 && price < 200) symbol = 'SOL/USDT';
        else symbol = 'ADA/USDT';
      }
      
      const asset = symbol.split('/')[0];
      
      if (!assetTrades[asset]) {
        assetTrades[asset] = { buys: [], sells: [] };
      }
      
      if (side === 'buy') {
        assetTrades[asset].buys.push({ 
          amount, 
          price, 
          cost, 
          timestamp: trade.timestamp || Date.now(),
          id: trade.trade_id || trade.id
        });
      } else if (side === 'sell') {
        assetTrades[asset].sells.push({ 
          amount, 
          price, 
          cost, 
          timestamp: trade.timestamp || Date.now(),
          id: trade.trade_id || trade.id
        });
      }
    });
    
    // Calculate P&L for each asset using FIFO
    Object.keys(assetTrades).forEach(asset => {
      const data = assetTrades[asset];
      let remainingBuys = [...data.buys].sort((a, b) => a.timestamp - b.timestamp);
      
      data.sells.forEach(sell => {
        let sellAmount = sell.amount;
        
        while (sellAmount > 0 && remainingBuys.length > 0) {
          const buy = remainingBuys[0];
          const tradeAmount = Math.min(sellAmount, buy.amount);
          const profit = (sell.price - buy.price) * tradeAmount;
          
          totalRealizedPnL += profit;
          
          tradeDetails.push({
            asset,
            buyPrice: buy.price,
            sellPrice: sell.price,
            amount: tradeAmount,
            profit,
            buyDate: new Date(buy.timestamp),
            sellDate: new Date(sell.timestamp)
          });
          
          buy.amount -= tradeAmount;
          sellAmount -= tradeAmount;
          
          if (buy.amount <= 0) {
            remainingBuys.shift();
          }
        }
      });
    });
    
    return {
      totalRealizedPnL,
      tradeDetails,
      assetBreakdown: assetTrades
    };
  }

  // Calculate comprehensive trade statistics
  calculateTradeStats(trades) {
    const pnlResult = this.calculateRealizedPnL(trades);
    const tradeDetails = pnlResult.tradeDetails;
    
    let winningTrades = 0;
    let losingTrades = 0;
    let bestTrade = null;
    let worstTrade = null;
    let totalProfit = 0;
    let totalLoss = 0;
    
    tradeDetails.forEach(trade => {
      if (trade.profit > 0) {
        winningTrades++;
        totalProfit += trade.profit;
        if (!bestTrade || trade.profit > bestTrade.profit) {
          bestTrade = trade;
        }
      } else {
        losingTrades++;
        totalLoss += Math.abs(trade.profit);
        if (!worstTrade || trade.profit < worstTrade.profit) {
          worstTrade = trade;
        }
      }
    });
    
    const totalTrades = winningTrades + losingTrades;
    const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0;
    const avgWin = winningTrades > 0 ? totalProfit / winningTrades : 0;
    const avgLoss = losingTrades > 0 ? totalLoss / losingTrades : 0;
    const profitFactor = totalLoss > 0 ? totalProfit / totalLoss : 0;
    
    return {
      totalTrades,
      winningTrades,
      losingTrades,
      winRate,
      bestTrade,
      worstTrade,
      totalProfit,
      totalLoss,
      avgWin,
      avgLoss,
      profitFactor,
      totalRealizedPnL: pnlResult.totalRealizedPnL
    };
  }

  // Get P&L by time period
  getPnLByPeriod(trades, period = '1m') {
    const now = new Date();
    let startDate;
    
    switch (period) {
      case '1d':
        startDate = new Date(now.getTime() - 24 * 60 * 60 * 1000);
        break;
      case '1w':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case '1m':
        startDate = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
        break;
      case '3m':
        startDate = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
        break;
      case '6m':
        startDate = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
        break;
      case '1y':
        startDate = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
        break;
      default:
        startDate = new Date(0); // All time
    }
    
    const filteredTrades = trades.filter(trade => {
      const tradeDate = new Date(trade.timestamp || trade.datetime);
      return tradeDate >= startDate;
    });
    
    return this.calculateTradeStats(filteredTrades);
  }

  // Get complete P&L analysis
  async getCompletePnLAnalysis() {
    try {
      const trades = await this.fetchTrades(null, null, 1000);
      const stats = this.calculateTradeStats(trades);
      
      // Calculate P&L by asset
      const assetPnL = [];
      const assetGroups = {};
      
      trades.forEach(trade => {
        const amount = trade?.quantity || trade?.amount || 0;
        const price = trade?.price || 0;
        const side = trade?.side;
        
        let symbol = trade?.symbol;
        if (!symbol) {
          if (price > 40000) symbol = 'BTC/USDT';
          else if (price > 2000 && price < 5000) symbol = 'ETH/USDT';
          else if (price > 100 && price < 1000) symbol = 'BNB/USDT';
          else if (price > 20 && price < 200) symbol = 'SOL/USDT';
          else symbol = 'ADA/USDT';
        }
        
        const asset = symbol.split('/')[0];
        
        if (!assetGroups[asset]) {
          assetGroups[asset] = { trades: [], totalVolume: 0 };
        }
        
        assetGroups[asset].trades.push(trade);
        assetGroups[asset].totalVolume += (price * amount);
      });
      
      Object.keys(assetGroups).forEach(asset => {
        const assetTrades = assetGroups[asset].trades;
        const assetStats = this.calculateTradeStats(assetTrades);
        
        assetPnL.push({
          asset,
          symbol: `${asset}/USDT`,
          realizedPnL: assetStats.totalRealizedPnL,
          trades: assetTrades.length,
          volume: assetGroups[asset].totalVolume,
          winRate: assetStats.winRate
        });
      });
      
      return {
        ...stats,
        assetPnL: assetPnL.sort((a, b) => b.realizedPnL - a.realizedPnL),
        monthlyPnL: this.getPnLByPeriod(trades, '1m'),
        weeklyPnL: this.getPnLByPeriod(trades, '1w'),
        dailyPnL: this.getPnLByPeriod(trades, '1d')
      };
    } catch (error) {
      console.error('Error getting complete P&L analysis:', error);
      throw error;
    }
  }

  // ============ DEMO DATA METHODS ============

  // Generate demo trades (810 trades like your JSON file)
  getDemoTrades(limit = 810) {
    const demoTrades = [];
    const symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT'];
    const sides = ['buy', 'sell'];
    
    for (let i = 1; i <= limit; i++) {
      const symbol = symbols[Math.floor(Math.random() * symbols.length)];
      const side = sides[Math.floor(Math.random() * sides.length)];
      
      let price, quantity, value;
      
      // Set realistic prices based on symbol
      switch (symbol) {
        case 'BTC/USDT':
          price = 42000 + (Math.random() * 5000);
          quantity = 0.001 + (Math.random() * 0.1);
          break;
        case 'ETH/USDT':
          price = 2500 + (Math.random() * 500);
          quantity = 0.1 + (Math.random() * 2);
          break;
        case 'BNB/USDT':
          price = 300 + (Math.random() * 100);
          quantity = 1 + (Math.random() * 10);
          break;
        case 'SOL/USDT':
          price = 55 + (Math.random() * 50);
          quantity = 5 + (Math.random() * 20);
          break;
        case 'ADA/USDT':
          price = 0.5 + (Math.random() * 0.5);
          quantity = 100 + (Math.random() * 500);
          break;
      }
      
      value = price * quantity;
      
      demoTrades.push({
        trade_id: i,
        timestamp: Date.now() - (Math.random() * 30 * 24 * 60 * 60 * 1000), // Last 30 days
        symbol: symbol,
        side: side,
        price: price,
        quantity: quantity,
        value: value,
        price_change_pct: (Math.random() - 0.5) * 10 // -5% to +5%
      });
    }
    
    return demoTrades.sort((a, b) => b.timestamp - a.timestamp);
  }

  // Demo portfolio stats
  getDemoPortfolioStats() {
    return {
      holdings: [
        {
          symbol: 'BTC',
          balance: 2.15,
          usdValue: 95250.50,
          change24h: 2.45,
          percentage: 42.3
        },
        {
          symbol: 'ETH',
          balance: 15.8,
          usdValue: 38703.02,
          change24h: -1.2,
          percentage: 17.2
        },
        {
          symbol: 'BNB',
          balance: 125.5,
          usdValue: 38200.15,
          change24h: 3.1,
          percentage: 16.9
        },
        {
          symbol: 'SOL',
          balance: 890.2,
          usdValue: 55420.45,
          change24h: -0.8,
          percentage: 24.6
        },
        {
          symbol: 'ADA',
          balance: 12500,
          usdValue: 7890.25,
          change24h: 1.9,
          percentage: 3.5
        }
      ],
      totalValue: 245562.85,
      numberOfAssets: 5
    };
  }

  // Get saved credentials
  async getCredentials() {
    try {
      const saved = await AsyncStorage.getItem('exchange_credentials');
      return saved ? JSON.parse(saved) : null;
    } catch (error) {
      console.error('Error getting credentials:', error);
      return null;
    }
  }

  // Update backend URL
  setBackendURL(url) {
    this.baseURL = url;
  }

  // Get supported exchanges
  static getSupportedExchanges() {
    return [
      'demo',         // Add demo mode at the top
      'binance',
      'coinbase',
      'kraken',
      'bitfinex',
      'huobi',
      'kucoin',
      'okex',
      'bybit',
      'ftx',
      'gate',
      'lbank2',
    ];
  }

  // Mock data methods for development/offline mode
  getMockBalance() {
    return {
      BTC: { free: 1.5, used: 0, total: 1.5 },
      ETH: { free: 15, used: 0, total: 15 },
      BNB: { free: 25, used: 0, total: 25 },
      SOL: { free: 100, used: 0, total: 100 },
      ADA: { free: 5000, used: 0, total: 5000 },
      DOT: { free: 200, used: 0, total: 200 },
      MATIC: { free: 2000, used: 0, total: 2000 },
      USDT: { free: 5000, used: 0, total: 5000 },
    };
  }

  getMockTrades() {
    return [
      {
        id: '1',
        symbol: 'BTC/USDT',
        side: 'buy',
        price: 42000,
        amount: 0.5,
        cost: 21000,
        fee: { cost: 21, currency: 'USDT' },
        timestamp: Date.now() - 3600000,
        datetime: new Date(Date.now() - 3600000).toISOString(),
      },
      {
        id: '2',
        symbol: 'ETH/USDT',
        side: 'sell',
        price: 2500,
        amount: 5,
        cost: 12500,
        fee: { cost: 12.5, currency: 'USDT' },
        timestamp: Date.now() - 7200000,
        datetime: new Date(Date.now() - 7200000).toISOString(),
      },
      {
        id: '3',
        symbol: 'BNB/USDT',
        side: 'buy',
        price: 300,
        amount: 10,
        cost: 3000,
        fee: { cost: 3, currency: 'USDT' },
        timestamp: Date.now() - 10800000,
        datetime: new Date(Date.now() - 10800000).toISOString(),
      },
    ];
  }

  getMockPortfolioStats() {
    const holdings = [
      { coin: 'BTC', amount: 1.5, usdValue: 65000, allocation: 51.8, change24h: 2.3, price: 43333 },
      { coin: 'ETH', amount: 15, usdValue: 37500, allocation: 29.9, change24h: -1.2, price: 2500 },
      { coin: 'BNB', amount: 25, usdValue: 7500, allocation: 6.0, change24h: 0.8, price: 300 },
      { coin: 'SOL', amount: 100, usdValue: 6000, allocation: 4.8, change24h: 5.4, price: 60 },
      { coin: 'ADA', amount: 5000, usdValue: 3500, allocation: 2.8, change24h: -3.2, price: 0.7 },
      { coin: 'DOT', amount: 200, usdValue: 3000, allocation: 2.4, change24h: 1.5, price: 15 },
      { coin: 'MATIC', amount: 2000, usdValue: 2932.56, allocation: 2.3, change24h: -0.5, price: 1.47 },
    ];

    const totalValue = holdings.reduce((sum, h) => sum + h.usdValue, 0);

    return {
      totalValue,
      holdings,
      numberOfAssets: holdings.length,
    };
  }
}

export default new ExchangeService();