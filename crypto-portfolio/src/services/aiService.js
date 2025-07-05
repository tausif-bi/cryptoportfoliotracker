import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authService } from './authService';

class AIService {
  constructor() {
    // Use environment variable for backend URL, with fallback for backward compatibility
    this.baseURL = process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:5000/api';
    
    this.axios = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Set backend URL (for production)
  setBackendURL(url) {
    this.baseURL = url;
    this.axios = axios.create({
      baseURL: this.baseURL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
  }

  // Helper method to make authenticated requests
  async makeAuthenticatedRequest(endpoint, data = {}, method = 'POST') {
    try {
      const url = `${this.baseURL}${endpoint}`;
      
      if (authService.isLoggedIn()) {
        const response = await authService.authenticatedRequest(url, {
          method,
          headers: {
            'Content-Type': 'application/json',
          },
          body: method !== 'GET' ? JSON.stringify(data) : undefined,
        });
        return await response.json();
      } else {
        // For backward compatibility - but most endpoints now require auth
        throw new Error('Authentication required. Please log in.');
      }
    } catch (error) {
      console.error('AI Service request error:', error);
      throw error;
    }
  }

  // Analyze portfolio and get insights
  async analyzePortfolio(holdings, prices) {
    try {
      const response = await this.makeAuthenticatedRequest('/analyze-portfolio', {
        holdings,
        prices,
      });

      if (response.success) {
        // Cache the analysis
        await this.cacheAnalysis(response.analysis);
        return response.analysis;
      }
      
      throw new Error('Analysis failed');
    } catch (error) {
      console.error('Error analyzing portfolio:', error);
      
      // Return cached analysis if available
      const cached = await this.getCachedAnalysis();
      if (cached) {
        return cached;
      }
      
      // Return default analysis if API fails
      return this.getDefaultAnalysis(holdings);
    }
  }

  // Get price predictions for a symbol
  async getPricePrediction(symbol, exchange = 'binance') {
    try {
      const response = await this.makeAuthenticatedRequest('/predict-price', {
        symbol,
        exchange,
      });

      if (response.success) {
        return response.prediction;
      }
      
      throw new Error('Prediction failed');
    } catch (error) {
      console.error('Error getting prediction:', error);
      return null;
    }
  }

  // Get market analysis
  async getMarketAnalysis() {
    try {
      const response = await this.axios.get('/market-analysis');

      if (response.data.success) {
        return response.data;
      }
      
      throw new Error('Market analysis failed');
    } catch (error) {
      console.error('Error getting market analysis:', error);
      return null;
    }
  }

  // Get rebalancing suggestions
  async getRebalancingSuggestions(holdings, targetAllocations = null) {
    try {
      const response = await this.axios.post('/rebalancing-suggestions', {
        holdings,
        target_allocations: targetAllocations,
      });

      if (response.data.success) {
        return response.data.suggestions;
      }
      
      throw new Error('Rebalancing suggestions failed');
    } catch (error) {
      console.error('Error getting rebalancing suggestions:', error);
      return [];
    }
  }

  // Cache analysis results
  async cacheAnalysis(analysis) {
    try {
      const cacheData = {
        analysis,
        timestamp: new Date().toISOString(),
      };
      await AsyncStorage.setItem('portfolio_analysis_cache', JSON.stringify(cacheData));
    } catch (error) {
      console.error('Error caching analysis:', error);
    }
  }

  // Get cached analysis
  async getCachedAnalysis() {
    try {
      const cached = await AsyncStorage.getItem('portfolio_analysis_cache');
      if (cached) {
        const data = JSON.parse(cached);
        // Check if cache is less than 1 hour old
        const cacheAge = new Date() - new Date(data.timestamp);
        if (cacheAge < 3600000) { // 1 hour in milliseconds
          return data.analysis;
        }
      }
      return null;
    } catch (error) {
      console.error('Error getting cached analysis:', error);
      return null;
    }
  }

  // Get default analysis when API is unavailable
  getDefaultAnalysis(holdings) {
    const insights = [];
    const recommendations = [];
    
    // Basic analysis based on holdings
    const totalValue = holdings.reduce((sum, h) => sum + h.usdValue, 0);
    const maxAllocation = Math.max(...holdings.map(h => h.allocation));
    
    // Concentration analysis
    if (maxAllocation > 50) {
      insights.push({
        type: 'warning',
        message: `High concentration in single asset (${maxAllocation.toFixed(1)}%)`,
        severity: 'high',
      });
      recommendations.push('Consider diversifying your portfolio to reduce risk');
    }
    
    // Number of assets
    if (holdings.length < 5) {
      insights.push({
        type: 'info',
        message: 'Low diversification - only ' + holdings.length + ' assets',
        severity: 'medium',
      });
      recommendations.push('Add more assets to improve diversification');
    }
    
    // Performance analysis
    const winners = holdings.filter(h => h.change24h > 0).length;
    const losers = holdings.filter(h => h.change24h < 0).length;
    
    insights.push({
      type: 'info',
      message: `${winners} gaining vs ${losers} losing assets today`,
      severity: 'info',
    });
    
    return {
      insights,
      recommendations,
      risk_score: maxAllocation > 50 ? 75 : 50,
      diversity_score: Math.min(holdings.length * 10, 100),
    };
  }

  // Generate AI trading signals
  async getTradingSignals(holdings) {
    const signals = [];
    
    for (const holding of holdings) {
      const prediction = await this.getPricePrediction(`${holding.coin}/USDT`);
      
      if (prediction && prediction.signal) {
        signals.push({
          coin: holding.coin,
          signal: prediction.signal,
          confidence: prediction.confidence,
          rsi: prediction.rsi,
          trend: prediction.trend,
        });
      }
    }
    
    return signals;
  }

  // Check if backend is available
  async checkBackendHealth() {
    try {
      const response = await this.axios.get('/health', { timeout: 5000 });
      return response.data.status === 'healthy';
    } catch (error) {
      console.error('Backend health check failed:', error);
      return false;
    }
  }
}

export default new AIService();