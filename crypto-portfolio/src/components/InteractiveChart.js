import React, { useEffect, useState } from 'react';
import { View, StyleSheet, Dimensions, ScrollView, Text } from 'react-native';
import Svg, { Line, Rect, Path, Circle, Text as SvgText, G } from 'react-native-svg';
import { useTheme } from '../theme/ThemeContext';

const { width: screenWidth } = Dimensions.get('window');

const InteractiveChart = ({ chartData, height = 400 }) => {
  const { theme } = useTheme();
  const [dimensions, setDimensions] = useState({ width: screenWidth - 40, height });
  
  const padding = { top: 20, right: 50, bottom: 40, left: 10 };
  const chartWidth = dimensions.width - padding.left - padding.right;
  const chartHeight = dimensions.height - padding.top - padding.bottom;
  
  if (!chartData || !chartData.candlestick || chartData.candlestick.length === 0) {
    return (
      <View style={[styles.container, { height }]}>
        <Text style={[styles.noDataText, { color: theme.colors.textSecondary }]}>
          No chart data available
        </Text>
      </View>
    );
  }

  // Calculate scales
  const data = chartData.candlestick;
  const priceRange = {
    min: Math.min(...data.map(d => d.low)),
    max: Math.max(...data.map(d => d.high))
  };
  const priceScale = (price) => {
    const range = priceRange.max - priceRange.min;
    const padding = range * 0.1;
    return chartHeight - ((price - priceRange.min + padding) / (range + padding * 2)) * chartHeight;
  };

  const timeScale = (index) => {
    return (index / (data.length - 1)) * chartWidth;
  };

  // Render candlesticks
  const renderCandlesticks = () => {
    const candleWidth = Math.max(1, chartWidth / data.length * 0.8);
    
    return data.map((candle, index) => {
      const x = timeScale(index);
      const isGreen = candle.close > candle.open;
      const color = isGreen ? '#26a69a' : '#ef5350';
      
      const bodyTop = priceScale(Math.max(candle.open, candle.close));
      const bodyBottom = priceScale(Math.min(candle.open, candle.close));
      const bodyHeight = Math.max(1, bodyBottom - bodyTop);
      
      return (
        <G key={index}>
          {/* Wick */}
          <Line
            x1={x + candleWidth / 2}
            y1={priceScale(candle.high)}
            x2={x + candleWidth / 2}
            y2={priceScale(candle.low)}
            stroke={color}
            strokeWidth={1}
          />
          {/* Body */}
          <Rect
            x={x}
            y={bodyTop}
            width={candleWidth}
            height={bodyHeight}
            fill={color}
            stroke={color}
          />
        </G>
      );
    });
  };

  // Render volume bars
  const renderVolumeBars = () => {
    if (!chartData.volume) return null;
    
    const volumeHeight = chartHeight * 0.2;
    const volumeTop = chartHeight - volumeHeight;
    const maxVolume = Math.max(...chartData.volume.map(v => v.value));
    
    return chartData.volume.map((vol, index) => {
      const x = timeScale(index);
      const barHeight = (vol.value / maxVolume) * volumeHeight;
      const candleWidth = Math.max(1, chartWidth / data.length * 0.8);
      
      return (
        <Rect
          key={index}
          x={x}
          y={volumeTop + volumeHeight - barHeight}
          width={candleWidth}
          height={barHeight}
          fill={vol.color || '#26a69a40'}
        />
      );
    });
  };

  // Render indicators (SMA lines)
  const renderIndicators = () => {
    if (!chartData.indicators) return null;
    
    return Object.entries(chartData.indicators).map(([key, indicator]) => {
      const pathData = indicator.data
        .map((point, index) => {
          const x = timeScale(index);
          const y = priceScale(point.value);
          return `${index === 0 ? 'M' : 'L'} ${x} ${y}`;
        })
        .join(' ');
      
      return (
        <Path
          key={key}
          d={pathData}
          stroke={indicator.color}
          strokeWidth={2}
          fill="none"
        />
      );
    });
  };

  // Render markers (buy/sell signals)
  const renderMarkers = () => {
    if (!chartData.markers) return null;
    
    return chartData.markers.map((marker, index) => {
      // Find the corresponding candle index
      const candleIndex = data.findIndex(c => c.time === marker.time);
      if (candleIndex === -1) return null;
      
      const x = timeScale(candleIndex) + (chartWidth / data.length * 0.4);
      const candle = data[candleIndex];
      const y = marker.position === 'aboveBar' 
        ? priceScale(candle.high) - 20 
        : priceScale(candle.low) + 20;
      
      const isArrowUp = marker.shape === 'arrowUp';
      const path = isArrowUp
        ? `M ${x} ${y} L ${x-8} ${y+15} L ${x+8} ${y+15} Z`
        : `M ${x} ${y} L ${x-8} ${y-15} L ${x+8} ${y-15} Z`;
      
      return (
        <G key={index}>
          <Path
            d={path}
            fill={marker.color}
          />
          {marker.text && (
            <SvgText
              x={x}
              y={y + (isArrowUp ? -10 : 25)}
              fill={marker.color}
              fontSize="10"
              textAnchor="middle"
            >
              {marker.text}
            </SvgText>
          )}
        </G>
      );
    });
  };

  // Render price axis
  const renderPriceAxis = () => {
    const steps = 5;
    const priceStep = (priceRange.max - priceRange.min) / steps;
    
    return Array.from({ length: steps + 1 }, (_, i) => {
      const price = priceRange.min + (priceStep * i);
      const y = priceScale(price);
      
      return (
        <G key={i}>
          <Line
            x1={chartWidth}
            y1={y}
            x2={chartWidth + 5}
            y2={y}
            stroke={theme.colors.textSecondary}
            strokeWidth={1}
          />
          <SvgText
            x={chartWidth + 10}
            y={y + 4}
            fill={theme.colors.textSecondary}
            fontSize="10"
          >
            ${price.toFixed(0)}
          </SvgText>
        </G>
      );
    });
  };

  return (
    <ScrollView 
      horizontal 
      showsHorizontalScrollIndicator={false}
      style={[styles.container, { height }]}
    >
      <Svg width={dimensions.width} height={dimensions.height}>
        <G transform={`translate(${padding.left}, ${padding.top})`}>
          {/* Grid lines */}
          {Array.from({ length: 5 }, (_, i) => (
            <Line
              key={i}
              x1={0}
              y1={(chartHeight / 5) * (i + 1)}
              x2={chartWidth}
              y2={(chartHeight / 5) * (i + 1)}
              stroke={theme.colors.border}
              strokeWidth={0.5}
              strokeDasharray="5,5"
            />
          ))}
          
          {/* Volume bars */}
          {renderVolumeBars()}
          
          {/* Indicators */}
          {renderIndicators()}
          
          {/* Candlesticks */}
          {renderCandlesticks()}
          
          {/* Markers */}
          {renderMarkers()}
          
          {/* Price axis */}
          {renderPriceAxis()}
        </G>
      </Svg>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: 'transparent',
  },
  noDataText: {
    textAlign: 'center',
    marginTop: 50,
    fontSize: 14,
  },
});

export default InteractiveChart;