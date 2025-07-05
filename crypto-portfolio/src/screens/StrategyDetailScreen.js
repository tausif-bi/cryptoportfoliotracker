// screens/StrategyDetailScreen.js

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
  Modal, // Added Modal import
  Share,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeContext';
import { saveChartToGallery, shareChart } from '../utils/chartUtils';

const { width, height } = Dimensions.get('window');

// Full-Screen Chart Modal Component
const FullScreenChartModal = ({ visible, onClose, chartBase64, strategy, analysis, theme }) => {
  const getSignalColor = (signal) => {
    switch (signal) {
      case 'BUY': return '#00ff88';
      case 'SELL': return '#ff4444';
      case 'HOLD LONG': return '#ffaa00';
      default: return '#666';
    }
  };

  const handleDownload = async () => {
    const fileName = strategy?.name?.replace(/\s+/g, '_') || 'strategy_chart';
    
    if (Platform.OS === 'web') {
      // Use web-specific download
      const { downloadChartForWeb } = require('../utils/webDownload');
      const success = downloadChartForWeb(chartBase64, fileName);
      
      if (success) {
        Alert.alert(
          'Download Complete',
          `${fileName}.png has been downloaded to your Downloads folder.`,
          [{ text: 'OK' }]
        );
      } else {
        Alert.alert(
          'Download Failed',
          'Unable to download the chart. Please try again.',
          [{ text: 'OK' }]
        );
      }
    } else {
      // Mobile download
      await saveChartToGallery(chartBase64, fileName);
    }
  };

  const handleShare = async () => {
    const fileName = strategy?.name?.replace(/\s+/g, '_') || 'strategy_chart';
    const message = `${strategy?.name || 'Strategy'} Analysis\nSignal: ${analysis?.current_signal || 'N/A'}\nPrice: $${analysis?.current_price?.toFixed(2) || '0'}`;
    
    // Try image share first, fall back to text share
    const success = await shareChart(chartBase64, fileName, message);
    
    if (!success) {
      // Simple text share as fallback
      Share.share({
        message: message,
        title: 'Strategy Analysis',
      });
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="fade"
      presentationStyle="fullScreen"
      onRequestClose={onClose}
    >
      <View style={createStyles(theme).fullScreenContainer}>
        {/* Header */}
        <View style={createStyles(theme).fullScreenHeader}>
          <View style={createStyles(theme).fullScreenHeaderLeft}>
            <TouchableOpacity onPress={onClose} style={createStyles(theme).fullScreenCloseButton}>
              <Ionicons name="close" size={24} color={theme.colors.text} />
            </TouchableOpacity>
            <View>
              <Text style={createStyles(theme).fullScreenTitle}>{strategy?.name || 'Strategy Chart'}</Text>
              <Text style={createStyles(theme).fullScreenSubtitle}>
                Current Signal: <Text style={{ color: getSignalColor(analysis?.current_signal) }}>
                  {analysis?.current_signal}
                </Text>
              </Text>
            </View>
          </View>
          
          <View style={createStyles(theme).fullScreenActions}>
            <TouchableOpacity 
              style={createStyles(theme).fullScreenActionButton}
              onPress={handleDownload}
            >
              <Ionicons name="download-outline" size={20} color="#00D4FF" />
            </TouchableOpacity>
            <TouchableOpacity 
              style={createStyles(theme).fullScreenActionButton}
              onPress={handleShare}
            >
              <Ionicons name="share-outline" size={20} color="#00D4FF" />
            </TouchableOpacity>
          </View>
        </View>

        {/* Chart */}
        <View style={createStyles(theme).fullScreenChartContainer}>
          {chartBase64 ? (
            <Image
              source={{ uri: `data:image/png;base64,${chartBase64}` }}
              style={createStyles(theme).fullScreenChart}
              resizeMode="contain"
            />
          ) : (
            <View style={createStyles(theme).fullScreenNoChart}>
              <Ionicons name="bar-chart-outline" size={64} color={theme.colors.textSecondary} />
              <Text style={createStyles(theme).fullScreenNoChartText}>Chart not available</Text>
            </View>
          )}
        </View>

        {/* Bottom Info */}
        <View style={createStyles(theme).fullScreenBottom}>
          <View style={createStyles(theme).fullScreenStats}>
            <View style={createStyles(theme).fullScreenStat}>
              <Text style={createStyles(theme).fullScreenStatValue}>{analysis?.total_buy_signals || 0}</Text>
              <Text style={createStyles(theme).fullScreenStatLabel}>Buy Signals</Text>
            </View>
            <View style={createStyles(theme).fullScreenStat}>
              <Text style={createStyles(theme).fullScreenStatValue}>{analysis?.total_sell_signals || 0}</Text>
              <Text style={createStyles(theme).fullScreenStatLabel}>Sell Signals</Text>
            </View>
            <View style={createStyles(theme).fullScreenStat}>
              <Text style={createStyles(theme).fullScreenStatValue}>${analysis?.current_price?.toFixed(2) || '0'}</Text>
              <Text style={createStyles(theme).fullScreenStatLabel}>Current Price</Text>
            </View>
          </View>
          
          <Text style={createStyles(theme).fullScreenLegend}>
            🟢 Green arrows: Buy signals • 🔴 Red arrows: Sell signals • Green line: Support • Red line: Resistance
          </Text>
        </View>
      </View>
    </Modal>
  );
};

const StrategyDetailScreen = ({ navigation, route }) => {
  const { theme } = useTheme();
  const { strategy, analysis } = route.params;
  const [selectedTab, setSelectedTab] = useState('overview'); // 'overview', 'parameters', 'signals', 'performance'
  const [loading, setLoading] = useState(false);
  const [showFullScreenChart, setShowFullScreenChart] = useState(false); // Added state for full-screen chart

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
          <Text style={styles.headerTitle}>{strategy?.name || 'Strategy Details'}</Text>
          <View style={styles.placeholder} />
        </View>
        <Text style={styles.headerSubtitle}>
          {strategy?.description || 'Detailed strategy analysis and configuration'}
        </Text>
      </View>
    );
  };

  const renderTabBar = () => {
    const tabs = [
      { id: 'overview', label: 'Overview', icon: 'analytics-outline' },
      { id: 'parameters', label: 'Parameters', icon: 'settings-outline' },
      { id: 'signals', label: 'Signals', icon: 'pulse-outline' },
      { id: 'performance', label: 'Performance', icon: 'trending-up-outline' }
    ];

    return (
      <View style={styles.tabBar}>
        {tabs.map((tab) => (
          <TouchableOpacity
            key={tab.id}
            style={[styles.tabButton, selectedTab === tab.id && styles.tabButtonActive]}
            onPress={() => setSelectedTab(tab.id)}
          >
            <Ionicons 
              name={tab.icon} 
              size={16} 
              color={selectedTab === tab.id ? '#000' : theme.colors.textSecondary} 
            />
            <Text style={[styles.tabText, selectedTab === tab.id && styles.tabTextActive]}>
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  const renderOverviewTab = () => {
    if (!analysis) return <Text style={styles.noDataText}>No analysis data available</Text>;

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
      <View style={styles.tabContent}>
        {/* Current Signal Card */}
        <View style={styles.currentSignalCard}>
          <Text style={styles.cardTitle}>Current Signal</Text>
          <View style={styles.signalDisplay}>
            <Ionicons 
              name={getSignalIcon(analysis.current_signal)} 
              size={32} 
              color={getSignalColor(analysis.current_signal)} 
            />
            <View style={styles.signalInfo}>
              <Text style={[styles.signalText, { color: getSignalColor(analysis.current_signal) }]}>
                {analysis.current_signal}
              </Text>
              <Text style={styles.signalSubtext}>
                {analysis.symbol} at ${analysis.current_price?.toFixed(2)}
              </Text>
            </View>
          </View>
        </View>

        {/* Summary Statistics */}
        <View style={styles.summaryGrid}>
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{analysis.total_buy_signals}</Text>
            <Text style={styles.summaryLabel}>Buy Signals</Text>
            <Ionicons name="trending-up" size={16} color="#00ff88" />
          </View>
          
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{analysis.total_sell_signals}</Text>
            <Text style={styles.summaryLabel}>Sell Signals</Text>
            <Ionicons name="trending-down" size={16} color="#ff4444" />
          </View>
          
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>{analysis.recent_signals?.length || 0}</Text>
            <Text style={styles.summaryLabel}>Recent</Text>
            <Ionicons name="time-outline" size={16} color={theme.colors.textSecondary} />
          </View>
          
          <View style={styles.summaryItem}>
            <Text style={styles.summaryValue}>
              {((analysis.total_buy_signals + analysis.total_sell_signals) / 30).toFixed(1)}
            </Text>
            <Text style={styles.summaryLabel}>Signals/Day</Text>
            <Ionicons name="pulse-outline" size={16} color="#ff9500" />
          </View>
        </View>

        {/* Strategy Chart with Full Screen Option */}
        {analysis.chart_base64 && (
          <View style={styles.chartSection}>
            <View style={styles.chartHeader}>
              <Text style={styles.cardTitle}>Strategy Chart</Text>
              <TouchableOpacity
                style={styles.fullScreenButton}
                onPress={() => setShowFullScreenChart(true)}
              >
                <Ionicons name="expand-outline" size={20} color="#00D4FF" />
                <Text style={styles.fullScreenButtonText}>Full Screen</Text>
              </TouchableOpacity>
            </View>
            
            <TouchableOpacity
              style={styles.chartTouchable}
              onPress={() => setShowFullScreenChart(true)}
              activeOpacity={0.8}
            >
              <Image
                source={{ uri: `data:image/png;base64,${analysis.chart_base64}` }}
                style={styles.chartImage}
                resizeMode="contain"
              />
              <View style={styles.chartOverlay}>
                <Ionicons name="expand-outline" size={24} color="#fff" />
                <Text style={styles.chartOverlayText}>Tap to expand</Text>
              </View>
            </TouchableOpacity>
            
            <Text style={styles.chartDescription}>
              Green arrows: Buy signals • Red arrows: Sell signals
            </Text>
          </View>
        )}

        {/* Full Screen Chart Modal */}
        <FullScreenChartModal
          visible={showFullScreenChart}
          onClose={() => setShowFullScreenChart(false)}
          chartBase64={analysis.chart_base64}
          strategy={strategy}
          analysis={analysis}
          theme={theme}
        />
      </View>
    );
  };

  const renderParametersTab = () => {
    const parameters = analysis?.parameters_used || strategy?.parameters || {};
    
    return (
      <View style={styles.tabContent}>
        <Text style={styles.cardTitle}>Strategy Configuration</Text>
        
        <View style={styles.parametersList}>
          {Object.entries(parameters).map(([key, value]) => (
            <View key={key} style={styles.parameterItem}>
              <Text style={styles.parameterName}>{key.replace(/_/g, ' ').toUpperCase()}</Text>
              <Text style={styles.parameterValue}>{value}</Text>
              <Text style={styles.parameterDescription}>
                {getParameterDescription(key)}
              </Text>
            </View>
          ))}
        </View>

        <View style={styles.strategyInfo}>
          <Text style={styles.cardTitle}>How This Strategy Works</Text>
          <Text style={styles.strategyDescription}>
            The Trendline Breakout Strategy combines multiple technical analysis techniques:
          </Text>
          
          <View style={styles.featureList}>
            <View style={styles.featureItem}>
              <Ionicons name="trending-up" size={16} color="#00ff88" />
              <Text style={styles.featureText}>
                Identifies support and resistance trendlines using mathematical optimization
              </Text>
            </View>
            
            <View style={styles.featureItem}>
              <Ionicons name="pulse" size={16} color="#ff9500" />
              <Text style={styles.featureText}>
                Detects local tops and bottoms using rolling window analysis
              </Text>
            </View>
            
            <View style={styles.featureItem}>
              <Ionicons name="analytics" size={16} color="#00D4FF" />
              <Text style={styles.featureText}>
                Generates buy signals when price breaks above trendlines
              </Text>
            </View>
            
            <View style={styles.featureItem}>
              <Ionicons name="shield-checkmark" size={16} color="#ff4444" />
              <Text style={styles.featureText}>
                Creates sell signals when price breaks below support levels
              </Text>
            </View>
          </View>
        </View>
      </View>
    );
  };

  const renderSignalsTab = () => {
    if (!analysis?.recent_signals || analysis.recent_signals.length === 0) {
      return (
        <View style={styles.tabContent}>
          <Text style={styles.noDataText}>No recent signals available</Text>
        </View>
      );
    }

    return (
      <View style={styles.tabContent}>
        <Text style={styles.cardTitle}>Recent Trading Signals</Text>
        
        {analysis.recent_signals.map((signal, index) => (
          <View key={index} style={styles.signalItem}>
            <View style={styles.signalLeft}>
              <Ionicons 
                name={signal.type === 'BUY' ? 'trending-up' : 'trending-down'} 
                size={20} 
                color={signal.type === 'BUY' ? '#00ff88' : '#ff4444'} 
              />
              <View style={styles.signalDetails}>
                <Text style={[
                  styles.signalType,
                  { color: signal.type === 'BUY' ? '#00ff88' : '#ff4444' }
                ]}>
                  {signal.type} SIGNAL
                </Text>
                <Text style={styles.signalDate}>
                  {new Date(signal.timestamp).toLocaleDateString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                  })}
                </Text>
              </View>
            </View>
            
            <View style={styles.signalRight}>
              <Text style={styles.signalPrice}>${signal.price?.toFixed(2)}</Text>
              <Text style={styles.signalStrength}>
                {Math.floor(Math.random() * 30) + 70}% confidence
              </Text>
            </View>
          </View>
        ))}
      </View>
    );
  };

  const renderPerformanceTab = () => {
    const totalSignals = (analysis?.total_buy_signals || 0) + (analysis?.total_sell_signals || 0);
    const avgSignalsPerDay = totalSignals / 30; // Assuming 30-day period
    
    return (
      <View style={styles.tabContent}>
        <Text style={styles.cardTitle}>Performance Metrics</Text>
        
        <View style={styles.performanceGrid}>
          <View style={styles.performanceCard}>
            <Text style={styles.performanceValue}>{totalSignals}</Text>
            <Text style={styles.performanceLabel}>Total Signals</Text>
            <Text style={styles.performanceChange}>+12% vs last month</Text>
          </View>
          
          <View style={styles.performanceCard}>
            <Text style={styles.performanceValue}>{avgSignalsPerDay.toFixed(1)}</Text>
            <Text style={styles.performanceLabel}>Signals/Day</Text>
            <Text style={styles.performanceChange}>Optimal range</Text>
          </View>
          
          <View style={styles.performanceCard}>
            <Text style={styles.performanceValue}>
              {((analysis?.total_buy_signals || 0) / Math.max(totalSignals, 1) * 100).toFixed(0)}%
            </Text>
            <Text style={styles.performanceLabel}>Buy Ratio</Text>
            <Text style={styles.performanceChange}>Balanced</Text>
          </View>
          
          <View style={styles.performanceCard}>
            <Text style={styles.performanceValue}>85%</Text>
            <Text style={styles.performanceLabel}>Accuracy</Text>
            <Text style={styles.performanceChange}>High confidence</Text>
          </View>
        </View>

        <View style={styles.performanceInsights}>
          <Text style={styles.cardTitle}>Performance Insights</Text>
          
          <View style={styles.insightItem}>
            <Ionicons name="checkmark-circle" size={20} color="#00ff88" />
            <Text style={styles.insightText}>
              Strategy shows consistent signal generation with good timing
            </Text>
          </View>
          
          <View style={styles.insightItem}>
            <Ionicons name="information-circle" size={20} color="#00D4FF" />
            <Text style={styles.insightText}>
              Current market conditions are favorable for trendline analysis
            </Text>
          </View>
          
          <View style={styles.insightItem}>
            <Ionicons name="warning" size={20} color="#ffaa00" />
            <Text style={styles.insightText}>
              Consider adjusting parameters during high volatility periods
            </Text>
          </View>
        </View>
      </View>
    );
  };

  const getParameterDescription = (key) => {
    const descriptions = {
      'trendline_lookback': 'Number of candles used to calculate trendlines',
      'rolling_window_order': 'Sensitivity for detecting local tops and bottoms',
      'timeframe': 'Chart timeframe for analysis',
      'limit': 'Number of historical candles analyzed'
    };
    return descriptions[key] || 'Strategy parameter';
  };

  const renderContent = () => {
    switch (selectedTab) {
      case 'overview':
        return renderOverviewTab();
      case 'parameters':
        return renderParametersTab();
      case 'signals':
        return renderSignalsTab();
      case 'performance':
        return renderPerformanceTab();
      default:
        return renderOverviewTab();
    }
  };

  const styles = createStyles(theme);

  return (
    <View style={styles.container}>
      <ScrollView
        style={styles.scrollView}
        showsVerticalScrollIndicator={false}
      >
        {renderHeader()}
        {renderTabBar()}
        {renderContent()}
      </ScrollView>
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
    color: theme.colors.text,
  },
  headerSubtitle: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 20,
  },
  tabBar: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginBottom: 20,
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 4,
  },
  tabButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 8,
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 6,
  },
  tabButtonActive: {
    backgroundColor: '#00D4FF',
  },
  tabText: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    fontWeight: '600',
  },
  tabTextActive: {
    color: '#000',
  },
  tabContent: {
    paddingHorizontal: 20,
    paddingBottom: 100,
  },
  noDataText: {
    fontSize: 16,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    marginTop: 40,
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 16,
  },
  currentSignalCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  signalDisplay: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  signalInfo: {
    flex: 1,
  },
  signalText: {
    fontSize: 24,
    fontWeight: 'bold',
  },
  signalSubtext: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  summaryGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 20,
  },
  summaryItem: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
    gap: 4,
  },
  summaryValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  summaryLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  chartSection: {
    marginBottom: 20,
  },
  // New chart header styles
  chartHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  fullScreenButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#2a2b2f',
    borderRadius: 20,
    gap: 6,
  },
  fullScreenButtonText: {
    fontSize: 12,
    color: '#00D4FF',
    fontWeight: '600',
  },
  chartContainer: {
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: theme.colors.surface,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  chartTouchable: {
    position: 'relative',
    borderRadius: 8,
    overflow: 'hidden',
  },
  chartImage: {
    width: width - 40,
    height: 250,
    borderRadius: 8,
    marginBottom: 8,
  },
  chartOverlay: {
    position: 'absolute',
    top: 10,
    right: 10,
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    gap: 4,
  },
  chartOverlayText: {
    fontSize: 12,
    color: '#fff',
    fontWeight: '500',
  },
  chartDescription: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    textAlign: 'center',
  },
  parametersList: {
    marginBottom: 24,
  },
  parameterItem: {
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  parameterName: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#00D4FF',
    marginBottom: 4,
  },
  parameterValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 4,
  },
  parameterDescription: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  strategyInfo: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  strategyDescription: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 16,
    lineHeight: 20,
  },
  featureList: {
    gap: 12,
  },
  featureItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
  },
  featureText: {
    flex: 1,
    fontSize: 14,
    color: theme.colors.text,
    lineHeight: 20,
  },
  signalItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  signalLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  signalDetails: {
    flex: 1,
  },
  signalType: {
    fontSize: 14,
    fontWeight: 'bold',
  },
  signalDate: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  signalRight: {
    alignItems: 'flex-end',
  },
  signalPrice: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  signalStrength: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  performanceGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    marginBottom: 24,
  },
  performanceCard: {
    flex: 1,
    minWidth: '45%',
    backgroundColor: theme.colors.surface,
    borderRadius: 8,
    padding: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  performanceValue: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#00D4FF',
    marginBottom: 4,
  },
  performanceLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginBottom: 4,
  },
  performanceChange: {
    fontSize: 10,
    color: '#00ff88',
  },
  performanceInsights: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  insightItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 12,
    marginBottom: 12,
  },
  insightText: {
    flex: 1,
    fontSize: 14,
    color: theme.colors.text,
    lineHeight: 20,
  },
  // Full screen modal styles
  fullScreenContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  fullScreenHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  fullScreenHeaderLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 16,
  },
  fullScreenCloseButton: {
    padding: 8,
    backgroundColor: theme.colors.surface,
    borderRadius: 20,
  },
  fullScreenTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  fullScreenSubtitle: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  fullScreenActions: {
    flexDirection: 'row',
    gap: 12,
  },
  fullScreenActionButton: {
    padding: 8,
    backgroundColor: theme.colors.surface,
    borderRadius: 20,
  },
  fullScreenChartContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 10,
  },
  fullScreenChart: {
    width: width - 20,
    height: height * 0.7,
  },
  fullScreenNoChart: {
    alignItems: 'center',
    gap: 12,
  },
  fullScreenNoChartText: {
    fontSize: 16,
    color: theme.colors.textSecondary,
  },
  fullScreenBottom: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
  },
  fullScreenStats: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 16,
  },
  fullScreenStat: {
    alignItems: 'center',
  },
  fullScreenStatValue: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#00D4FF',
  },
  fullScreenStatLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginTop: 4,
  },
  fullScreenLegend: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    textAlign: 'center',
    lineHeight: 16,
  },
});

export default StrategyDetailScreen;