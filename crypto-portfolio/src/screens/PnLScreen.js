import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  RefreshControl,
  Dimensions,
  Alert,
  Modal,
  Image,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeContext';

const { width } = Dimensions.get('window');

// AI Overlay Toggle Component (will be moved inside main component)

// Trade Comparison Modal Component
const TradeComparisonModal = ({ visible, onClose, trade, aiSignals }) => {
  const [showChart, setShowChart] = useState(false);
  const [chartData, setChartData] = useState(null);
  const [chartLoading, setChartLoading] = useState(false);

  const fetchTradeChart = async () => {
    setChartLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/strategies/trendline_breakout/signals', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: trade.symbol || 'BTC/USDT',
          timeframe: '1h',
          limit: 200
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setChartData(data.signals);
        }
      }
    } catch (error) {
      console.error('Error fetching chart data:', error);
    } finally {
      setChartLoading(false);
    }
  };

  useEffect(() => {
    if (visible && showChart && !chartData) {
      fetchTradeChart();
    }
  }, [visible, showChart]);

  if (!trade) return null;

  const buyDate = new Date(trade.buy_timestamp).toLocaleDateString();
  const sellDate = new Date(trade.sell_timestamp).toLocaleDateString();
  
  // Find AI signals near the trade dates
  const nearbyAIBuys = aiSignals?.buy_signals?.filter(signal => {
    const signalDate = new Date(signal.timestamp);
    const buyDate = new Date(trade.buy_timestamp);
    const timeDiff = Math.abs(signalDate - buyDate) / (1000 * 60 * 60 * 24);
    return timeDiff <= 7;
  }) || [];

  const nearbyAISells = aiSignals?.sell_signals?.filter(signal => {
    const signalDate = new Date(signal.timestamp);
    const sellDate = new Date(trade.sell_timestamp);
    const timeDiff = Math.abs(signalDate - sellDate) / (1000 * 60 * 60 * 24);
    return timeDiff <= 7;
  }) || [];

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={onClose}
    >
      <View style={styles.modalContainer}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Trade Analysis</Text>
          <TouchableOpacity onPress={onClose} style={styles.modalCloseButton}>
            <Ionicons name="close" size={24} color="#fff" />
          </TouchableOpacity>
        </View>

        <ScrollView style={styles.modalContent}>
          {/* Trade Details */}
          <View style={styles.tradeDetailsCard}>
            <Text style={styles.cardTitle}>Your Trade</Text>
            <View style={styles.tradeDetailRow}>
              <Text style={styles.detailLabel}>Symbol:</Text>
              <Text style={styles.detailValue}>{trade.symbol}</Text>
            </View>
            <View style={styles.tradeDetailRow}>
              <Text style={styles.detailLabel}>Buy Date:</Text>
              <Text style={styles.detailValue}>{buyDate}</Text>
            </View>
            <View style={styles.tradeDetailRow}>
              <Text style={styles.detailLabel}>Sell Date:</Text>
              <Text style={styles.detailValue}>{sellDate}</Text>
            </View>
            <View style={styles.tradeDetailRow}>
              <Text style={styles.detailLabel}>P&L:</Text>
              <Text style={[
                styles.detailValue,
                trade.pnl >= 0 ? styles.profit : styles.loss
              ]}>
                {trade.pnl >= 0 ? '+' : ''}${trade.pnl}
              </Text>
            </View>
          </View>

          {/* AI Comparison */}
          <View style={styles.aiComparisonCard}>
            <Text style={styles.cardTitle}>AI Signal Comparison</Text>
            
            {nearbyAIBuys.length > 0 ? (
              <View style={styles.aiSignalSection}>
                <Text style={styles.aiSignalTitle}>AI Buy Signals (±7 days)</Text>
                {nearbyAIBuys.map((signal, index) => (
                  <View key={index} style={styles.aiSignalItem}>
                    <Ionicons name="trending-up" size={16} color="#00ff88" />
                    <Text style={styles.aiSignalDate}>
                      {new Date(signal.timestamp).toLocaleDateString()}
                    </Text>
                    <Text style={styles.aiSignalPrice}>
                      ${signal.price?.toFixed(2)}
                    </Text>
                  </View>
                ))}
              </View>
            ) : (
              <Text style={styles.noSignalsText}>No AI buy signals found near your buy date</Text>
            )}

            {nearbyAISells.length > 0 ? (
              <View style={styles.aiSignalSection}>
                <Text style={styles.aiSignalTitle}>AI Sell Signals (±7 days)</Text>
                {nearbyAISells.map((signal, index) => (
                  <View key={index} style={styles.aiSignalItem}>
                    <Ionicons name="trending-down" size={16} color="#ff4444" />
                    <Text style={styles.aiSignalDate}>
                      {new Date(signal.timestamp).toLocaleDateString()}
                    </Text>
                    <Text style={styles.aiSignalPrice}>
                      ${signal.price?.toFixed(2)}
                    </Text>
                  </View>
                ))}
              </View>
            ) : (
              <Text style={styles.noSignalsText}>No AI sell signals found near your sell date</Text>
            )}
          </View>

          {/* Chart Toggle */}
          <TouchableOpacity
            style={styles.chartToggleButton}
            onPress={() => setShowChart(!showChart)}
          >
            <Ionicons 
              name={showChart ? "chevron-up" : "chevron-down"} 
              size={20} 
              color="#00ff88" 
            />
            <Text style={styles.chartToggleText}>
              {showChart ? 'Hide' : 'Show'} Strategy Chart
            </Text>
          </TouchableOpacity>

          {/* Chart Display */}
          {showChart && (
            <View style={styles.chartContainer}>
              {chartLoading ? (
                <View style={styles.chartLoading}>
                  <ActivityIndicator size="large" color="#00ff88" />
                  <Text style={styles.chartLoadingText}>Loading chart...</Text>
                </View>
              ) : chartData ? (
                <View style={styles.chartDataContainer}>
                  <Text style={styles.chartDataTitle}>AI Strategy Analysis</Text>
                  <Text style={styles.chartDataSubtitle}>
                    Current Signal: {chartData.current_signal}
                  </Text>
                  <Text style={styles.chartDataSubtitle}>
                    Price: ${chartData.current_price?.toFixed(2)}
                  </Text>
                </View>
              ) : (
                <Text style={styles.chartErrorText}>Chart data not available</Text>
              )}
            </View>
          )}
        </ScrollView>
      </View>
    </Modal>
  );
};

// Main PnL Screen Component
const PnLScreen = ({ navigation }) => {
  const { theme } = useTheme();
  const styles = createStyles(theme);
  
  // AI Overlay Toggle Component (moved inside to access styles)
  const AIOverlayToggle = ({ enabled, onToggle, loading }) => {
    return (
      <TouchableOpacity
        style={[styles.aiToggle, enabled && styles.aiToggleEnabled]}
        onPress={onToggle}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator size="small" color="#fff" />
        ) : (
          <Ionicons 
            name={enabled ? "robot" : "robot-outline"} 
            size={16} 
            color={enabled ? "#000" : "#00ff88"} 
          />
        )}
        <Text style={[styles.aiToggleText, enabled && styles.aiToggleTextEnabled]}>
          AI Signals
        </Text>
      </TouchableOpacity>
    );
  };
  
  // Existing state variables
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [pnlData, setPnlData] = useState(null);
  const [selectedView, setSelectedView] = useState('trades');
  const [expandedTrade, setExpandedTrade] = useState(null);
  const [dailyPnL, setDailyPnL] = useState([]);

  // New AI overlay state
  const [aiOverlayEnabled, setAiOverlayEnabled] = useState(false);
  const [aiSignals, setAiSignals] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [selectedTradeForAnalysis, setSelectedTradeForAnalysis] = useState(null);
  const [showTradeModal, setShowTradeModal] = useState(false);

  const fetchPnLData = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/pnl/summary');
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const contentType = response.headers.get("content-type");
      if (!contentType || !contentType.includes("application/json")) {
        throw new TypeError("Response was not JSON!");
      }
      
      const data = await response.json();
      
      if (data.success !== false) {
        setPnlData(data);
      } else {
        console.error('P&L data error:', data.error);
        setPnlData({
          summary: {
            total_pnl: 0,
            total_trades: 0,
            winning_trades: 0,
            losing_trades: 0,
            win_rate: 0,
            average_win: 0,
            average_loss: 0,
            best_trade: null,
            worst_trade: null,
          },
          trades: []
        });
      }
      
      try {
        const dailyResponse = await fetch('http://localhost:5000/api/pnl/daily');
        if (dailyResponse.ok) {
          const dailyData = await dailyResponse.json();
          if (dailyData.success !== false) {
            setDailyPnL(dailyData.daily_pnl || []);
          }
        }
      } catch (dailyError) {
        console.error('Error fetching daily P&L:', dailyError);
        setDailyPnL([]);
      }
    } catch (error) {
      console.error('Error fetching P&L data:', error);
      setPnlData({
        summary: {
          total_pnl: 0,
          total_trades: 0,
          winning_trades: 0,
          losing_trades: 0,
          win_rate: 0,
          average_win: 0,
          average_loss: 0,
          best_trade: null,
          worst_trade: null,
        },
        trades: []
      });
      setDailyPnL([]);
      
      Alert.alert(
        'Connection Error', 
        'Could not connect to the server. Please make sure the backend is running on http://localhost:5000',
        [{ text: 'OK' }]
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  // Fetch AI signals
  const fetchAISignals = async () => {
    setAiLoading(true);
    try {
      const response = await fetch('http://localhost:5000/api/strategies/trendline_breakout/signals', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          symbol: 'BTC/USDT',
          timeframe: '1h',
          limit: 200
        })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setAiSignals(data.signals);
        }
      }
    } catch (error) {
      console.error('Error fetching AI signals:', error);
    } finally {
      setAiLoading(false);
    }
  };

  // Toggle AI overlay
  const toggleAIOverlay = () => {
    if (!aiOverlayEnabled && !aiSignals) {
      fetchAISignals();
    }
    setAiOverlayEnabled(!aiOverlayEnabled);
  };

  // Open trade analysis modal
  const openTradeAnalysis = (trade) => {
    setSelectedTradeForAnalysis(trade);
    setShowTradeModal(true);
  };

  useEffect(() => {
    fetchPnLData();
  }, []);

  const onRefresh = () => {
    setRefreshing(true);
    fetchPnLData();
  };

  const formatCurrency = (value) => {
    const prefix = value >= 0 ? '+$' : '-$';
    return prefix + Math.abs(value).toFixed(2);
  };

  const formatPercentage = (value) => {
    const prefix = value >= 0 ? '+' : '';
    return prefix + value.toFixed(2) + '%';
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString();
  };

  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-US', { 
      month: 'short', 
      day: 'numeric',
      year: 'numeric'
    });
  };

  const renderHeader = () => {
    const summary = pnlData?.summary || {};
    
    return (
      <View style={styles.header}>
        <View style={styles.headerTop}>
          <TouchableOpacity 
            style={styles.backButton}
            onPress={() => navigation.goBack()}
          >
            <Ionicons name="arrow-back" size={24} color={theme.colors.text} />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Profit & Loss</Text>
          <View style={styles.headerActions}>
            <AIOverlayToggle 
              enabled={aiOverlayEnabled}
              onToggle={toggleAIOverlay}
              loading={aiLoading}
            />
            <TouchableOpacity 
              style={styles.exportButton}
              onPress={handleExport}
            >
              <Ionicons name="download-outline" size={24} color="#00ff88" />
            </TouchableOpacity>
          </View>
        </View>
        <Text style={styles.headerSubtitle}>
          {aiOverlayEnabled ? 'Track your trading performance with AI insights' : 'Track your trading performance'}
        </Text>
        
        <View style={styles.totalPnLCard}>
          <Text style={styles.totalPnLLabel}>Total P&L</Text>
          <Text style={[
            styles.totalPnLValue,
            summary.total_pnl >= 0 ? styles.profit : styles.loss
          ]}>
            {formatCurrency(summary.total_pnl || 0)}
          </Text>
          <View style={styles.totalPnLStats}>
            <Text style={styles.totalPnLSubtext}>
              {summary.total_trades || 0} trades
            </Text>
            <Text style={styles.totalPnLDivider}>•</Text>
            <Text style={[
              styles.totalPnLSubtext,
              summary.win_rate >= 50 ? styles.profitText : styles.lossText
            ]}>
              {summary.win_rate || 0}% win rate
            </Text>
          </View>
          
          {aiOverlayEnabled && aiSignals && (
            <View style={styles.aiInsightCard}>
              <Ionicons name="robot-outline" size={16} color="#00ff88" />
              <Text style={styles.aiInsightText}>
                AI Current Signal: {aiSignals.current_signal || 'ANALYZING'}
              </Text>
            </View>
          )}
        </View>
      </View>
    );
  };

  const renderSummaryCards = () => {
    const summary = pnlData?.summary || {};
    
    return (
      <View style={styles.summaryContainer}>
        <View style={styles.summaryCard}>
          <View style={styles.summaryIconContainer}>
            <Ionicons name="trending-up" size={24} color="#00ff88" />
          </View>
          <Text style={styles.summaryCardValue}>{summary.winning_trades || 0}</Text>
          <Text style={styles.summaryCardLabel}>Winning</Text>
          <Text style={styles.summaryCardSubtext}>
            Avg: {formatCurrency(summary.average_win || 0)}
          </Text>
        </View>
        
        <View style={styles.summaryCard}>
          <View style={styles.summaryIconContainer}>
            <Ionicons name="trending-down" size={24} color="#ff4444" />
          </View>
          <Text style={styles.summaryCardValue}>{summary.losing_trades || 0}</Text>
          <Text style={styles.summaryCardLabel}>Losing</Text>
          <Text style={styles.summaryCardSubtext}>
            Avg: {formatCurrency(summary.average_loss || 0)}
          </Text>
        </View>
      </View>
    );
  };

  const renderBestWorstTrades = () => {
    const summary = pnlData?.summary || {};
    if (!summary.best_trade || !summary.worst_trade) return null;

    return (
      <View style={styles.bestWorstContainer}>
        <View style={[styles.bestWorstCard, styles.bestCard]}>
          <Text style={styles.bestWorstTitle}>Best Trade</Text>
          <Text style={styles.bestWorstSymbol}>{summary.best_trade.symbol}</Text>
          <Text style={[styles.bestWorstValue, styles.profit]}>
            {formatCurrency(summary.best_trade.pnl)}
          </Text>
          <Text style={styles.bestWorstPercent}>
            {formatPercentage(summary.best_trade.pnl_percentage)}
          </Text>
        </View>

        <View style={[styles.bestWorstCard, styles.worstCard]}>
          <Text style={styles.bestWorstTitle}>Worst Trade</Text>
          <Text style={styles.bestWorstSymbol}>{summary.worst_trade.symbol}</Text>
          <Text style={[styles.bestWorstValue, styles.loss]}>
            {formatCurrency(summary.worst_trade.pnl)}
          </Text>
          <Text style={styles.bestWorstPercent}>
            {formatPercentage(summary.worst_trade.pnl_percentage)}
          </Text>
        </View>
      </View>
    );
  };

  const renderViewToggle = () => {
    return (
      <View style={styles.viewToggle}>
        <TouchableOpacity
          style={[styles.toggleButton, selectedView === 'trades' && styles.toggleButtonActive]}
          onPress={() => setSelectedView('trades')}
        >
          <Text style={[styles.toggleText, selectedView === 'trades' && styles.toggleTextActive]}>
            Trades
          </Text>
        </TouchableOpacity>
        
        <TouchableOpacity
          style={[styles.toggleButton, selectedView === 'daily' && styles.toggleButtonActive]}
          onPress={() => setSelectedView('daily')}
        >
          <Text style={[styles.toggleText, selectedView === 'daily' && styles.toggleTextActive]}>
            Daily
          </Text>
        </TouchableOpacity>
      </View>
    );
  };

  const renderTradeItem = (trade, index) => {
    const isExpanded = expandedTrade === index;
    
    return (
      <TouchableOpacity
        key={`trade-${index}`}
        style={styles.tradeItem}
        onPress={() => setExpandedTrade(isExpanded ? null : index)}
        activeOpacity={0.7}
      >
        <View style={styles.tradeHeader}>
          <View style={styles.tradeBasicInfo}>
            <Text style={styles.tradeSymbol}>{trade.symbol}</Text>
            <Text style={styles.tradeQuantity}>
              {trade.quantity.toFixed(4)} units
            </Text>
          </View>
          
          <View style={styles.tradePnL}>
            <Text style={[
              styles.tradePnLValue,
              trade.pnl >= 0 ? styles.profit : styles.loss
            ]}>
              {formatCurrency(trade.pnl)}
            </Text>
            <Text style={[
              styles.tradePnLPercent,
              trade.pnl >= 0 ? styles.profitText : styles.lossText
            ]}>
              {formatPercentage(trade.pnl_percentage)}
            </Text>
          </View>
          
          {aiOverlayEnabled && (
            <TouchableOpacity
              style={styles.aiAnalysisButton}
              onPress={() => openTradeAnalysis(trade)}
            >
              <Ionicons name="analytics-outline" size={16} color="#00ff88" />
            </TouchableOpacity>
          )}
        </View>

        {isExpanded && (
          <View style={styles.tradeDetails}>
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Buy Price:</Text>
              <Text style={styles.detailValue}>${trade.buy_price.toFixed(2)}</Text>
            </View>
            
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Sell Price:</Text>
              <Text style={styles.detailValue}>${trade.sell_price.toFixed(2)}</Text>
            </View>
            
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Buy Value:</Text>
              <Text style={styles.detailValue}>${trade.buy_value.toFixed(2)}</Text>
            </View>
            
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Sell Value:</Text>
              <Text style={styles.detailValue}>${trade.sell_value.toFixed(2)}</Text>
            </View>
            
            <View style={styles.detailRow}>
              <Text style={styles.detailLabel}>Holding Period:</Text>
              <Text style={styles.detailValue}>{trade.holding_period_hours.toFixed(1)}h</Text>
            </View>
            
            <View style={styles.timestampRow}>
              <Text style={styles.timestampLabel}>Buy: {formatTimestamp(trade.buy_timestamp)}</Text>
              <Text style={styles.timestampLabel}>Sell: {formatTimestamp(trade.sell_timestamp)}</Text>
            </View>
            
            {aiOverlayEnabled && (
              <TouchableOpacity
                style={styles.fullAnalysisButton}
                onPress={() => openTradeAnalysis(trade)}
              >
                <Ionicons name="robot-outline" size={16} color="#000" />
                <Text style={styles.fullAnalysisButtonText}>Compare with AI</Text>
              </TouchableOpacity>
            )}
          </View>
        )}
      </TouchableOpacity>
    );
  };

  const renderDailyItem = (day, index) => {
    const winRate = day.trades > 0 ? (day.winning_trades / day.trades * 100).toFixed(1) : 0;
    
    return (
      <View key={`daily-${index}`} style={styles.dailyItem}>
        <View style={styles.dailyHeader}>
          <Text style={styles.dailyDate}>{formatDate(day.date)}</Text>
          <Text style={[
            styles.dailyPnL,
            day.pnl >= 0 ? styles.profit : styles.loss
          ]}>
            {formatCurrency(day.pnl)}
          </Text>
        </View>
        
        <View style={styles.dailyStats}>
          <Text style={styles.dailyStatText}>
            {day.trades} trades • {winRate}% win rate
          </Text>
          <Text style={styles.dailyStatText}>
            {day.winning_trades}W / {day.losing_trades}L
          </Text>
        </View>
      </View>
    );
  };

  const handleExport = async () => {
    try {
      const response = await fetch('http://localhost:5000/api/pnl/export');
      const data = await response.json();
      
      Alert.alert(
        'Export P&L Data',
        'P&L data has been prepared for export. In a production app, this would save to a file or share.',
        [{ text: 'OK' }]
      );
    } catch (error) {
      Alert.alert('Error', 'Failed to export P&L data');
    }
  };

  const renderEmptyState = () => {
    return (
      <View style={styles.emptyState}>
        <Ionicons name="bar-chart-outline" size={64} color="#666" />
        <Text style={styles.emptyStateText}>No trades found</Text>
        <Text style={styles.emptyStateSubtext}>
          Your completed trades will appear here
        </Text>
      </View>
    );
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#00ff88" />
        <Text style={styles.loadingText}>Loading P&L data...</Text>
      </View>
    );
  }

  const hasTradeData = pnlData?.trades && pnlData.trades.length > 0;
  const hasDailyData = dailyPnL && dailyPnL.length > 0;

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
        
        {hasTradeData ? (
          <>
            {renderSummaryCards()}
            {renderBestWorstTrades()}
            {renderViewToggle()}
            
            <View style={styles.contentContainer}>
              {selectedView === 'trades' ? (
                <>
                  <Text style={styles.sectionTitle}>
                    Trade History
                    {aiOverlayEnabled && <Text style={styles.aiIndicator}> • AI Analysis Enabled</Text>}
                  </Text>
                  {pnlData.trades.map((trade, index) => renderTradeItem(trade, index))}
                </>
              ) : (
                <>
                  <Text style={styles.sectionTitle}>Daily P&L</Text>
                  {hasDailyData ? (
                    dailyPnL.map((day, index) => renderDailyItem(day, index))
                  ) : (
                    renderEmptyState()
                  )}
                </>
              )}
            </View>
          </>
        ) : (
          <View style={styles.contentContainer}>
            {renderEmptyState()}
          </View>
        )}
      </ScrollView>

      {/* Trade Comparison Modal */}
      <TradeComparisonModal
        visible={showTradeModal}
        onClose={() => setShowTradeModal(false)}
        trade={selectedTradeForAnalysis}
        aiSignals={aiSignals}
      />
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
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  exportButton: {
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
  totalPnLCard: {
    backgroundColor: theme.colors.surface,
    padding: 24,
    borderRadius: 16,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  totalPnLLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 8,
  },
  totalPnLValue: {
    fontSize: 40,
    fontWeight: 'bold',
    marginBottom: 12,
  },
  totalPnLStats: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  totalPnLSubtext: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  totalPnLDivider: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginHorizontal: 8,
  },
  profit: {
    color: '#00ff88',
  },
  loss: {
    color: '#ff4444',
  },
  profitText: {
    color: '#00ff88',
  },
  lossText: {
    color: '#ff4444',
  },
  // AI Toggle Styles
  aiToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: '#00ff88',
    backgroundColor: 'transparent',
    gap: 6,
  },
  aiToggleEnabled: {
    backgroundColor: '#00ff88',
  },
  aiToggleText: {
    fontSize: 12,
    color: '#00ff88',
    fontWeight: '600',
  },
  aiToggleTextEnabled: {
    color: '#000',
  },
  aiInsightCard: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: theme.colors.border,
    borderRadius: 8,
    gap: 8,
  },
  aiInsightText: {
    fontSize: 12,
    color: '#00ff88',
    fontWeight: '500',
  },
  aiIndicator: {
    fontSize: 14,
    color: '#00ff88',
    fontWeight: 'normal',
  },
  aiAnalysisButton: {
    padding: 8,
    borderRadius: 6,
    backgroundColor: theme.colors.border,
    marginLeft: 8,
  },
  fullAnalysisButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#00ff88',
    paddingVertical: 8,
    paddingHorizontal: 12,
    borderRadius: 6,
    marginTop: 12,
    gap: 6,
  },
  fullAnalysisButtonText: {
    color: '#000',
    fontSize: 12,
    fontWeight: 'bold',
  },
  // Modal Styles
  modalContainer: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.colors.border,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  modalCloseButton: {
    padding: 4,
  },
  modalContent: {
    flex: 1,
    paddingHorizontal: 20,
  },
  tradeDetailsCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  cardTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 12,
  },
  tradeDetailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  aiComparisonCard: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  aiSignalSection: {
    marginBottom: 16,
  },
  aiSignalTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#00ff88',
    marginBottom: 8,
  },
  aiSignalItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: theme.colors.border,
    borderRadius: 6,
    marginBottom: 6,
    gap: 8,
  },
  aiSignalDate: {
    flex: 1,
    fontSize: 12,
    color: theme.colors.text,
  },
  aiSignalPrice: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    fontWeight: '500',
  },
  noSignalsText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    fontStyle: 'italic',
    textAlign: 'center',
    paddingVertical: 16,
  },
  chartToggleButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: theme.colors.border,
    paddingVertical: 12,
    borderRadius: 8,
    marginTop: 16,
    gap: 8,
  },
  chartToggleText: {
    color: '#00ff88',
    fontSize: 14,
    fontWeight: '600',
  },
  chartContainer: {
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 16,
    marginTop: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  chartLoading: {
    alignItems: 'center',
    paddingVertical: 32,
  },
  chartLoadingText: {
    color: theme.colors.textSecondary,
    marginTop: 12,
    fontSize: 14,
  },
  chartDataContainer: {
    alignItems: 'center',
    paddingVertical: 16,
  },
  chartDataTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 8,
  },
  chartDataSubtitle: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginBottom: 4,
  },
  chartErrorText: {
    fontSize: 14,
    color: '#ff4444',
    textAlign: 'center',
    paddingVertical: 16,
  },
  // Existing styles continue...
  summaryContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginTop: 16,
    gap: 12,
  },
  summaryCard: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    padding: 20,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  summaryIconContainer: {
    marginBottom: 12,
  },
  summaryCardValue: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 4,
  },
  summaryCardLabel: {
    fontSize: 13,
    color: theme.colors.textSecondary,
    marginBottom: 8,
  },
  summaryCardSubtext: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  bestWorstContainer: {
    flexDirection: 'row',
    paddingHorizontal: 20,
    marginTop: 16,
    gap: 12,
  },
  bestWorstCard: {
    flex: 1,
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 12,
    alignItems: 'center',
    borderWidth: 1,
  },
  bestCard: {
    borderColor: '#00ff8833',
  },
  worstCard: {
    borderColor: '#ff444433',
  },
  bestWorstTitle: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginBottom: 8,
  },
  bestWorstSymbol: {
    fontSize: 14,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 4,
  },
  bestWorstValue: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 2,
  },
  bestWorstPercent: {
    fontSize: 12,
    color: theme.colors.textSecondary,
  },
  viewToggle: {
    flexDirection: 'row',
    marginHorizontal: 20,
    marginTop: 20,
    backgroundColor: theme.colors.surface,
    borderRadius: 12,
    padding: 4,
  },
  toggleButton: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderRadius: 8,
  },
  toggleButtonActive: {
    backgroundColor: theme.colors.border,
  },
  toggleText: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    fontWeight: '600',
  },
  toggleTextActive: {
    color: theme.colors.text,
  },
  contentContainer: {
    paddingHorizontal: 20,
    paddingTop: 20,
    paddingBottom: 100,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.text,
    marginBottom: 16,
  },
  tradeItem: {
    backgroundColor: theme.colors.surface,
    marginBottom: 12,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  tradeHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
  },
  tradeBasicInfo: {
    flex: 1,
  },
  tradeSymbol: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  tradeQuantity: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: 2,
  },
  tradePnL: {
    alignItems: 'flex-end',
  },
  tradePnLValue: {
    fontSize: 16,
    fontWeight: 'bold',
  },
  tradePnLPercent: {
    fontSize: 12,
    marginTop: 2,
  },
  tradeDetails: {
    backgroundColor: theme.colors.background,
    padding: 16,
    borderTopWidth: 1,
    borderTopColor: theme.colors.border,
  },
  detailRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  detailLabel: {
    fontSize: 14,
    color: theme.colors.textSecondary,
  },
  detailValue: {
    fontSize: 14,
    color: theme.colors.text,
    fontWeight: '500',
  },
  timestampRow: {
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: '#2a2b2f',
  },
  timestampLabel: {
    fontSize: 12,
    color: theme.colors.textSecondary,
    marginBottom: 2,
  },
  dailyItem: {
    backgroundColor: theme.colors.surface,
    marginBottom: 12,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: theme.colors.border,
  },
  dailyHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  dailyDate: {
    fontSize: 16,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  dailyPnL: {
    fontSize: 18,
    fontWeight: 'bold',
  },
  dailyStats: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  dailyStatText: {
    fontSize: 13,
    color: theme.colors.textSecondary,
  },
  emptyState: {
    alignItems: 'center',
    paddingVertical: 60,
  },
  emptyStateText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: theme.colors.textSecondary,
    marginTop: 16,
  },
  emptyStateSubtext: {
    fontSize: 14,
    color: theme.colors.textSecondary,
    marginTop: 8,
  },
});

export default PnLScreen;