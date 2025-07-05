import { Alert, Share } from 'react-native';
import * as Clipboard from 'expo-clipboard';

export const copyChartLink = async (chartBase64) => {
  // For web/demo purposes, create a data URL
  const dataUrl = `data:image/png;base64,${chartBase64}`;
  
  await Clipboard.setStringAsync(dataUrl);
  
  Alert.alert(
    'Chart Copied!',
    'The chart has been copied to your clipboard. You can paste it in any app that supports images.',
    [{ text: 'OK' }]
  );
};

export const simpleShare = async (chartBase64, strategyName, signal, price) => {
  const message = `📊 ${strategyName} Analysis
📈 Signal: ${signal}
💰 Price: $${price}
  
Check out my trading strategy analysis from Crypto Portfolio Tracker!`;
  
  try {
    await Share.share({
      message: message,
      title: 'Strategy Analysis',
    });
  } catch (error) {
    Alert.alert('Error', 'Unable to share');
  }
};