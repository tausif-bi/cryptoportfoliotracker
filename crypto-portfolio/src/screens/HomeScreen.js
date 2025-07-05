import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import exchangeService from '../services/exchangeService';
import aiService from '../services/aiService';
import { useTheme } from '../theme/ThemeContext';
import { useRealTimePrices } from '../hooks/useRealTimePrices';

const HomeScreen = () => {
  const { theme } = useTheme();
  const [portfolioValue, setPortfolioValue] = useState(0);
  const [dailyChange, setDailyChange] = useState(0);
  const [dailyChangePercent, setDailyChangePercent] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [trades, setTrades] = useState([]);
  const [holdings, setHoldings] = useState([]);
  const [aiInsight, setAiInsight] = useState('');
  
  // Get real-time prices for portfolio holdings
  const symbols = holdings.map(h => `${h.coin || h.symbol}/USDT`).filter(s => s !== '/USDT');
  const { prices: realtimePrices, connected } = useRealTimePrices(symbols);

  useEffect(() => {
    loadPortfolioData();
  }, []);

  // Reload data when screen comes into focus
  useFocusEffect(
    React.useCallback(() => {
      loadPortfolioData();
    }, [])
  );

  // Recalculate portfolio value with real-time prices
  useEffect(() => {
    if (connected && holdings.length > 0 && Object.keys(realtimePrices).length > 0) {
      let totalValue = 0;
      let totalChange = 0;
      
      holdings.forEach(holding => {
        const coinName = holding.coin || holding.symbol || 'Unknown';
        const amount = holding.amount || holding.balance || 0;
        const symbol = `${coinName}/USDT`;
        const realtimeData = realtimePrices[symbol];
        
        if (realtimeData) {
          const value = realtimeData.price * amount;
          totalValue += value;
          
          // Calculate change based on real-time data
          const change = (value * realtimeData.change24h) / 100;
          totalChange += change;
        } else {
          // Fall back to cached data if no real-time price
          totalValue += holding.usdValue || 0;
          const change = (holding.usdValue * (holding.change24h || 0)) / 100;
          totalChange += change;
        }
      });
      
      setPortfolioValue(totalValue);
      setDailyChange(totalChange);
      setDailyChangePercent((totalChange / totalValue) * 100);
    }
  }, [realtimePrices, holdings, connected]);

  const loadPortfolioData = async () => {
    try {
      console.log('Loading portfolio data...');
      
      // Check if exchange is connected
      const hasCredentials = await exchangeService.loadSavedCredentials();
      console.log('Has credentials:', hasCredentials);
      
      if (hasCredentials) {
        // Fetch real portfolio data
        console.log('Fetching portfolio stats...');
        const stats = await exchangeService.calculatePortfolioStats();
        console.log('Portfolio stats:', stats);
        
        if (stats && stats.totalValue) {
          setPortfolioValue(stats.totalValue);
          setHoldings(stats.holdings);
          
          // Calculate daily change (you might want to store previous day's value)
          // For now, we'll calculate based on the 24h changes of holdings
          let totalChange = 0;
          stats.holdings.forEach(holding => {
            const change = (holding.usdValue * holding.change24h) / 100;
            totalChange += change;
          });
          
          setDailyChange(totalChange);
          setDailyChangePercent((totalChange / stats.totalValue) * 100);
        }
        
        // Fetch recent trades
        console.log('Fetching trades...');
        const recentTrades = await exchangeService.fetchTrades(null, null, 5);
        console.log('Recent trades:', recentTrades);
        setTrades(recentTrades.slice(0, 2)); // Show only 2 most recent
        
        // Get AI insights
        // Get AI insights - handle errors gracefully
      try {
        const analysis = await aiService.analyzePortfolio(stats.holdings, {});
        if (analysis && analysis.insights && analysis.insights.length > 0) {
          setAiInsight(analysis.insights[0].message);
        }
      } catch (error) {
        console.log('AI service unavailable, using fallback insight');
        setAiInsight('Your portfolio shows strong momentum. Consider rebalancing for optimal performance.');
      }
      } else {
        console.log('No credentials found, using mock data');
        // Use mock data if no exchange connected
        setPortfolioValue(125432.56);
        setDailyChange(2341.23);
        setDailyChangePercent(1.87);
      }
    } catch (error) {
      console.error('Error loading portfolio data:', error);
      console.error('Error details:', error.response?.data);
      // Use mock data on error
      setPortfolioValue(125432.56);
      setDailyChange(2341.23);
      setDailyChangePercent(1.87);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadPortfolioData();
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  // Create dynamic styles based on theme
  const styles = createStyles(theme);

  if (isLoading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#00D4FF" />
      </View>
    );
  }

  return (
    <ScrollView 
      style={styles.container}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={onRefresh}
          tintColor="#00D4FF"
        />
      }
    >
      {/* Header */}
      <LinearGradient
        colors={[theme.colors.background, theme.colors.surface]}
        style={styles.header}
      >
        <Text style={styles.greeting}>Good morning!</Text>
        <Text style={styles.date}>{new Date().toLocaleDateString('en-US', { 
          weekday: 'long', 
          year: 'numeric', 
          month: 'long', 
          day: 'numeric' 
        })}</Text>
      </LinearGradient>

      {/* Portfolio Value Card */}
      <LinearGradient
        colors={[theme.colors.card, theme.colors.surface]}
        style={styles.portfolioCard}
      >
        <View style={styles.portfolioHeader}>
          <View style={{ flexDirection: 'row', alignItems: 'center' }}>
            <Text style={styles.portfolioLabel}>Total Portfolio Value</Text>
            {connected && Object.keys(realtimePrices).length > 0 && (
              <View style={styles.liveIndicator}>
                <View style={styles.liveDot} />
                <Text style={styles.liveText}>LIVE</Text>
              </View>
            )}
          </View>
          <TouchableOpacity>
            <Ionicons name="eye-outline" size={24} color={theme.colors.textSecondary} />
          </TouchableOpacity>
        </View>
        
        <Text style={styles.portfolioValue}>{formatCurrency(portfolioValue)}</Text>
        
        <View style={styles.changeContainer}>
          <Ionicons 
            name={dailyChange >= 0 ? "trending-up" : "trending-down"} 
            size={20} 
            color={dailyChange >= 0 ? "#00F89E" : "#FF3B5C"} 
          />
          <Text style={[
            styles.changeValue, 
            { color: dailyChange >= 0 ? "#00F89E" : "#FF3B5C" }
          ]}>
            {dailyChange >= 0 ? '+' : ''}{formatCurrency(Math.abs(dailyChange))} ({dailyChangePercent}%)
          </Text>
        </View>

        <Text style={styles.changeLabel}>24h Change</Text>
      </LinearGradient>

      {/* Quick Stats */}
      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <Ionicons name="wallet-outline" size={24} color="#00D4FF" />
          <Text style={styles.statValue}>{holdings.length || 12}</Text>
          <Text style={styles.statLabel}>Assets</Text>
        </View>
        
        <View style={styles.statCard}>
          <Ionicons name="trending-up-outline" size={24} color="#00F89E" />
          <Text style={styles.statValue}>
            {holdings.length > 0 
              ? `${((holdings.filter(h => h.change24h > 0).length / holdings.length) * 100).toFixed(0)}%`
              : '68%'
            }
          </Text>
          <Text style={styles.statLabel}>Win Rate</Text>
        </View>
        
        <View style={styles.statCard}>
          <Ionicons name="swap-horizontal-outline" size={24} color="#FFB800" />
          <Text style={styles.statValue}>{trades.length || 156}</Text>
          <Text style={styles.statLabel}>Total Trades</Text>
        </View>
      </View>

      {/* AI Insights Section */}
      <TouchableOpacity style={styles.aiCard}>
        <LinearGradient
          colors={['#00D4FF20', '#00D4FF10']}
          style={styles.aiGradient}
        >
          <View style={styles.aiHeader}>
            <Ionicons name="bulb-outline" size={24} color="#00D4FF" />
            <Text style={styles.aiTitle}>AI Insights</Text>
            <Ionicons name="chevron-forward" size={20} color={theme.colors.textSecondary} />
          </View>
          <Text style={styles.aiText}>
            {aiInsight || 'Your portfolio shows strong momentum. Consider rebalancing ETH position.'}
          </Text>
        </LinearGradient>
      </TouchableOpacity>

      {/* Recent Activity */}
      <View style={styles.activitySection}>
        <Text style={styles.sectionTitle}>Recent Activity</Text>
        
        {trades.length > 0 ? (
          trades.map((trade, index) => (
            <View key={trade.id || index} style={styles.activityItem}>
              <View style={styles.activityIcon}>
                <Ionicons 
                  name={trade.side === 'buy' ? "arrow-up" : "arrow-down"} 
                  size={20} 
                  color={trade.side === 'buy' ? "#00F89E" : "#FF3B5C"} 
                />
              </View>
              <View style={styles.activityDetails}>
                <Text style={styles.activityText}>
                  {trade.side === 'buy' ? 'Bought' : 'Sold'} {trade.amount} {trade.symbol ? trade.symbol.split('/')[0] : 'Unknown'}
                </Text>
                <Text style={styles.activityTime}>
                  {new Date(trade.timestamp).toLocaleString()}
                </Text>
              </View>
              <Text style={styles.activityAmount}>{formatCurrency(trade.cost)}</Text>
            </View>
          ))
        ) : (
          <>
            <View style={styles.activityItem}>
              <View style={styles.activityIcon}>
                <Ionicons name="arrow-up" size={20} color="#00F89E" />
              </View>
              <View style={styles.activityDetails}>
                <Text style={styles.activityText}>Bought 0.5 ETH</Text>
                <Text style={styles.activityTime}>2 hours ago</Text>
              </View>
              <Text style={styles.activityAmount}>$1,250.00</Text>
            </View>
            
            <View style={styles.activityItem}>
              <View style={styles.activityIcon}>
                <Ionicons name="arrow-down" size={20} color="#FF3B5C" />
              </View>
              <View style={styles.activityDetails}>
                <Text style={styles.activityText}>Sold 100 ADA</Text>
                <Text style={styles.activityTime}>5 hours ago</Text>
              </View>
              <Text style={styles.activityAmount}>$350.00</Text>
            </View>
          </>
        )}
      </View>
      {/* Debug Button - Remove in production */}
      <TouchableOpacity 
        style={styles.debugButton}
        onPress={async () => {
          console.log('=== DEBUG: Testing API connection ===');
          
          // Check stored credentials
          const creds = await exchangeService.getCredentials();
          console.log('Stored credentials:', creds ? {
            exchange: creds.exchangeName,
            hasApiKey: !!creds.apiKey,
            hasSecret: !!creds.apiSecret,
            apiKeyLength: creds.apiKey?.length
          } : 'No credentials');
          
          // Test direct API call
          try {
            const response = await fetch('http://localhost:5000/api/test-lbank', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
              },
              body: JSON.stringify({
                apiKey: creds?.apiKey || '',
                apiSecret: creds?.apiSecret || ''
              })
            });
            const result = await response.json();
            console.log('Direct API test result:', result);
          } catch (error) {
            console.error('Direct API test error:', error);
          }
          
          // Test through service
          try {
            const stats = await exchangeService.calculatePortfolioStats();
            console.log('Service stats result:', stats);
          } catch (error) {
            console.error('Service stats error:', error);
          }
        }}
      >
        <Text style={styles.debugText}>Debug API Connection</Text>
      </TouchableOpacity>
    </ScrollView>
  );
};

const createStyles = (theme) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    padding: 20,
    paddingTop: 60,
  },
  greeting: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 5,
  },
  date: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  portfolioCard: {
    margin: 20,
    padding: 24,
    borderRadius: 20,
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
  },
  portfolioHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  portfolioLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  portfolioValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 16,
  },
  changeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 4,
  },
  changeValue: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 8,
  },
  changeLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  statsContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  statCard: {
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 16,
    alignItems: 'center',
    flex: 1,
    marginHorizontal: 5,
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  aiCard: {
    marginHorizontal: 20,
    marginBottom: 20,
  },
  aiGradient: {
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: '#00D4FF30',
  },
  aiHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  aiTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    marginLeft: 12,
    flex: 1,
  },
  aiText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    lineHeight: 20,
  },
  activitySection: {
    padding: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 16,
  },
  activityItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  activityIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  activityDetails: {
    flex: 1,
    marginLeft: 12,
  },
  activityText: {
    fontSize: 14,
    fontWeight: '500',
    color: theme.colors.text,
  },
  activityTime: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  activityAmount: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
  },
  debugButton: {
    backgroundColor: '#FF3B5C',
    padding: 16,
    margin: 20,
    borderRadius: 8,
    alignItems: 'center',
  },
  debugText: {
    color: '#FFFFFF',
    fontWeight: 'bold',
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 12,
    paddingHorizontal: 8,
    paddingVertical: 4,
    backgroundColor: theme.colors.success + '20',
    borderRadius: 10,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: theme.colors.success,
    marginRight: 4,
  },
  liveText: {
    fontSize: 11,
    fontWeight: 'bold',
    color: theme.colors.success,
  },
});

export default HomeScreen;