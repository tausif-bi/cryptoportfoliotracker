import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  ActivityIndicator,
  Alert,
} from 'react-native';
import { useTheme } from '../theme/ThemeContext';
import InteractiveTradingChart from '../components/InteractiveTradingChart';
import exchangeService from '../services/exchangeService';
import { authService } from '../services/authService';

const InteractiveChartScreen = ({ route, navigation }) => {
  const { theme } = useTheme();
  const { symbol = 'BTC/USDT' } = route.params || {};
  
  const [loading, setLoading] = useState(true);
  const [chartData, setChartData] = useState(null);
  const [currentSignal, setCurrentSignal] = useState('-');
  const [error, setError] = useState(null);
  const [selectedTimeframe, setSelectedTimeframe] = useState('1h');

  const timeframes = [
    { label: '15m', value: '15m' },
    { label: '1H', value: '1h' },
    { label: '4H', value: '4h' },
    { label: '1D', value: '1d' },
  ];

  const fetchChartData = async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch chart data from the new endpoint
      const response = await fetch(
        `${exchangeService.baseURL}/chart/interactive/${symbol.replace('/', '-')}?timeframe=${selectedTimeframe}&limit=200`
      );

      const data = await response.json();

      if (data.success && data.chartData) {
        setChartData({
          ...data.chartData,
          symbol: symbol,
          currentSignal: data.currentSignal,
        });
        setCurrentSignal(data.currentSignal);
      } else {
        throw new Error(data.error || 'Failed to load chart data');
      }
    } catch (err) {
      console.error('Error fetching chart data:', err);
      setError(err.message);
      Alert.alert('Error', 'Failed to load chart data. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchChartData();
  }, [symbol, selectedTimeframe]);

  const handleTimeframeChange = (timeframe) => {
    setSelectedTimeframe(timeframe);
  };

  const getSignalColor = () => {
    switch (currentSignal) {
      case 'BUY':
        return theme.colors.success;
      case 'SELL':
        return theme.colors.error;
      case 'HOLD LONG':
        return theme.colors.warning;
      default:
        return theme.colors.textSecondary;
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.colors.background }]}>
      <View style={[styles.header, { backgroundColor: theme.colors.card }]}>
        <Text style={[styles.title, { color: theme.colors.text }]}>{symbol}</Text>
        <View style={styles.signalContainer}>
          <Text style={[styles.signalLabel, { color: theme.colors.textSecondary }]}>
            Signal:
          </Text>
          <Text style={[styles.signalValue, { color: getSignalColor() }]}>
            {currentSignal}
          </Text>
        </View>
      </View>

      <View style={[styles.timeframeContainer, { backgroundColor: theme.colors.card }]}>
        {timeframes.map((tf) => (
          <TouchableOpacity
            key={tf.value}
            style={[
              styles.timeframeButton,
              {
                backgroundColor:
                  selectedTimeframe === tf.value ? theme.colors.primary : 'transparent',
              },
            ]}
            onPress={() => handleTimeframeChange(tf.value)}
          >
            <Text
              style={[
                styles.timeframeText,
                {
                  color:
                    selectedTimeframe === tf.value
                      ? theme.colors.background
                      : theme.colors.text,
                },
              ]}
            >
              {tf.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      <ScrollView style={styles.chartContainer}>
        {loading ? (
          <View style={styles.loadingContainer}>
            <ActivityIndicator size="large" color={theme.colors.primary} />
            <Text style={[styles.loadingText, { color: theme.colors.textSecondary }]}>
              Loading interactive chart...
            </Text>
          </View>
        ) : error ? (
          <View style={styles.errorContainer}>
            <Text style={[styles.errorText, { color: theme.colors.error }]}>
              {error}
            </Text>
            <TouchableOpacity
              style={[styles.retryButton, { backgroundColor: theme.colors.primary }]}
              onPress={fetchChartData}
            >
              <Text style={[styles.retryText, { color: theme.colors.background }]}>
                Retry
              </Text>
            </TouchableOpacity>
          </View>
        ) : (
          <>
            <InteractiveTradingChart
              chartData={chartData}
              symbol={symbol}
              timeframe={selectedTimeframe}
              height={500}
            />
            
            <View style={[styles.infoCard, { backgroundColor: theme.colors.card }]}>
              <Text style={[styles.infoTitle, { color: theme.colors.text }]}>
                About This Chart
              </Text>
              <Text style={[styles.infoText, { color: theme.colors.textSecondary }]}>
                This interactive chart uses TradingView Lightweight Charts library.
                You can:
              </Text>
              <Text style={[styles.infoText, { color: theme.colors.textSecondary }]}>
                • Pinch to zoom in/out
              </Text>
              <Text style={[styles.infoText, { color: theme.colors.textSecondary }]}>
                • Drag to pan across time
              </Text>
              <Text style={[styles.infoText, { color: theme.colors.textSecondary }]}>
                • View support/resistance trendlines
              </Text>
              <Text style={[styles.infoText, { color: theme.colors.textSecondary }]}>
                • See buy/sell signals as markers
              </Text>
              <Text style={[styles.infoText, { color: theme.colors.textSecondary }]}>
                • Monitor RSI indicator below
              </Text>
            </View>
          </>
        )}
      </ScrollView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  title: {
    fontSize: 20,
    fontWeight: '600',
  },
  signalContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  signalLabel: {
    fontSize: 14,
  },
  signalValue: {
    fontSize: 16,
    fontWeight: '600',
  },
  timeframeContainer: {
    flexDirection: 'row',
    padding: 8,
    gap: 8,
  },
  timeframeButton: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  timeframeText: {
    fontSize: 14,
    fontWeight: '500',
  },
  chartContainer: {
    flex: 1,
  },
  loadingContainer: {
    height: 400,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 14,
  },
  errorContainer: {
    height: 400,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 20,
  },
  retryButton: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  retryText: {
    fontSize: 16,
    fontWeight: '600',
  },
  infoCard: {
    margin: 16,
    padding: 16,
    borderRadius: 12,
  },
  infoTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 12,
  },
  infoText: {
    fontSize: 14,
    lineHeight: 20,
    marginBottom: 4,
  },
});

export default InteractiveChartScreen;