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
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect } from '@react-navigation/native';
import exchangeService from '../services/exchangeService';
import { useTheme } from '../theme/ThemeContext';

const TradesScreen = () => {
  const { theme } = useTheme();
  const [trades, setTrades] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState('all'); // all, buy, sell
  const [stats, setStats] = useState({
    totalTrades: 0,
    winRate: 0,
    totalProfit: 0,
  });

  useEffect(() => {
    loadTrades();
  }, []);

  const loadTrades = async () => {
    try {
      setIsLoading(true);
      
      // Check if exchange is initialized
      const hasCredentials = await exchangeService.loadSavedCredentials();
      
      if (hasCredentials) {
        // Check if it's demo mode
        const creds = await exchangeService.getCredentials();
        const isDemoMode = creds && creds.exchangeName === 'demo';
        
        // Fetch more trades for demo mode
        const limit = isDemoMode ? 1000 : 100;
        const tradesData = await exchangeService.fetchTrades(null, null, limit);
        
        console.log('API Response:', tradesData);
        console.log(`Fetched ${tradesData.length} trades`);
        
        // Check if we got an array
        if (Array.isArray(tradesData)) {
          setTrades(tradesData);
          calculateStats(tradesData);
        } else {
          console.error('Trades data is not an array:', tradesData);
          // Use mock data as fallback
          const mockTrades = getMockTrades();
          setTrades(mockTrades);
          calculateStats(mockTrades);
        }
      } else {
        // Use mock data for demo
        const mockTrades = getMockTrades();
        setTrades(mockTrades);
        calculateStats(mockTrades);
      }
    } catch (error) {
      console.error('Error loading trades:', error);
      // Use mock data on error
      const mockTrades = getMockTrades();
      setTrades(mockTrades);
      calculateStats(mockTrades);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const getMockTrades = () => [
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
    {
      id: '4',
      symbol: 'SOL/USDT',
      side: 'buy',
      price: 55,
      amount: 50,
      cost: 2750,
      fee: { cost: 2.75, currency: 'USDT' },
      timestamp: Date.now() - 86400000,
      datetime: new Date(Date.now() - 86400000).toISOString(),
    },
    {
      id: '5',
      symbol: 'ADA/USDT',
      side: 'sell',
      price: 0.65,
      amount: 2000,
      cost: 1300,
      fee: { cost: 1.3, currency: 'USDT' },
      timestamp: Date.now() - 172800000,
      datetime: new Date(Date.now() - 172800000).toISOString(),
    },
  ];

  const calculateStats = (tradesData) => {
    const totalTrades = tradesData.length;
    
    // Group trades by symbol and calculate P&L
    const tradesBySymbol = {};
    let totalProfit = 0;
    let winningTrades = 0;
    let losingTrades = 0;
    
    tradesData.forEach(trade => {
      // Handle both demo and live data field names
      const symbol = trade.symbol || 'Unknown';
      const amount = trade.quantity || trade.amount || 0;
      const cost = trade.value || trade.cost || 0;
      const side = trade.side;
      
      if (!symbol || symbol === 'Unknown') {
        return;
      }
      if (!tradesBySymbol[symbol]) {
        tradesBySymbol[symbol] = {
          buys: [],
          sells: [],
          totalBought: 0,
          totalSold: 0,
          avgBuyPrice: 0,
          avgSellPrice: 0
        };
      }
      
      if (side === 'buy') {
        tradesBySymbol[symbol].buys.push(trade);
        tradesBySymbol[symbol].totalBought += amount;
      } else {
        tradesBySymbol[symbol].sells.push(trade);
        tradesBySymbol[symbol].totalSold += amount;
      }
    });
    
    // Calculate average prices and estimate P&L
    Object.keys(tradesBySymbol).forEach(symbol => {
      const data = tradesBySymbol[symbol];
      
      // Calculate average buy price
      let totalBuyCost = 0;
      data.buys.forEach(trade => {
        totalBuyCost += (trade.value || trade.cost || 0);
      });
      data.avgBuyPrice = data.totalBought > 0 ? totalBuyCost / data.totalBought : 0;
      
      // Calculate average sell price
      let totalSellRevenue = 0;
      data.sells.forEach(trade => {
        totalSellRevenue += (trade.value || trade.cost || 0);
      });
      data.avgSellPrice = data.totalSold > 0 ? totalSellRevenue / data.totalSold : 0;
      
      // Estimate P&L for closed positions
      const closedAmount = Math.min(data.totalBought, data.totalSold);
      if (closedAmount > 0 && data.avgBuyPrice > 0 && data.avgSellPrice > 0) {
        const profit = (data.avgSellPrice - data.avgBuyPrice) * closedAmount;
        totalProfit += profit;
        
        if (profit > 0) {
          winningTrades += data.sells.length;
        } else {
          losingTrades += data.sells.length;
        }
      }
    });
    
    const winRate = (winningTrades + losingTrades) > 0 
      ? (winningTrades / (winningTrades + losingTrades)) * 100 
      : 0;
    
    setStats({
      totalTrades,
      winRate: winRate.toFixed(1),
      totalProfit: totalProfit,
    });
  };

  const onRefresh = () => {
    setRefreshing(true);
    loadTrades();
  };

  const formatDate = (timestamp) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffInHours = (now - date) / (1000 * 60 * 60);
    
    if (diffInHours < 1) {
      return 'Just now';
    } else if (diffInHours < 24) {
      return `${Math.floor(diffInHours)}h ago`;
    } else if (diffInHours < 48) {
      return 'Yesterday';
    } else {
      return date.toLocaleDateString();
    }
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const getFilteredTrades = () => {
    if (filter === 'all') return trades;
    return trades.filter(trade => trade.side === filter);
  };

  const styles = createStyles(theme);

  if (isLoading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Trades</Text>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
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
          tintColor={theme.colors.primary}
        />
      }
    >
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Trades</Text>
        <TouchableOpacity>
          <Ionicons name="filter-outline" size={24} color={theme.colors.textSecondary} />
        </TouchableOpacity>
      </View>

      {/* Stats Cards */}
      <ScrollView 
        horizontal 
        showsHorizontalScrollIndicator={false}
        style={styles.statsContainer}
      >
        <View style={[styles.statCard, { backgroundColor: theme.colors.surface }]}>
          <Ionicons name="swap-horizontal" size={24} color={theme.colors.primary} />
          <Text style={styles.statValue}>{stats.totalTrades}</Text>
          <Text style={styles.statLabel}>Total Trades</Text>
        </View>

        <View style={[styles.statCard, { backgroundColor: theme.colors.surface }]}>
          <Ionicons name="trending-up" size={24} color="#00F89E" />
          <Text style={styles.statValue}>{stats.winRate}%</Text>
          <Text style={styles.statLabel}>Win Rate</Text>
        </View>

        <View style={[styles.statCard, { backgroundColor: theme.colors.surface }]}>
          <Ionicons name="cash-outline" size={24} color="#FFB800" />
          <Text style={styles.statValue}>{formatCurrency(stats.totalProfit)}</Text>
          <Text style={styles.statLabel}>Total Profit</Text>
        </View>
      </ScrollView>

      {/* Filter Tabs */}
      <View style={styles.filterContainer}>
        <TouchableOpacity
          style={[styles.filterTab, filter === 'all' && styles.filterTabActive]}
          onPress={() => setFilter('all')}
        >
          <Text style={[styles.filterText, filter === 'all' && styles.filterTextActive]}>
            All
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.filterTab, filter === 'buy' && styles.filterTabActive]}
          onPress={() => setFilter('buy')}
        >
          <Text style={[styles.filterText, filter === 'buy' && styles.filterTextActive]}>
            Buy
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.filterTab, filter === 'sell' && styles.filterTabActive]}
          onPress={() => setFilter('sell')}
        >
          <Text style={[styles.filterText, filter === 'sell' && styles.filterTextActive]}>
            Sell
          </Text>
        </TouchableOpacity>
      </View>

      {/* Trades List */}
      <View style={styles.tradesSection}>
        {getFilteredTrades().map((trade, index) => {
          // Handle both demo and live data structures
          const tradeKey = trade?.trade_id || trade?.id || index;
          const amount = trade?.quantity || trade?.amount || 0;
          
          // For demo data, infer symbol based on price range or use default
          let symbol = trade?.symbol;
          let baseCurrency = 'BTC';
          
          if (!symbol) {
            // Demo data doesn't have symbol, so infer from price
            const price = trade?.price || 0;
            if (price > 40000) {
              symbol = 'BTC/USDT';
              baseCurrency = 'BTC';
            } else if (price > 2000 && price < 5000) {
              symbol = 'ETH/USDT';
              baseCurrency = 'ETH';
            } else if (price > 100 && price < 1000) {
              symbol = 'BNB/USDT';
              baseCurrency = 'BNB';
            } else if (price > 20 && price < 200) {
              symbol = 'SOL/USDT';
              baseCurrency = 'SOL';
            } else if (price > 0.1 && price < 10) {
              symbol = 'ADA/USDT';
              baseCurrency = 'ADA';
            } else {
              // Random assignment for demo purposes
              const demoSymbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'SOL/USDT', 'ADA/USDT'];
              symbol = demoSymbols[index % demoSymbols.length];
              baseCurrency = symbol.split('/')[0];
            }
          } else {
            baseCurrency = symbol.includes('/') ? symbol.split('/')[0] : 'BTC';
          }
          
          const cost = trade?.value || trade?.cost || 0;
          const price = trade?.price || 0;
          const side = trade?.side || 'unknown';
          const timestamp = trade?.timestamp || trade?.datetime;
          
          return (
            <TouchableOpacity key={tradeKey} style={styles.tradeItem}>
              <View style={styles.tradeLeft}>
                <View style={[
                  styles.tradeIcon,
                  { backgroundColor: side === 'buy' ? '#00F89E20' : '#FF3B5C20' }
                ]}>
                  <Ionicons 
                    name={side === 'buy' ? 'arrow-up' : 'arrow-down'} 
                    size={20} 
                    color={side === 'buy' ? '#00F89E' : '#FF3B5C'} 
                  />
                </View>
                
                <View style={styles.tradeDetails}>
                  <Text style={styles.tradeSymbol}>
                    {symbol}
                  </Text>
                  <Text style={styles.tradeTime}>
                    {timestamp ? formatDate(timestamp) : 'Unknown time'}
                  </Text>
                </View>
              </View>
              
              <View style={styles.tradeRight}>
                <Text style={styles.tradeAmount}>
                  {amount} {baseCurrency}
                </Text>
                <Text style={styles.tradeCost}>
                  {formatCurrency(cost)}
                </Text>
                <Text style={styles.tradePrice}>
                  @ {formatCurrency(price)}
                </Text>
              </View>
            </TouchableOpacity>
          );
        })}
      </View>
    </ScrollView>
  );
};

const createStyles = (theme) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  statsContainer: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  statCard: {
    padding: 20,
    borderRadius: 16,
    marginRight: 12,
    alignItems: 'center',
    minWidth: 120,
  },
  statValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginTop: 8,
  },
  statLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  filterContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  filterTab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 12,
    marginHorizontal: 4,
    backgroundColor: theme.colors.surface,
  },
  filterTabActive: {
    backgroundColor: theme.colors.primary + '20',
    borderWidth: 1,
    borderColor: theme.colors.primary + '40',
  },
  filterText: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.textSecondary,
  },
  filterTextActive: {
    color: theme.colors.primary,
  },
  tradesSection: {
    paddingHorizontal: 20,
    paddingBottom: 20,
  },
  tradeItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
  },
  tradeLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  tradeIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  tradeDetails: {
    flex: 1,
  },
  tradeSymbol: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
  },
  tradeTime: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  tradeRight: {
    alignItems: 'flex-end',
  },
  tradeAmount: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
  },
  tradeCost: {
    fontSize: 14,
    fontWeight: '500',
    color: theme.colors.primary,
    marginTop: 2,
  },
  tradePrice: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
});

export default TradesScreen;