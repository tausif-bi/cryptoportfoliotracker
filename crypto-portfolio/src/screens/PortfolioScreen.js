import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { PieChart } from 'react-native-chart-kit';
import exchangeService from '../services/exchangeService';
import { useTheme } from '../theme/ThemeContext';
import { useRealTimePrices } from '../hooks/useRealTimePrices';

const { width } = Dimensions.get('window');

const PortfolioScreen = () => {
  const { theme } = useTheme();
  const [portfolio, setPortfolio] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCoin, setSelectedCoin] = useState(null);
  
  // Get real-time prices for portfolio coins
  const holdings = portfolio?.holdings || [];
  const symbols = holdings.map(h => `${h.coin || h.symbol}/USDT`).filter(s => s !== '/USDT');
  const { prices: realtimePrices, connected } = useRealTimePrices(symbols);
  const [realtimeTotalValue, setRealtimeTotalValue] = useState(null);

  useEffect(() => {
    loadPortfolioData();
  }, []);

  // Calculate real-time total portfolio value
  useEffect(() => {
    if (connected && holdings.length > 0 && Object.keys(realtimePrices).length > 0) {
      let totalValue = 0;
      
      holdings.forEach(holding => {
        const coinName = holding.coin || holding.symbol || 'Unknown';
        const amount = holding.amount || holding.balance || 0;
        const symbol = `${coinName}/USDT`;
        const realtimeData = realtimePrices[symbol];
        
        if (realtimeData) {
          totalValue += realtimeData.price * amount;
        } else {
          // Fall back to cached value if no real-time price
          totalValue += holding.usdValue || 0;
        }
      });
      
      setRealtimeTotalValue(totalValue);
    }
  }, [realtimePrices, holdings, connected]);

  const loadPortfolioData = async () => {
    try {
      setIsLoading(true);
      
      // Check if exchange is initialized
      const hasCredentials = await exchangeService.loadSavedCredentials();
      
      if (hasCredentials) {
        const stats = await exchangeService.calculatePortfolioStats();
        setPortfolio(stats);
      } else {
        // Use mock data for demo
        setPortfolio(getMockPortfolioData());
      }
    } catch (error) {
      console.error('Error loading portfolio:', error);
      // Use mock data on error
      setPortfolio(getMockPortfolioData());
    } finally {
      setIsLoading(false);
    }
  };

  const getMockPortfolioData = () => ({
    totalValue: 125432.56,
    holdings: [
      { coin: 'BTC', amount: 1.5, usdValue: 65000, allocation: 51.8, change24h: 2.3, price: 43333 },
      { coin: 'ETH', amount: 15, usdValue: 37500, allocation: 29.9, change24h: -1.2, price: 2500 },
      { coin: 'BNB', amount: 25, usdValue: 7500, allocation: 6.0, change24h: 0.8, price: 300 },
      { coin: 'SOL', amount: 100, usdValue: 6000, allocation: 4.8, change24h: 5.4, price: 60 },
      { coin: 'ADA', amount: 5000, usdValue: 3500, allocation: 2.8, change24h: -3.2, price: 0.7 },
      { coin: 'DOT', amount: 200, usdValue: 3000, allocation: 2.4, change24h: 1.5, price: 15 },
      { coin: 'MATIC', amount: 2000, usdValue: 2932.56, allocation: 2.3, change24h: -0.5, price: 1.47 },
    ],
    numberOfAssets: 7,
  });

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(value);
  };

  const getChartData = () => {
    if (!portfolio || !portfolio.holdings) return [];
    
    const colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FECA57', '#FF9FF3', '#54A0FF'];
    
    return portfolio.holdings.map((holding, index) => {
      // Handle both data structures: {coin, allocation} vs {symbol, percentage}
      const name = holding.coin || holding.symbol || 'Unknown';
      const allocation = holding.allocation || holding.percentage || 0;
      
      return {
        name,
        population: allocation,
        color: colors[index % colors.length],
        legendFontColor: theme.colors.textSecondary,
        legendFontSize: 12,
      };
    });
  };

  const styles = createStyles(theme);

  if (isLoading) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Portfolio</Text>
        </View>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      </View>
    );
  }

  if (!portfolio) {
    return (
      <View style={styles.container}>
        <View style={styles.header}>
          <Text style={styles.headerTitle}>Portfolio</Text>
        </View>
        <View style={styles.loadingContainer}>
          <Text style={styles.errorText}>No portfolio data available</Text>
        </View>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Portfolio</Text>
        <TouchableOpacity onPress={loadPortfolioData}>
          <Ionicons name="refresh-outline" size={24} color={theme.colors.textSecondary} />
        </TouchableOpacity>
      </View>

      {/* Total Value Card */}
      <LinearGradient
        colors={[theme.colors.surface, theme.colors.background]}
        style={styles.totalValueCard}
      >
        <View style={styles.totalValueHeader}>
          <Text style={styles.totalValueLabel}>Total Portfolio Value</Text>
          {connected && realtimeTotalValue && (
            <View style={styles.liveIndicator}>
              <View style={styles.liveDot} />
              <Text style={styles.liveText}>LIVE</Text>
            </View>
          )}
        </View>
        <Text style={styles.totalValue}>{formatCurrency(realtimeTotalValue || portfolio.totalValue || 0)}</Text>
        <Text style={styles.assetsCount}>{portfolio.numberOfAssets || portfolio.holdings?.length || 0} Assets</Text>
      </LinearGradient>

      {/* Pie Chart */}
      {portfolio.holdings && portfolio.holdings.length > 0 && (
        <View style={styles.chartContainer}>
          <Text style={styles.sectionTitle}>Allocation</Text>
          <PieChart
            data={getChartData()}
            width={width - 40}
            height={220}
            chartConfig={{
              color: (opacity = 1) => `rgba(255, 255, 255, ${opacity})`,
            }}
            accessor="population"
            backgroundColor="transparent"
            paddingLeft="15"
            absolute
          />
        </View>
      )}

      {/* Holdings List */}
      <View style={styles.holdingsSection}>
        <Text style={styles.sectionTitle}>Holdings</Text>
        
        {portfolio.holdings && portfolio.holdings.length > 0 ? (
          portfolio.holdings.map((holding, index) => {
            // Handle both data structures safely
            const coinName = holding.coin || holding.symbol || 'Unknown';
            const amount = holding.amount || holding.balance || 0;
            const allocation = holding.allocation || holding.percentage || 0;
            
            // Get real-time price data
            const symbol = `${coinName}/USDT`;
            const realtimeData = realtimePrices[symbol];
            const hasRealtimePrice = connected && realtimeData;
            
            // Use real-time price if available, otherwise fall back to cached
            const currentPrice = hasRealtimePrice ? realtimeData.price : (holding.price || 0);
            const change24h = hasRealtimePrice ? realtimeData.change24h : (holding.change24h || 0);
            const usdValue = currentPrice * amount;
            
            // Debug log
            if (index === 0) {
              console.log(`${coinName}: realtime=${hasRealtimePrice}, price=${currentPrice}, amount=${amount}, value=${usdValue}`);
            }
            
            return (
              <TouchableOpacity
                key={`${coinName}-${index}`}
                style={styles.holdingItem}
                onPress={() => setSelectedCoin(coinName)}
              >
                <View style={styles.holdingLeft}>
                  <View style={styles.coinIcon}>
                    <Text style={styles.coinIconText}>
                      {coinName && coinName.length > 0 ? coinName[0] : '?'}
                    </Text>
                  </View>
                  <View style={styles.coinInfo}>
                    <Text style={styles.coinName}>{coinName}</Text>
                    <Text style={styles.coinAmount}>{amount} {coinName}</Text>
                  </View>
                </View>
                
                <View style={styles.holdingRight}>
                  <View style={styles.priceRow}>
                    <Text style={styles.holdingValue}>{formatCurrency(usdValue)}</Text>
                    {hasRealtimePrice && (
                      <View style={styles.liveIndicator}>
                        <View style={styles.liveDot} />
                        <Text style={styles.liveText}>LIVE</Text>
                      </View>
                    )}
                  </View>
                  <View style={styles.changeContainer}>
                    <Text style={[
                      styles.changeText,
                      { color: change24h >= 0 ? theme.colors.success : theme.colors.error }
                    ]}>
                      {change24h >= 0 ? '+' : ''}{change24h.toFixed(1)}%
                    </Text>
                    <Text style={styles.allocationText}>{allocation.toFixed(1)}%</Text>
                  </View>
                </View>
              </TouchableOpacity>
            );
          })
        ) : (
          <View style={styles.emptyState}>
            <Text style={styles.emptyText}>No holdings found</Text>
          </View>
        )}
      </View>

      {/* AI Insights */}
      <TouchableOpacity style={styles.insightsCard}>
        <LinearGradient
          colors={[`${theme.colors.primary}20`, `${theme.colors.primary}10`]}
          style={styles.insightsGradient}
        >
          <View style={styles.insightsHeader}>
            <Ionicons name="analytics-outline" size={24} color={theme.colors.primary} />
            <Text style={styles.insightsTitle}>Portfolio Analysis</Text>
          </View>
          <Text style={styles.insightsText}>
            Your portfolio shows good diversification across major cryptocurrencies. Consider monitoring market trends for optimization opportunities.
          </Text>
          <TouchableOpacity style={styles.viewMoreButton}>
            <Text style={styles.viewMoreText}>View Detailed Analysis</Text>
            <Ionicons name="arrow-forward" size={16} color={theme.colors.primary} />
          </TouchableOpacity>
        </LinearGradient>
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
  errorText: {
    color: theme.colors.textSecondary,
    fontSize: 16,
  },
  totalValueCard: {
    marginHorizontal: 20,
    padding: 24,
    borderRadius: 20,
    alignItems: 'center',
    marginBottom: 20,
  },
  totalValueHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  totalValueLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  totalValue: {
    fontSize: 36,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 8,
  },
  assetsCount: {
    fontSize: 14,
    color: theme.colors.primary,
  },
  chartContainer: {
    marginHorizontal: 20,
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 16,
  },
  holdingsSection: {
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  holdingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 16,
    marginBottom: 12,
  },
  holdingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  coinIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: theme.colors.background,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  coinIconText: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.primary,
  },
  coinInfo: {
    justifyContent: 'center',
  },
  coinName: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
  },
  coinAmount: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  holdingRight: {
    alignItems: 'flex-end',
  },
  priceRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  holdingValue: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
  },
  liveIndicator: {
    flexDirection: 'row',
    alignItems: 'center',
    marginLeft: 8,
    paddingHorizontal: 6,
    paddingVertical: 2,
    backgroundColor: theme.colors.success + '20',
    borderRadius: 8,
  },
  liveDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: theme.colors.success,
    marginRight: 4,
  },
  liveText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: theme.colors.success,
  },
  changeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 2,
  },
  changeText: {
    fontSize: 12,
    fontWeight: '500',
    marginRight: 8,
  },
  allocationText: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  emptyState: {
    padding: 20,
    alignItems: 'center',
  },
  emptyText: {
    color: theme.colors.textSecondary,
    fontSize: 14,
  },
  insightsCard: {
    marginHorizontal: 20,
    marginBottom: 40,
  },
  insightsGradient: {
    padding: 20,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: `${theme.colors.primary}30`,
  },
  insightsHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  insightsTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    marginLeft: 12,
  },
  insightsText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    lineHeight: 20,
    marginBottom: 12,
  },
  viewMoreButton: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  viewMoreText: {
    fontSize: 14,
    color: theme.colors.primary,
    marginRight: 4,
  },
});

export default PortfolioScreen;