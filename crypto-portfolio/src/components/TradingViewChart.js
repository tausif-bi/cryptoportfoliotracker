import React, { useEffect, useRef, useState } from 'react';
import { View, StyleSheet, Dimensions, ActivityIndicator } from 'react-native';
import { WebView } from 'react-native-webview';
import { useTheme } from '../theme/ThemeContext';

const { width: screenWidth, height: screenHeight } = Dimensions.get('window');

const TradingViewChart = ({ chartData, height = 400 }) => {
  const { theme } = useTheme();
  const [isLoading, setIsLoading] = useState(true);

  const chartHTML = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
      <script src="https://unpkg.com/lightweight-charts/dist/lightweight-charts.standalone.production.js"></script>
      <style>
        body {
          margin: 0;
          padding: 0;
          background-color: ${theme.colors.background};
          overflow: hidden;
        }
        #container {
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
        }
        .loading {
          position: absolute;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          color: ${theme.colors.text};
          font-family: Arial, sans-serif;
        }
      </style>
    </head>
    <body>
      <div id="container">
        <div class="loading">Loading chart...</div>
      </div>
      <script>
        const chartData = ${JSON.stringify(chartData)};
        const isDarkTheme = ${theme.dark ? 'true' : 'false'};
        
        // Chart configuration
        const chartOptions = {
          layout: {
            background: {
              type: 'solid',
              color: isDarkTheme ? '#1a1a1a' : '#ffffff'
            },
            textColor: isDarkTheme ? '#d1d4dc' : '#191919',
          },
          grid: {
            vertLines: {
              color: isDarkTheme ? '#2a2a2a' : '#e6e6e6',
            },
            horzLines: {
              color: isDarkTheme ? '#2a2a2a' : '#e6e6e6',
            },
          },
          crosshair: {
            mode: LightweightCharts.CrosshairMode.Normal,
          },
          rightPriceScale: {
            borderColor: isDarkTheme ? '#2a2a2a' : '#e6e6e6',
          },
          timeScale: {
            borderColor: isDarkTheme ? '#2a2a2a' : '#e6e6e6',
            timeVisible: true,
            secondsVisible: false,
          },
        };

        const container = document.getElementById('container');
        const chart = LightweightCharts.createChart(container, {
          ...chartOptions,
          width: container.clientWidth,
          height: container.clientHeight,
        });

        // Add candlestick series
        const candlestickSeries = chart.addCandlestickSeries({
          upColor: '#26a69a',
          downColor: '#ef5350',
          borderVisible: false,
          wickUpColor: '#26a69a',
          wickDownColor: '#ef5350',
        });
        
        if (chartData.candlestick) {
          candlestickSeries.setData(chartData.candlestick);
        }

        // Add volume histogram
        const volumeSeries = chart.addHistogramSeries({
          color: '#26a69a',
          priceFormat: {
            type: 'volume',
          },
          priceScaleId: '',
          scaleMargins: {
            top: 0.8,
            bottom: 0,
          },
        });
        
        if (chartData.volume) {
          volumeSeries.setData(chartData.volume);
        }

        // Add indicators
        if (chartData.indicators) {
          Object.entries(chartData.indicators).forEach(([key, indicator]) => {
            const lineSeries = chart.addLineSeries({
              color: indicator.color,
              lineWidth: 2,
              title: indicator.name,
            });
            lineSeries.setData(indicator.data);
          });
        }

        // Add markers
        if (chartData.markers) {
          candlestickSeries.setMarkers(chartData.markers);
        }

        // Add price levels
        if (chartData.priceLevels) {
          chartData.priceLevels.forEach(level => {
            candlestickSeries.createPriceLine(level);
          });
        }

        // Handle responsive sizing
        function handleResize() {
          chart.applyOptions({
            width: container.clientWidth,
            height: container.clientHeight
          });
        }

        window.addEventListener('resize', handleResize);
        
        // Fit content
        chart.timeScale().fitContent();
        
        // Hide loading message
        container.querySelector('.loading').style.display = 'none';
        
        // Send ready message to React Native
        window.ReactNativeWebView.postMessage(JSON.stringify({ type: 'chartReady' }));
      </script>
    </body>
    </html>
  `;

  const handleMessage = (event) => {
    const message = JSON.parse(event.nativeEvent.data);
    if (message.type === 'chartReady') {
      setIsLoading(false);
    }
  };

  return (
    <View style={[styles.container, { height }]}>
      {isLoading && (
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color={theme.colors.primary} />
        </View>
      )}
      <WebView
        source={{ html: chartHTML }}
        style={styles.webview}
        scrollEnabled={false}
        onMessage={handleMessage}
        javaScriptEnabled={true}
        domStorageEnabled={true}
        startInLoadingState={true}
        originWhitelist={['*']}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    backgroundColor: 'transparent',
  },
  webview: {
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
    zIndex: 1,
  },
});

export default TradingViewChart;