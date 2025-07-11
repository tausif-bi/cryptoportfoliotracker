import React, { useRef, useState, useEffect } from 'react';
import { View, Text, StyleSheet, ActivityIndicator, Platform } from 'react-native';
import { useTheme } from '../theme/ThemeContext';

// Conditional import for WebView
let WebView;
if (Platform.OS !== 'web') {
  WebView = require('react-native-webview').WebView;
}

const InteractiveTradingChart = ({ chartData, symbol = 'BTC/USDT', timeframe = '1h', height = 600 }) => {
  const { theme } = useTheme();
  const webViewRef = useRef(null);
  const [loading, setLoading] = useState(true);

  // HTML template with inline chart code
  const getHtmlContent = () => {
    return `
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>Trading Chart</title>
    <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: ${theme.colors.background};
            color: ${theme.colors.text};
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            overflow: hidden;
        }
        #container {
            display: flex;
            flex-direction: column;
            height: 100vh;
        }
        #toolbar {
            padding: 10px;
            background-color: ${theme.colors.card};
            border-bottom: 1px solid ${theme.colors.border};
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        #mainChart {
            flex: 2;
            position: relative;
        }
        #rsiChart {
            flex: 1;
            position: relative;
            border-top: 1px solid ${theme.colors.border};
        }
        .chart-label {
            position: absolute;
            top: 10px;
            left: 10px;
            background-color: rgba(26, 26, 26, 0.8);
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 12px;
            z-index: 10;
        }
        .info-box {
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }
        .info-item {
            display: flex;
            flex-direction: column;
        }
        .info-label {
            font-size: 11px;
            color: ${theme.colors.textSecondary};
        }
        .info-value {
            font-size: 14px;
            font-weight: 600;
        }
        .signal-buy { color: ${theme.colors.success}; }
        .signal-sell { color: ${theme.colors.error}; }
        .signal-hold { color: ${theme.colors.warning}; }
    </style>
</head>
<body>
    <div id="container">
        <div id="toolbar">
            <div class="info-box">
                <div class="info-item">
                    <span class="info-label">Symbol</span>
                    <span class="info-value" id="symbol">${symbol}</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Price</span>
                    <span class="info-value" id="price">-</span>
                </div>
                <div class="info-item">
                    <span class="info-label">RSI</span>
                    <span class="info-value" id="rsi">-</span>
                </div>
                <div class="info-item">
                    <span class="info-label">Signal</span>
                    <span class="info-value" id="signal">-</span>
                </div>
            </div>
        </div>
        <div id="mainChart">
            <div class="chart-label">Trendline Breakout</div>
            <div id="mainChartContainer" style="height: 100%;"></div>
        </div>
        <div id="rsiChart">
            <div class="chart-label">RSI (14)</div>
            <div id="rsiChartContainer" style="height: 100%;"></div>
        </div>
    </div>

    <script>
        // Wait for LightweightCharts to load
        function initializeChart() {
            const chartOptions = {
                layout: {
                    background: { color: '${theme.colors.background}' },
                    textColor: '${theme.colors.text}',
                },
                grid: {
                    vertLines: { color: '${theme.colors.border}33' },
                    horzLines: { color: '${theme.colors.border}33' },
                },
                crosshair: {
                    mode: LightweightCharts.CrosshairMode.Normal,
                },
                rightPriceScale: {
                    borderColor: '${theme.colors.border}',
                },
                timeScale: {
                    borderColor: '${theme.colors.border}',
                    timeVisible: true,
                    secondsVisible: false,
                },
            };

            // Initialize charts
            const mainChart = LightweightCharts.createChart(
                document.getElementById('mainChartContainer'), 
                { ...chartOptions, height: 300 }
            );
            
            const rsiChart = LightweightCharts.createChart(
                document.getElementById('rsiChartContainer'), 
                { ...chartOptions, height: 150 }
            );

            // Create series
            const candlestickSeries = mainChart.addCandlestickSeries({
                upColor: '${theme.colors.success}',
                downColor: '${theme.colors.error}',
                borderVisible: false,
                wickUpColor: '${theme.colors.success}',
                wickDownColor: '${theme.colors.error}',
            });

            const supportLine = mainChart.addLineSeries({
                color: '${theme.colors.success}',
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Solid,
                title: 'Support',
            });

            const resistanceLine = mainChart.addLineSeries({
                color: '${theme.colors.error}',
                lineWidth: 2,
                lineStyle: LightweightCharts.LineStyle.Solid,
                title: 'Resistance',
            });

            const rsiLine = rsiChart.addLineSeries({
                color: '${theme.colors.primary}',
                lineWidth: 2,
                title: 'RSI',
            });

            // Add RSI levels
            const rsiUpperBound = rsiChart.addLineSeries({
                color: '${theme.colors.error}',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceLineVisible: false,
                lastValueVisible: false,
            });

            const rsiLowerBound = rsiChart.addLineSeries({
                color: '${theme.colors.success}',
                lineWidth: 1,
                lineStyle: LightweightCharts.LineStyle.Dashed,
                priceLineVisible: false,
                lastValueVisible: false,
            });

            // Function to update chart with data
            window.updateChart = function(data) {
                try {
                    // Update candlestick data
                    if (data.candlestickData && data.candlestickData.length > 0) {
                        candlestickSeries.setData(data.candlestickData);
                    }
                    
                    // Update support and resistance lines
                    if (data.supportLine && data.supportLine.length > 0) {
                        supportLine.setData(data.supportLine);
                    }
                    if (data.resistanceLine && data.resistanceLine.length > 0) {
                        resistanceLine.setData(data.resistanceLine);
                    }
                    
                    // Update RSI
                    if (data.rsiData && data.rsiData.length > 0) {
                        rsiLine.setData(data.rsiData);
                        
                        // Set RSI bounds
                        const firstTime = data.rsiData[0].time;
                        const lastTime = data.rsiData[data.rsiData.length - 1].time;
                        rsiUpperBound.setData([
                            { time: firstTime, value: 70 },
                            { time: lastTime, value: 70 }
                        ]);
                        rsiLowerBound.setData([
                            { time: firstTime, value: 30 },
                            { time: lastTime, value: 30 }
                        ]);
                    }
                    
                    // Add buy/sell markers
                    const markers = [];
                    if (data.buySignals) {
                        data.buySignals.forEach(signal => {
                            markers.push({
                                time: signal.time,
                                position: signal.position,
                                color: signal.color,
                                shape: signal.shape,
                                text: signal.text
                            });
                        });
                    }
                    if (data.sellSignals) {
                        data.sellSignals.forEach(signal => {
                            markers.push({
                                time: signal.time,
                                position: signal.position,
                                color: signal.color,
                                shape: signal.shape,
                                text: signal.text
                            });
                        });
                    }
                    if (markers.length > 0) {
                        candlestickSeries.setMarkers(markers);
                    }
                    
                    // Add horizontal levels
                    if (data.horizontalLevels) {
                        data.horizontalLevels.forEach(level => {
                            const priceLine = {
                                price: level.price,
                                color: level.color,
                                lineWidth: level.lineWidth,
                                lineStyle: level.lineStyle,
                                axisLabelVisible: true,
                                title: level.title,
                            };
                            candlestickSeries.createPriceLine(priceLine);
                        });
                    }
                    
                    // Update info display
                    document.getElementById('price').textContent = data.currentPrice ? '$' + data.currentPrice.toFixed(2) : '-';
                    document.getElementById('rsi').textContent = data.currentRSI ? data.currentRSI.toFixed(2) : '-';
                    
                    const signalElement = document.getElementById('signal');
                    signalElement.textContent = data.currentSignal || '-';
                    signalElement.className = 'info-value';
                    if (data.currentSignal === 'BUY') {
                        signalElement.classList.add('signal-buy');
                    } else if (data.currentSignal === 'SELL') {
                        signalElement.classList.add('signal-sell');
                    } else {
                        signalElement.classList.add('signal-hold');
                    }
                    
                    // Sync time scales
                    mainChart.timeScale().subscribeVisibleTimeRangeChange(() => {
                        const range = mainChart.timeScale().getVisibleRange();
                        if (range) {
                            rsiChart.timeScale().setVisibleRange(range);
                        }
                    });
                    
                    rsiChart.timeScale().subscribeVisibleTimeRangeChange(() => {
                        const range = rsiChart.timeScale().getVisibleRange();
                        if (range) {
                            mainChart.timeScale().setVisibleRange(range);
                        }
                    });
                    
                    // Fit content
                    mainChart.timeScale().fitContent();
                    rsiChart.timeScale().fitContent();
                    
                    // Notify React Native that chart is ready
                    if (window.ReactNativeWebView) {
                        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'chartReady' }));
                    }
                } catch (error) {
                    console.error('Error updating chart:', error);
                    if (window.ReactNativeWebView) {
                        window.ReactNativeWebView.postMessage(JSON.stringify({ 
                            type: 'error', 
                            message: error.toString() 
                        }));
                    }
                }
            };

            // Handle window resize
            window.addEventListener('resize', () => {
                mainChart.applyOptions({ 
                    width: document.getElementById('mainChartContainer').clientWidth,
                });
                rsiChart.applyOptions({ 
                    width: document.getElementById('rsiChartContainer').clientWidth,
                });
            });

            // Notify that chart is initialized
            if (window.ReactNativeWebView) {
                window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'initialized' }));
            }
            
            // For web platform - listen for messages from parent window
            window.addEventListener('message', function(event) {
                if (event.data && event.data.type === 'updateChart' && event.data.data) {
                    window.updateChart(event.data.data);
                }
            });
        }

        // Initialize when page loads
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initializeChart);
        } else {
            initializeChart();
        }
    </script>
</body>
</html>
    `;
  };

  const handleMessage = (event) => {
    const data = JSON.parse(event.nativeEvent.data);
    
    if (data.type === 'initialized') {
      // Send chart data to WebView
      if (chartData && webViewRef.current) {
        webViewRef.current.injectJavaScript(`
          window.updateChart(${JSON.stringify(chartData)});
          true;
        `);
      }
    } else if (data.type === 'chartReady') {
      setLoading(false);
    } else if (data.type === 'error') {
      console.error('Chart error:', data.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    // Update chart when data changes
    if (chartData && webViewRef.current && !loading) {
      webViewRef.current.injectJavaScript(`
        window.updateChart(${JSON.stringify(chartData)});
        true;
      `);
    }
  }, [chartData, loading]);

  // For web platform, use iframe pointing to Flask endpoint
  if (Platform.OS === 'web') {
    const baseURL = 'http://localhost:5000'; // You may want to get this from config
    const chartUrl = `${baseURL}/api/chart/view/${symbol.replace('/', '-')}?timeframe=${timeframe}`;
    
    return (
      <View style={[styles.container, { height }]}>
        <iframe
          id="tradingChartIframe"
          src={chartUrl}
          style={{
            width: '100%',
            height: '100%',
            border: 'none',
            backgroundColor: theme.colors.background
          }}
          allow="fullscreen"
          allowFullScreen
          title="Trading Chart"
          onLoad={() => setLoading(false)}
        />
      </View>
    );
  }

  return (
    <View style={[styles.container, { height }]}>
      {loading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      )}
      {WebView && (
        <WebView
          ref={webViewRef}
          source={{ html: getHtmlContent() }}
          style={styles.webView}
          originWhitelist={['*']}
          onMessage={handleMessage}
          javaScriptEnabled={true}
          domStorageEnabled={true}
          startInLoadingState={false}
          scalesPageToFit={Platform.OS === 'android'}
          scrollEnabled={false}
          bounces={false}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    backgroundColor: '#0D0E11',
  },
  webView: {
    flex: 1,
    backgroundColor: 'transparent',
  },
  loadingContainer: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#0D0E11',
    zIndex: 1,
  },
  webNotSupportedContainer: {
    padding: 20,
    alignItems: 'center',
  },
  webNotSupportedText: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 10,
    textAlign: 'center',
  },
  webNotSupportedSubtext: {
    fontSize: 14,
    marginBottom: 20,
    textAlign: 'center',
  },
  chartDataInfo: {
    marginTop: 20,
    padding: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 8,
    width: '100%',
  },
  infoText: {
    fontSize: 16,
    marginVertical: 5,
    textAlign: 'center',
  },
});

export default InteractiveTradingChart;