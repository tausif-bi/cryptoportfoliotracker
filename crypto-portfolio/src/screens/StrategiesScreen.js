// screens/StrategiesScreen.js

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Alert,
  Image,
  Dimensions,
  Modal,
  FlatList,
  TextInput,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeContext';
import exchangeService from '../services/exchangeService';
import { authService } from '../services/authService';

const { width } = Dimensions.get('window');

const StrategiesScreen = ({ navigation }) => {
  const { theme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [strategies, setStrategies] = useState([]);
  
  // Debug state changes
  useEffect(() => {
    console.log('Strategies state updated:', strategies.length, 'strategies');
  }, [strategies]);
  const [selectedStrategy, setSelectedStrategy] = useState(null);
  const [analysisData, setAnalysisData] = useState(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [selectedCoin, setSelectedCoin] = useState('BTC/USDT');
  const [tradingPairs, setTradingPairs] = useState([]);
  const [popularPairs, setPopularPairs] = useState([]);
  const [showCoinPicker, setShowCoinPicker] = useState(false);
  const [coinSearch, setCoinSearch] = useState('');
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');
  const [showTimeframePicker, setShowTimeframePicker] = useState(false);
  
  // Available timeframes
  const timeframes = [
    { value: '1m', label: '1 Minute', description: 'Very short-term scalping' },
    { value: '5m', label: '5 Minutes', description: 'Short-term trading' },
    { value: '15m', label: '15 Minutes', description: 'Day trading' },
    { value: '30m', label: '30 Minutes', description: 'Intraday trading' },
    { value: '1h', label: '1 Hour', description: 'Short to medium-term' },
    { value: '2h', label: '2 Hours', description: 'Medium-term trading' },
    { value: '4h', label: '4 Hours', description: 'Swing trading' },
    { value: '6h', label: '6 Hours', description: 'Medium-term positions' },
    { value: '12h', label: '12 Hours', description: 'Daily analysis' },
    { value: '1d', label: '1 Day', description: 'Position trading' },
    { value: '3d', label: '3 Days', description: 'Long-term swing' },
    { value: '1w', label: '1 Week', description: 'Long-term investing' },
  ];

  const fetchTradingPairs = async () => {
    try {
      const response = await fetch(`http://localhost:5000/api/trading-pairs`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        // Ensure uniqueness on frontend as well
        const uniquePairs = data.pairs || [];
        const uniquePopular = data.popular || [];
        
        // Additional deduplication based on symbol
        const pairsMap = new Map();
        uniquePairs.forEach(pair => {
          if (!pairsMap.has(pair.symbol)) {
            pairsMap.set(pair.symbol, pair);
          }
        });
        
        const popularMap = new Map();
        uniquePopular.forEach(pair => {
          if (!popularMap.has(pair.symbol)) {
            popularMap.set(pair.symbol, pair);
          }
        });
        
        setTradingPairs(Array.from(pairsMap.values()));
        setPopularPairs(Array.from(popularMap.values()));
        
        console.log(`Loaded ${pairsMap.size} unique pairs, ${popularMap.size} popular`);
      }
    } catch (error) {
      console.error('Error fetching trading pairs:', error);
      // Use default pairs if fetch fails
      const defaultPairs = [
        { symbol: 'BTC/USDT', base: 'BTC', displayName: 'BTC/USDT' },
        { symbol: 'ETH/USDT', base: 'ETH', displayName: 'ETH/USDT' },
        { symbol: 'BNB/USDT', base: 'BNB', displayName: 'BNB/USDT' },
        { symbol: 'SOL/USDT', base: 'SOL', displayName: 'SOL/USDT' },
        { symbol: 'XRP/USDT', base: 'XRP', displayName: 'XRP/USDT' },
      ];
      setTradingPairs(defaultPairs);
      setPopularPairs(defaultPairs);
    }
  };

  const fetchStrategies = async () => {
    console.log('Fetching strategies...');
    // Use direct URL to avoid baseURL issues
    const strategiesUrl = 'http://localhost:5000/api/strategies/list';
    console.log('API URL:', strategiesUrl);
    
    try {
      // Strategies list is now public, no auth required
      const response = await fetch(strategiesUrl);
      console.log('Response status:', response.status);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('Strategies response:', data);
      
      if (data.success) {
        console.log('Setting strategies:', data.strategies.length);
        setStrategies(data.strategies);
      } else {
        console.error('Failed to fetch strategies:', data.error);
        setStrategies([]);
      }
    } catch (error) {
      console.error('Error fetching strategies:', error);
      if (error.message && error.message.includes('Authentication required')) {
        Alert.alert('Login Required', 'Please log in to view trading strategies', [
          { text: 'OK', onPress: () => navigation.navigate('Profile') }
        ]);
      } else {
        Alert.alert('Error', 'Could not fetch strategies. Please check your connection.');
      }
      setStrategies([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const runStrategyAnalysis = async (strategyId, symbol = null) => {
    console.log('Running strategy analysis for:', strategyId);
    setAnalysisLoading(true);
    const symbolToUse = symbol || selectedCoin;
    
    try {
      // Check if user is logged in before running analysis
      await authService.initialize();
      const isLoggedIn = authService.isLoggedIn();
      console.log('User logged in status:', isLoggedIn);
      console.log('Auth token:', authService.accessToken ? 'Present' : 'Missing');
      
      if (!isLoggedIn) {
        console.log('User not logged in, showing alert');
        Alert.alert('Login Required', 'Please log in to run strategy analysis', [
          { text: 'OK', onPress: () => navigation.navigate('Profile') }
        ]);
        setAnalysisLoading(false);
        return;
      }
      
      // Use authenticated request for strategy analysis
      console.log('Making authenticated request to:', `/strategies/${strategyId}/analyze`);
      console.log('Request params:', { symbol: symbolToUse, timeframe: selectedTimeframe });
      
      const data = await exchangeService.makeAuthenticatedRequest(
        `/strategies/${strategyId}/analyze`,
        {
          symbol: symbolToUse,
          timeframe: selectedTimeframe,
          limit: 500
        }
      );
      
      console.log('Analysis response:', data);
      
      if (data.success) {
        console.log('Setting analysis data');
        setAnalysisData(data.analysis);
      } else {
        console.log('Analysis failed:', data.error);
        Alert.alert('Error', data.error || 'Failed to run analysis');
      }
    } catch (error) {
      console.error('Error running analysis:', error);
      if (error.message && error.message.includes('Authentication required')) {
        Alert.alert('Login Required', 'Please log in to use trading strategies', [
          { text: 'OK', onPress: () => navigation.navigate('Profile') }
        ]);
      } else {
        Alert.alert('Error', 'Could not run strategy analysis');
      }
    } finally {
      setAnalysisLoading(false);
    }
  };

  useEffect(() => {
    fetchStrategies();
    fetchTradingPairs();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchStrategies();
    fetchTradingPairs();
  };

  const handleSelectCoin = (coin) => {
    setSelectedCoin(coin.symbol);
    setShowCoinPicker(false);
    setCoinSearch('');
    // Clear previous analysis when coin changes
    setAnalysisData(null);
  };

  const handleSelectTimeframe = (timeframe) => {
    setSelectedTimeframe(timeframe.value);
    setShowTimeframePicker(false);
    // Clear previous analysis when timeframe changes
    setAnalysisData(null);
  };

  const filteredPairs = coinSearch.length > 0 
    ? tradingPairs.filter(pair => 
        pair.symbol.toLowerCase().includes(coinSearch.toLowerCase()) ||
        pair.base.toLowerCase().includes(coinSearch.toLowerCase())
      )
    : tradingPairs;
  
  // Remove popular pairs from all pairs to avoid duplicates
  const nonPopularPairs = filteredPairs.filter(pair => 
    !popularPairs.some(popular => popular.symbol === pair.symbol)
  );
  
  const getTimeframeLabel = (value) => {
    const tf = timeframes.find(t => t.value === value);
    return tf ? tf.label : value;
  };

  const renderHeader = () => {
    return (
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <TouchableOpacity 
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Trading Strategies</Text>
          <TouchableOpacity 
            style={styles.refreshButton}
            onPress={onRefresh}
          >
            <Ionicons name="refresh-outline" size={24} color="#00ff88" />
          </TouchableOpacity>
        </View>
        <Text style={styles.headerSubtitle}>AI-powered trading analysis</Text>
        
        {/* Selectors Row */}
        <View style={styles.selectorsRow}>
          {/* Coin Selector */}
          <TouchableOpacity 
            style={[styles.selector, styles.coinSelector]}
            onPress={() => setShowCoinPicker(true)}
            activeOpacity={0.7}
          >
            <View style={styles.selectorContent}>
              <Ionicons name="logo-bitcoin" size={20} color="#00ff88" />
              <Text style={styles.selectorText}>{selectedCoin}</Text>
              <Ionicons name="chevron-down" size={20} color={theme.colors.textSecondary} />
            </View>
          </TouchableOpacity>
          
          {/* Timeframe Selector */}
          <TouchableOpacity 
            style={[styles.selector, styles.timeframeSelector]}
            onPress={() => setShowTimeframePicker(true)}
            activeOpacity={0.7}
          >
            <View style={styles.selectorContent}>
              <Ionicons name="time-outline" size={20} color="#00ff88" />
              <Text style={styles.selectorText}>{getTimeframeLabel(selectedTimeframe)}</Text>
              <Ionicons name="chevron-down" size={20} color={theme.colors.textSecondary} />
            </View>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const renderStrategyCard = (strategy) => {
    const isSelected = selectedStrategy?.id === strategy.id;
    const hasAnalysis = isSelected && analysisData;
    
    return (
      <View key={strategy.id}>
        <TouchableOpacity
          style={[styles.strategyCard, isSelected && styles.selectedCard]}
          onPress={() => {
            setSelectedStrategy(strategy);
            setAnalysisData(null);
          }}
          activeOpacity={0.7}
        >
        <View style={styles.cardHeader}>
          <View style={styles.strategyIcon}>
            <Ionicons name="trending-up" size={24} color="#00ff88" />
          </View>
          <View style={styles.strategyInfo}>
            <Text style={styles.strategyName}>{strategy.name}</Text>
            <Text style={styles.strategyCategory}>{strategy.category.toUpperCase()}</Text>
          </View>
          <View style={styles.cardArrow}>
            <Ionicons 
              name={isSelected ? "chevron-down" : "chevron-forward"} 
              size={20} 
              color={theme.colors.textSecondary} 
            />
          </View>
        </View>
        
        <Text style={styles.strategyDescription}>{strategy.description}</Text>
        
        {isSelected && (
          <View style={styles.strategyActions}>
            <TouchableOpacity
              style={styles.analyzeButton}
              onPress={() => {
                console.log('Analyze button pressed for strategy:', strategy.id);
                runStrategyAnalysis(strategy.id);
              }}
              disabled={analysisLoading}
            >
              {analysisLoading ? (
                <ActivityIndicator size="small" color="#fff" />
              ) : (
                <>
                  <Ionicons name="analytics-outline" size={16} color="#fff" />
                  <Text style={styles.analyzeButtonText}>Analyze {selectedCoin}</Text>
                </>
              )}
            </TouchableOpacity>
            
            <TouchableOpacity
              style={styles.compareButton}
              onPress={() => navigation.navigate('StrategyComparison', { 
                strategy,
                symbol: selectedCoin 
              })}
            >
              <Ionicons name="git-compare-outline" size={16} color="#00ff88" />
              <Text style={styles.compareButtonText}>Compare Results</Text>
            </TouchableOpacity>
          </View>
        )}
        </TouchableOpacity>
        
        {/* Show analysis results right below this strategy card */}
        {hasAnalysis && (
          <View style={{ marginTop: -1 }}>
            {renderAnalysisResults()}
          </View>
        )}
      </View>
    );
  };

  const renderAnalysisResults = () => {
    if (!analysisData) return null;

    const getSignalColor = (signal) => {
      switch (signal) {
        case 'BUY': return '#00ff88';
        case 'SELL': return '#ff4444';
        case 'HOLD LONG': return '#ffaa00';
        default: return '#666';
      }
    };

    const getSignalIcon = (signal) => {
      switch (signal) {
        case 'BUY': return 'trending-up';
        case 'SELL': return 'trending-down';
        case 'HOLD LONG': return 'hand-left';
        default: return 'pause';
      }
    };

    return (
      <View style={styles.analysisContainer}>
        <Text style={styles.analysisTitle}>Strategy Analysis Results</Text>
        
        {/* Current Signal */}
        <View style={styles.signalCard}>
          <View style={styles.signalHeader}>
            <Ionicons 
              name={getSignalIcon(analysisData.current_signal)} 
              size={24} 
              color={getSignalColor(analysisData.current_signal)} 
            />
            <Text style={[styles.signalText, { color: getSignalColor(analysisData.current_signal) }]}>
              {analysisData.current_signal}
            </Text>
          </View>
          
          <View style={styles.signalDetails}>
            <Text style={styles.symbolText}>{analysisData.symbol}</Text>
            <Text style={styles.priceText}>
              ${analysisData.current_price?.toFixed(2)}
            </Text>
          </View>
        </View>

        {/* Strategy Metrics */}
        <View style={styles.metricsContainer}>
          <View style={styles.metricCard}>
            <Text style={styles.metricValue}>{analysisData.total_buy_signals}</Text>
            <Text style={styles.metricLabel}>Buy Signals</Text>
          </View>
          
          <View style={styles.metricCard}>
            <Text style={styles.metricValue}>{analysisData.total_sell_signals}</Text>
            <Text style={styles.metricLabel}>Sell Signals</Text>
          </View>
          
          <View style={styles.metricCard}>
            <Text style={styles.metricValue}>
              {analysisData.recent_signals?.length || 0}
            </Text>
            <Text style={styles.metricLabel}>Recent Signals</Text>
          </View>
        </View>

        {/* Chart */}
        {analysisData.chart_base64 && (
          <View style={styles.chartContainer}>
            <Text style={styles.chartTitle}>Strategy Chart</Text>
            <Image
              source={{ uri: `data:image/png;base64,${analysisData.chart_base64}` }}
              style={styles.chartImage}
              resizeMode="contain"
            />
          </View>
        )}

        {/* Recent Signals */}
        {analysisData.recent_signals && analysisData.recent_signals.length > 0 && (
          <View style={styles.recentSignalsContainer}>
            <Text style={styles.recentSignalsTitle}>Recent Signals</Text>
            {analysisData.recent_signals.slice(0, 5).map((signal, index) => (
              <View key={index} style={styles.recentSignalItem}>
                <View style={styles.signalTypeContainer}>
                  <Ionicons 
                    name={signal.type === 'BUY' ? 'trending-up' : 'trending-down'} 
                    size={16} 
                    color={signal.type === 'BUY' ? '#00ff88' : '#ff4444'} 
                  />
                  <Text style={[
                    styles.signalTypeText,
                    { color: signal.type === 'BUY' ? '#00ff88' : '#ff4444' }
                  ]}>
                    {signal.type}
                  </Text>
                </View>
                
                <Text style={styles.signalPrice}>${signal.price?.toFixed(2)}</Text>
                
                <Text style={styles.signalTime}>
                  {new Date(signal.timestamp).toLocaleDateString()}
                </Text>
              </View>
            ))}
          </View>
        )}

        {/* Action Buttons */}
        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={styles.detailButton}
            onPress={() => navigation.navigate('StrategyDetail', { 
              strategy: selectedStrategy, 
              analysis: analysisData,
              symbol: selectedCoin 
            })}
          >
            <Text style={styles.detailButtonText}>View Details</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={styles.compareButton}
            onPress={() => navigation.navigate('StrategyComparison', { 
              strategy: selectedStrategy,
              analysis: analysisData,
              symbol: selectedCoin 
            })}
          >
            <Text style={styles.compareButtonText}>Compare with Actual</Text>
          </TouchableOpacity>
        </View>
        
        {/* Interactive Chart Button */}
        <TouchableOpacity
          style={[styles.interactiveChartButton, { backgroundColor: theme.colors.primary }]}
          onPress={() => navigation.navigate('InteractiveChart', { 
            symbol: selectedCoin 
          })}
        >
          <Ionicons name="trending-up" size={20} color={theme.colors.background} />
          <Text style={[styles.interactiveChartButtonText, { color: theme.colors.background }]}>
            Open Interactive Chart
          </Text>
        </TouchableOpacity>
      </View>
    );
  };

  const renderEmptyState = () => {
    return (
      <View style={styles.emptyState}>
        <Ionicons name="analytics-outline" size={64} color="#666" />
        <Text style={styles.emptyStateText}>No strategies available</Text>
        <Text style={styles.emptyStateSubtext}>
          Check your backend connection
        </Text>
      </View>
    );
  };

  const styles = createStyles(theme);

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#00ff88" />
        <Text style={styles.loadingText}>Loading strategies...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            tintColor="#00ff88"
          />
        }
      >
        {renderHeader()}
        
        <View style={styles.contentContainer}>
          {loading ? (
            <ActivityIndicator size="large" color={theme.colors.primary} style={{ marginTop: 50 }} />
          ) : strategies.length > 0 ? (
            <>
              <Text style={styles.sectionTitle}>Available Strategies</Text>
              {strategies.map(renderStrategyCard)}
            </>
          ) : (
            renderEmptyState()
          )}
        </View>
      </ScrollView>
      
      {/* Coin Picker Modal */}
      <Modal
        visible={showCoinPicker}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowCoinPicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Trading Pair</Text>
              <TouchableOpacity
                onPress={() => setShowCoinPicker(false)}
                style={styles.modalCloseButton}
              >
                <Ionicons name="close" size={24} color={theme.colors.text} />
              </TouchableOpacity>
            </View>
            
            {/* Search Bar */}
            <View style={styles.searchContainer}>
              <Ionicons name="search" size={20} color={theme.colors.textSecondary} />
              <TextInput
                style={styles.searchInput}
                placeholder="Search coins..."
                placeholderTextColor={theme.colors.textSecondary}
                value={coinSearch}
                onChangeText={setCoinSearch}
                autoCapitalize="none"
              />
              {coinSearch.length > 0 && (
                <TouchableOpacity onPress={() => setCoinSearch('')}>
                  <Ionicons name="close-circle" size={20} color={theme.colors.textSecondary} />
                </TouchableOpacity>
              )}
            </View>
            
            {/* Popular Pairs Section */}
            {coinSearch.length === 0 && popularPairs.length > 0 && (
              <>
                <Text style={styles.sectionHeader}>Popular Pairs</Text>
                <FlatList
                  data={popularPairs}
                  keyExtractor={(item) => item.symbol}
                  renderItem={({ item }) => (
                    <TouchableOpacity
                      style={[
                        styles.coinItem,
                        selectedCoin === item.symbol && styles.selectedCoinItem
                      ]}
                      onPress={() => handleSelectCoin(item)}
                    >
                      <Text style={styles.coinItemText}>{item.displayName || item.symbol}</Text>
                      {selectedCoin === item.symbol && (
                        <Ionicons name="checkmark-circle" size={20} color="#00ff88" />
                      )}
                    </TouchableOpacity>
                  )}
                  style={styles.popularList}
                />
                <Text style={styles.sectionHeader}>All Pairs</Text>
              </>
            )}
            
            {/* All Pairs List */}
            <FlatList
              data={coinSearch.length > 0 ? filteredPairs : nonPopularPairs}
              keyExtractor={(item) => item.symbol}
              renderItem={({ item }) => (
                <TouchableOpacity
                  style={[
                    styles.coinItem,
                    selectedCoin === item.symbol && styles.selectedCoinItem
                  ]}
                  onPress={() => handleSelectCoin(item)}
                >
                  <Text style={styles.coinItemText}>{item.displayName || item.symbol}</Text>
                  {selectedCoin === item.symbol && (
                    <Ionicons name="checkmark-circle" size={20} color="#00ff88" />
                  )}
                </TouchableOpacity>
              )}
              style={styles.coinList}
              ListEmptyComponent={
                <View style={styles.emptySearch}>
                  <Text style={styles.emptySearchText}>No pairs found</Text>
                </View>
              }
            />
          </View>
        </View>
      </Modal>
      
      {/* Timeframe Picker Modal */}
      <Modal
        visible={showTimeframePicker}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowTimeframePicker(false)}
      >
        <View style={styles.modalOverlay}>
          <View style={[styles.modalContent, styles.timeframeModalContent]}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Select Timeframe</Text>
              <TouchableOpacity
                onPress={() => setShowTimeframePicker(false)}
                style={styles.modalCloseButton}
              >
                <Ionicons name="close" size={24} color={theme.colors.text} />
              </TouchableOpacity>
            </View>
            
            <ScrollView style={styles.timeframeList}>
              {timeframes.map((timeframe) => (
                <TouchableOpacity
                  key={timeframe.value}
                  style={[
                    styles.timeframeItem,
                    selectedTimeframe === timeframe.value && styles.selectedTimeframeItem
                  ]}
                  onPress={() => handleSelectTimeframe(timeframe)}
                >
                  <View style={styles.timeframeInfo}>
                    <Text style={[
                      styles.timeframeLabel,
                      selectedTimeframe === timeframe.value && styles.selectedTimeframeLabel
                    ]}>
                      {timeframe.label}
                    </Text>
                    <Text style={styles.timeframeDescription}>
                      {timeframe.description}
                    </Text>
                  </View>
                  {selectedTimeframe === timeframe.value && (
                    <Ionicons name="checkmark-circle" size={24} color="#00ff88" />
                  )}
                </TouchableOpacity>
              ))}
            </ScrollView>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const createStyles = (theme) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: theme.colors.background,
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 10,
  },
  headerTop: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  backButton: {
    padding: 8,
  },
  refreshButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  headerSubtitle: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 20,
  },
  contentContainer: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 16,
  },
  strategyCard: {
    backgroundColor: theme.colors.surface,
    marginBottom: 12,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  selectedCard: {
    borderColor: '#00ff88',
    backgroundColor: '#1a2b1f',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 8,
  },
  strategyIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#2a2b2f',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  strategyInfo: {
    flex: 1,
  },
  strategyName: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  strategyCategory: {
    fontSize: 12,
    color: '#00ff88',
    marginTop: 2,
  },
  cardArrow: {
    padding: 4,
  },
  strategyDescription: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    lineHeight: 20,
    marginBottom: 12,
  },
  strategyActions: {
    flexDirection: 'row',
    gap: 12,
    marginTop: 12,
  },
  analyzeButton: {
    flex: 1,
    backgroundColor: '#00ff88',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 8,
  },
  analyzeButtonText: {
    color: '#000',
    fontWeight: 'bold',
    fontSize: 14,
  },
  compareButton: {
    flex: 1,
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#00ff88',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 12,
    borderRadius: 8,
    gap: 8,
  },
  compareButtonText: {
    color: '#00ff88',
    fontWeight: 'bold',
    fontSize: 14,
  },
  analysisContainer: {
    marginTop: -8,
    marginBottom: 16,
    marginHorizontal: 16,
    padding: 16,
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    borderTopLeftRadius: 0,
    borderTopRightRadius: 0,
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderTopWidth: 0,
  },
  analysisTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 16,
  },
  signalCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 20,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  signalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
    gap: 12,
  },
  signalText: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  signalDetails: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  symbolText: {
    fontSize: 16,
    color: theme.colors.text,
    fontWeight: '600',
  },
  priceText: {
    fontSize: 20,
    color: theme.colors.text,
    fontWeight: 'bold',
  },
  metricsContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 20,
  },
  metricCard: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  metricValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#00ff88',
    marginBottom: 4,
  },
  metricLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  chartContainer: {
    marginBottom: 20,
  },
  chartTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 12,
  },
  chartImage: {
    width: width - 40,
    height: 250,
    borderRadius: 8,
  },
  recentSignalsContainer: {
    marginBottom: 20,
  },
  recentSignalsTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 12,
  },
  recentSignalItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 12,
    paddingHorizontal: 16,
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  signalTypeContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    flex: 1,
  },
  signalTypeText: {
    fontWeight: 'bold',
    fontSize: 14,
  },
  signalPrice: {
    color: theme.colors.text,
    fontWeight: '600',
    flex: 1,
    textAlign: 'center',
  },
  signalTime: {
    color: theme.colors.textSecondary,
    fontSize: 12,
    flex: 1,
    textAlign: 'right',
  },
  actionButtons: {
    flexDirection: 'row',
    gap: 12,
  },
  detailButton: {
    flex: 1,
    backgroundColor: '#2a2b2f',
    paddingVertical: 14,
    borderRadius: 8,
    alignItems: 'center',
  },
  detailButtonText: {
    color: theme.colors.text,
    fontWeight: 'bold',
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyStateText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#666',
    marginTop: 16,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: '#555',
    marginTop: 8,
  },
  // Selectors Styles
  selectorsRow: {
    flexDirection: 'row',
    marginTop: 16,
    gap: 12,
  },
  selector: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  coinSelector: {
    // Additional coin-specific styles if needed
  },
  timeframeSelector: {
    // Additional timeframe-specific styles if needed
  },
  selectorContent: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  selectorText: {
    fontSize: 14,
    fontWeight: '600',
    color: theme.colors.text,
  },
  // Modal Styles
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: theme.colors.background,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    height: '80%',
    paddingTop: 20,
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 16,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  modalCloseButton: {
    padding: 8,
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    marginHorizontal: 20,
    marginBottom: 16,
    gap: 12,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
    color: theme.colors.text,
  },
  sectionHeader: {
    fontSize: 14,
    fontWeight: 'bold',
    color: theme.colors.textSecondary,
    paddingHorizontal: 20,
    paddingVertical: 8,
    textTransform: 'uppercase',
  },
  popularList: {
    maxHeight: 200,
  },
  coinList: {
    flex: 1,
  },
  coinItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  selectedCoinItem: {
    backgroundColor: '#1a2b1f',
  },
  coinItemText: {
    fontSize: 16,
    color: theme.colors.text,
    fontWeight: '600',
  },
  emptySearch: {
    padding: 40,
    alignItems: 'center',
  },
  emptySearchText: {
    fontSize: 16,
    color: theme.colors.textSecondary,
  },
  // Timeframe Modal Styles
  timeframeModalContent: {
    height: '60%',
  },
  timeframeList: {
    flex: 1,
  },
  timeframeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 16,
    paddingHorizontal: 20,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  selectedTimeframeItem: {
    backgroundColor: '#1a2b1f',
  },
  timeframeInfo: {
    flex: 1,
  },
  timeframeLabel: {
    fontSize: 16,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 4,
  },
  selectedTimeframeLabel: {
    color: '#00ff88',
  },
  timeframeDescription: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  interactiveChartButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 8,
    marginTop: 16,
    gap: 8,
  },
  interactiveChartButtonText: {
    fontSize: 16,
    fontWeight: 'bold',
  },
});

export default StrategiesScreen;