// screens/StrategyComparisonScreen.js

import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
  Image,
  Dimensions,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';

const { width } = Dimensions.get('window');

const StrategyComparisonScreen = ({ navigation, route }) => {
  const { strategy, analysis } = route.params;
  const [loading, setLoading] = useState(true);
  const [comparisonData, setComparisonData] = useState(null);
  const [selectedView, setSelectedView] = useState('overview'); // 'overview', 'signals', 'performance'

  const fetchComparisonData = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/strategies/compare', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: 'BTC/USDT',
          timeframe: '1h'
        })
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data = await response.json();
      
      if (data.success) {
        setComparisonData(data.comparison);
      } else {
        Alert.alert('Error', data.error || 'Failed to load comparison data');
      }
    } catch (error) {
      console.error('Error fetching comparison data:', error);
      Alert.alert('Error', 'Could not load comparison data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchComparisonData();
  }, []);

  const renderHeader = () => {
    return (
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <TouchableOpacity 
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Ionicons name="arrow-back" size={24} color="#fff" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Strategy Comparison</Text>
          <View style={styles.placeholder} />
        </View>
        <Text style={styles.headerSubtitle}>AI Predictions vs Actual Trading</Text>
      </View>
    );
  };

  const renderViewToggle = () => {
    const views = [
      { id: 'overview', label: 'Overview', icon: 'analytics-outline' },
      { id: 'signals', label: 'Signals', icon: 'pulse-outline' },
      { id: 'performance', label: 'Performance', icon: 'trending-up-outline' }
    ];

    return (
      <View style={styles.viewToggle}>
        {views.map((view) => (
          <TouchableOpacity
            key={view.id}
            style={[styles.toggleButton, selectedView === view.id && styles.toggleButtonActive]}
            onPress={() => setSelectedView(view.id)}
          >
            <Ionicons 
              name={view.icon} 
              size={16} 
              color={selectedView === view.id ? '#000' : '#666'} 
            />
            <Text style={[styles.toggleText, selectedView === view.id && styles.toggleTextActive]}>
              {view.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  // Update the renderOverviewTab function in your StrategyComparisonScreen.js:

const renderOverviewTab = () => {
  if (!comparisonData) return null;

  const { actual_trading, ai_predictions, metrics } = comparisonData;

  return (
    <View style={styles.tabContent}>
      {/* Summary Cards */}
      <View style={styles.summaryContainer}>
        <View style={styles.summaryCard}>
          <View style={styles.summaryHeader}>
            <Ionicons name="person-outline" size={20} color="#00ff88" />
            <Text style={styles.summaryTitle}>Your Trading</Text>
          </View>
          <Text style={styles.summaryValue}>{actual_trading.total_trades}</Text>
          <Text style={styles.summaryLabel}>Total Trades</Text>
          <Text style={[
            styles.summaryPnL,
            actual_trading.total_pnl >= 0 ? styles.profit : styles.loss
          ]}>
            {actual_trading.total_pnl >= 0 ? '+' : ''}${actual_trading.total_pnl?.toFixed(2)}
          </Text>
          <Text style={styles.summaryWinRate}>
            Win Rate: {actual_trading.win_rate?.toFixed(1)}%
          </Text>
        </View>

        <View style={styles.summaryCard}>
          <View style={styles.summaryHeader}>
            <Ionicons name="robot-outline" size={20} color="#ff9500" />
            <Text style={styles.summaryTitle}>AI Strategy</Text>
          </View>
          <Text style={styles.summaryValue}>{ai_predictions.total_trades || 0}</Text>
          <Text style={styles.summaryLabel}>Completed Trades</Text>
          <Text style={[
            styles.summaryPnL,
            (ai_predictions.total_pnl || 0) >= 0 ? styles.profit : styles.loss
          ]}>
            {(ai_predictions.total_pnl || 0) >= 0 ? '+' : ''}${(ai_predictions.total_pnl || 0)?.toFixed(2)}
          </Text>
          <Text style={styles.summaryWinRate}>
            Win Rate: {ai_predictions.win_rate?.toFixed(1) || '0.0'}%
          </Text>
        </View>
      </View>

      {/* Performance Comparison */}
      <View style={styles.performanceComparisonCard}>
        <Text style={styles.comparisonTitle}>Performance Comparison</Text>
        <Text style={styles.comparisonResult}>
          {metrics.performance_comparison || 'Analyzing performance...'}
        </Text>
        
        <View style={styles.comparisonMetrics}>
          <View style={styles.comparisonMetric}>
            <Text style={styles.comparisonLabel}>Your Win Rate</Text>
            <Text style={[styles.comparisonValue, styles.profit]}>
              {actual_trading.win_rate?.toFixed(1)}%
            </Text>
          </View>
          
          <Text style={styles.vsText}>vs</Text>
          
          <View style={styles.comparisonMetric}>
            <Text style={styles.comparisonLabel}>AI Win Rate</Text>
            <Text style={[styles.comparisonValue, styles.aiColor]}>
              {ai_predictions.win_rate?.toFixed(1) || '0.0'}%
            </Text>
          </View>
        </View>
      </View>

      {/* Metrics Comparison */}
      <View style={styles.metricsSection}>
        <Text style={styles.sectionTitle}>Detailed Metrics</Text>
        
        <View style={styles.metricRow}>
          <Text style={styles.metricLabel}>Total Trades</Text>
          <View style={styles.metricComparison}>
            <Text style={styles.metricValue}>
              You: {actual_trading.total_trades} trades
            </Text>
            <Text style={styles.metricValue}>
              AI: {ai_predictions.total_trades || 0} trades
            </Text>
          </View>
        </View>

        <View style={styles.metricRow}>
          <Text style={styles.metricLabel}>Total P&L</Text>
          <View style={styles.metricComparison}>
            <Text style={[styles.metricValue, actual_trading.total_pnl >= 0 ? styles.profit : styles.loss]}>
              You: ${actual_trading.total_pnl?.toFixed(2)}
            </Text>
            <Text style={[styles.metricValue, (ai_predictions.total_pnl || 0) >= 0 ? styles.profit : styles.loss]}>
              AI: ${(ai_predictions.total_pnl || 0)?.toFixed(2)}
            </Text>
          </View>
        </View>

        <View style={styles.metricRow}>
          <Text style={styles.metricLabel}>Signal Activity</Text>
          <View style={styles.metricComparison}>
            <Text style={styles.metricValue}>
              AI generates {metrics.signal_frequency_ratio?.toFixed(2)}x more signals
            </Text>
          </View>
        </View>
      </View>

      {/* Analysis Period */}
      <View style={styles.periodSection}>
        <Text style={styles.sectionTitle}>Analysis Period</Text>
        <Text style={styles.periodText}>
          From: {new Date(metrics.analysis_period?.start).toLocaleDateString()}
        </Text>
        <Text style={styles.periodText}>
          To: {new Date(metrics.analysis_period?.end).toLocaleDateString()}
        </Text>
      </View>
    </View>
  );
};

// Add these new styles to your StyleSheet:

const newStyles = {
  summaryWinRate: {
    fontSize: 12,
    color: '#00ff88',
    fontWeight: '600',
    marginTop: 4,
  },
  performanceComparisonCard: {
    backgroundColor: '#1a1b1f',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#2a2b2f',
  },
  comparisonTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
    textAlign: 'center',
  },
  comparisonResult: {
    fontSize: 14,
    color: '#00ff88',
    textAlign: 'center',
    marginBottom: 16,
    fontWeight: '600',
  },
  comparisonMetrics: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-around',
  },
  comparisonMetric: {
    alignItems: 'center',
  },
  comparisonLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  comparisonValue: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  vsText: {
    fontSize: 14,
    color: '#666',
    fontWeight: 'bold',
  },
  aiColor: {
    color: '#ff9500',
  },
};

  const renderSignalsTab = () => {
    if (!comparisonData) return null;

    const { actual_trading, ai_predictions } = comparisonData;

    return (
      <View style={styles.tabContent}>
        {/* Signal Comparison Chart */}
        <View style={styles.signalChartContainer}>
          <Text style={styles.sectionTitle}>Signal Timeline Comparison</Text>
          <Text style={styles.chartSubtitle}>
            Green: Your trades • Blue: AI predictions
          </Text>
          
          {/* This would be a more complex chart in a real implementation */}
          <View style={styles.chartPlaceholder}>
            <Ionicons name="bar-chart-outline" size={48} color="#666" />
            <Text style={styles.chartPlaceholderText}>
              Signal timeline visualization would go here
            </Text>
          </View>
        </View>

        {/* Recent Signals Comparison */}
        <View style={styles.recentSignalsSection}>
          <Text style={styles.sectionTitle}>Recent Activity</Text>
          
          {/* Your Recent Trades */}
          <View style={styles.signalGroup}>
            <Text style={styles.signalGroupTitle}>Your Recent Trades</Text>
            {actual_trading.buy_signals?.slice(0, 3).map((signal, index) => (
              <View key={`actual-${index}`} style={styles.signalItem}>
                <View style={styles.signalIcon}>
                  <Ionicons name="trending-up" size={16} color="#00ff88" />
                </View>
                <View style={styles.signalInfo}>
                  <Text style={styles.signalType}>BUY</Text>
                  <Text style={styles.signalTime}>
                    {new Date(signal.timestamp).toLocaleDateString()}
                  </Text>
                </View>
                <Text style={styles.signalPrice}>${signal.price?.toFixed(2)}</Text>
              </View>
            ))}
          </View>

          {/* AI Recent Signals */}
          <View style={styles.signalGroup}>
            <Text style={styles.signalGroupTitle}>AI Recent Signals</Text>
            {ai_predictions.buy_signals?.slice(0, 3).map((signal, index) => (
              <View key={`ai-${index}`} style={styles.signalItem}>
                <View style={[styles.signalIcon, { backgroundColor: '#ff9500' }]}>
                  <Ionicons name="trending-up" size={16} color="#fff" />
                </View>
                <View style={styles.signalInfo}>
                  <Text style={styles.signalType}>AI BUY</Text>
                  <Text style={styles.signalTime}>
                    {new Date(signal.timestamp).toLocaleDateString()}
                  </Text>
                </View>
                <Text style={styles.signalPrice}>${signal.price?.toFixed(2)}</Text>
              </View>
            ))}
          </View>
        </View>
      </View>
    );
  };

  const renderPerformanceTab = () => {
    if (!comparisonData) return null;

    const { actual_trading, metrics } = comparisonData;

    return (
      <View style={styles.tabContent}>
        {/* Performance Summary */}
        <View style={styles.performanceSection}>
          <Text style={styles.sectionTitle}>Performance Analysis</Text>
          
          <View style={styles.performanceCard}>
            <Text style={styles.performanceTitle}>Your Trading Performance</Text>
            <View style={styles.performanceMetrics}>
              <View style={styles.performanceMetric}>
                <Text style={styles.performanceLabel}>Total P&L</Text>
                <Text style={[
                  styles.performanceValue,
                  actual_trading.total_pnl >= 0 ? styles.profit : styles.loss
                ]}>
                  {actual_trading.total_pnl >= 0 ? '+' : ''}${actual_trading.total_pnl?.toFixed(2)}
                </Text>
              </View>
              
              <View style={styles.performanceMetric}>
                <Text style={styles.performanceLabel}>Win Rate</Text>
                <Text style={styles.performanceValue}>
                  {metrics.actual_win_rate?.toFixed(1)}%
                </Text>
              </View>
              
              <View style={styles.performanceMetric}>
                <Text style={styles.performanceLabel}>Total Trades</Text>
                <Text style={styles.performanceValue}>
                  {actual_trading.total_trades}
                </Text>
              </View>
            </View>
          </View>

          <View style={styles.performanceCard}>
            <Text style={styles.performanceTitle}>Strategy Insights</Text>
            <View style={styles.insightsList}>
              <View style={styles.insightItem}>
                <Ionicons name="analytics-outline" size={16} color="#00ff88" />
                <Text style={styles.insightText}>
                  AI generated {comparisonData.ai_predictions.total_signals} signals vs your {actual_trading.total_trades} trades
                </Text>
              </View>
              
              <View style={styles.insightItem}>
                <Ionicons name="time-outline" size={16} color="#ff9500" />
                <Text style={styles.insightText}>
                  Strategy suggests {metrics.signal_frequency_ratio > 1 ? 'more frequent' : 'less frequent'} trading
                </Text>
              </View>
              
              <View style={styles.insightItem}>
                <Ionicons name="trending-up-outline" size={16} color="#666" />
                <Text style={styles.insightText}>
                  Analysis covers {Math.ceil((new Date(metrics.analysis_period?.end) - new Date(metrics.analysis_period?.start)) / (1000 * 60 * 60 * 24))} days of data
                </Text>
              </View>
            </View>
          </View>

          {/* Recommendations */}
          <View style={styles.recommendationsSection}>
            <Text style={styles.sectionTitle}>Recommendations</Text>
            
            <View style={styles.recommendationCard}>
              <Ionicons name="bulb-outline" size={20} color="#ffaa00" />
              <View style={styles.recommendationContent}>
                <Text style={styles.recommendationTitle}>Strategy Suggestion</Text>
                <Text style={styles.recommendationText}>
                  {metrics.signal_frequency_ratio > 2 
                    ? "The AI strategy suggests more frequent trading. Consider testing with smaller position sizes."
                    : metrics.signal_frequency_ratio < 0.5
                    ? "The AI strategy is more conservative. This could help reduce trading costs."
                    : "The AI strategy has similar frequency to your trading pattern."
                  }
                </Text>
              </View>
            </View>

            <View style={styles.recommendationCard}>
              <Ionicons name="shield-checkmark-outline" size={20} color="#00ff88" />
              <View style={styles.recommendationContent}>
                <Text style={styles.recommendationTitle}>Risk Management</Text>
                <Text style={styles.recommendationText}>
                  {actual_trading.total_pnl >= 0 
                    ? "Your trading has been profitable. Consider using AI signals to optimize entry/exit timing."
                    : "Consider paper trading the AI strategy first to evaluate its performance before live implementation."
                  }
                </Text>
              </View>
            </View>
          </View>
        </View>
      </View>
    );
  };

  const renderContent = () => {
    switch (selectedView) {
      case 'overview':
        return renderOverviewTab();
      case 'signals':
        return renderSignalsTab();
      case 'performance':
        return renderPerformanceTab();
      default:
        return renderOverviewTab();
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#00ff88" />
        <Text style={styles.loadingText}>Loading comparison data...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
      >
        {renderHeader()}
        {renderViewToggle()}
        {renderContent()}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#0D0E11',
  },
  scrollView: {
    flex: 1,
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0D0E11',
  },
  loadingText: {
    marginTop: 12,
    fontSize: 14,
    color: '#666',
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
  placeholder: {
    width: 40,
  },
  headerTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  headerSubtitle: {
    fontSize: 14,
    color: '#999',
    marginBottom: 20,
  },
  viewToggle: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginBottom: 20,
    backgroundColor: '#1a1b1f',
    borderRadius: 12,
    padding: 4,
  },
  toggleButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 8,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
  },
  toggleButtonActive: {
    backgroundColor: '#00ff88',
  },
  toggleText: {
    fontSize: 12,
    color: '#666',
    fontWeight: '600',
  },
  toggleTextActive: {
    color: '#000',
  },
  tabContent: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  summaryContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: '#1a1b1f',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2a2b2f',
  },
  summaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 12,
  },
  summaryTitle: {
    fontSize: 14,
    color: '#999',
    fontWeight: '600',
  },
  summaryValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 4,
  },
  summaryLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 8,
  },
  summaryPnL: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  summaryStatus: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#ff9500',
  },
  profit: {
    color: '#00ff88',
  },
  loss: {
    color: '#ff4444',
  },
  metricsSection: {
    marginBottom: 24,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 16,
  },
  metricRow: {
    backgroundColor: '#1a1b1f',
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a2b2f',
  },
  metricLabel: {
    fontSize: 14,
    color: '#999',
    marginBottom: 8,
  },
  metricComparison: {
    gap: 4,
  },
  metricValue: {
    fontSize: 14,
    color: '#fff',
    fontWeight: '500',
  },
  periodSection: {
    backgroundColor: '#1a1b1f',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: '#2a2b2f',
  },
  periodText: {
    fontSize: 14,
    color: '#999',
    marginBottom: 4,
  },
  signalChartContainer: {
    marginBottom: 24,
  },
  chartSubtitle: {
    fontSize: 12,
    color: '#666',
    marginBottom: 16,
  },
  chartPlaceholder: {
    backgroundColor: '#1a1b1f',
    borderRadius: 12,
    padding: 40,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#2a2b2f',
  },
  chartPlaceholderText: {
    color: '#666',
    marginTop: 12,
    fontSize: 14,
  },
  recentSignalsSection: {
    marginBottom: 24,
  },
  signalGroup: {
    marginBottom: 20,
  },
  signalGroupTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 12,
  },
  signalItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#1a1b1f',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: '#2a2b2f',
  },
  signalIcon: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#00ff88',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  signalInfo: {
    flex: 1,
  },
  signalType: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#fff',
  },
  signalTime: {
    fontSize: 12,
    color: '#666',
  },
  signalPrice: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#fff',
  },
  performanceSection: {
    marginBottom: 24,
  },
  performanceCard: {
    backgroundColor: '#1a1b1f',
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    borderWidth: 1,
    borderColor: '#2a2b2f',
  },
  performanceTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 16,
  },
  performanceMetrics: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  performanceMetric: {
    alignItems: 'center',
  },
  performanceLabel: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  performanceValue: {
    fontSize: 16,
    fontWeight: 'bold',
    color: '#fff',
  },
  insightsList: {
    gap: 12,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    color: '#999',
    lineHeight: 20,
  },
  recommendationsSection: {
    marginBottom: 24,
  },
  recommendationCard: {
    flexDirection: 'row',
    backgroundColor: '#1a1b1f',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: '#2a2b2f',
    gap: 12,
  },
  recommendationContent: {
    flex: 1,
  },
  recommendationTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 6,
  },
  recommendationText: {
    fontSize: 14,
    color: '#999',
    lineHeight: 20,
  },
});

export default StrategyComparisonScreen;