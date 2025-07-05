import * as FileSystem from 'expo-file-system';
import * as MediaLibrary from 'expo-media-library';
import * as Sharing from 'expo-sharing';
import { Alert, Platform, Linking } from 'react-native';

export const saveChartToGallery = async (base64Data, fileName = 'chart') => {
  try {
    // Check if we have the base64 data
    if (!base64Data) {
      throw new Error('No chart data available');
    }

    // Check if running on web
    if (Platform.OS === 'web') {
      // Web download implementation
      const link = document.createElement('a');
      link.href = `data:image/png;base64,${base64Data}`;
      link.download = `${fileName}_${new Date().getTime()}.png`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      Alert.alert(
        'Download Started',
        'Check your Downloads folder for the chart image.',
        [{ text: 'OK' }]
      );
      return true;
    }

    // Mobile implementation (existing code)
    const permissionResult = await MediaLibrary.requestPermissionsAsync();
    
    if (permissionResult.status !== 'granted') {
      Alert.alert(
        'Permission Required',
        'Please grant permission to save images to your gallery.\n\nGo to Settings > Apps > Crypto Portfolio > Permissions',
        [
          { text: 'Cancel', style: 'cancel' },
          { text: 'Open Settings', onPress: () => {
            if (Platform.OS === 'ios') {
              Linking.openURL('app-settings:');
            } else {
              Linking.openSettings();
            }
          }}
        ]
      );
      return false;
    }

    // Create a unique filename
    const timestamp = new Date().getTime();
    const fileUri = `${FileSystem.documentDirectory}${fileName}_${timestamp}.png`;

    // Write the base64 data to a file
    await FileSystem.writeAsStringAsync(fileUri, base64Data, {
      encoding: FileSystem.EncodingType.Base64,
    });

    // Save to media library
    const asset = await MediaLibrary.createAssetAsync(fileUri);
    
    // Create album if it doesn't exist
    const album = await MediaLibrary.getAlbumAsync('Crypto Portfolio');
    if (album == null) {
      await MediaLibrary.createAlbumAsync('Crypto Portfolio', asset, false);
    } else {
      await MediaLibrary.addAssetsToAlbumAsync([asset], album, false);
    }

    // Clean up the temporary file
    await FileSystem.deleteAsync(fileUri, { idempotent: true });

    Alert.alert(
      'Success!',
      'Chart saved to your gallery in "Crypto Portfolio" album',
      [{ text: 'OK' }]
    );

    return true;
  } catch (error) {
    console.error('Save error:', error);
    Alert.alert(
      'Save Failed',
      'Unable to save the chart. Please try again.',
      [{ text: 'OK' }]
    );
    return false;
  }
};

export const shareChart = async (base64Data, fileName = 'chart', message = '') => {
  try {
    // Check if we have the base64 data
    if (!base64Data) {
      throw new Error('No chart data available');
    }

    // Create a unique filename
    const timestamp = new Date().getTime();
    const fileUri = `${FileSystem.cacheDirectory}${fileName}_${timestamp}.png`;

    // Write the base64 data to a file
    await FileSystem.writeAsStringAsync(fileUri, base64Data, {
      encoding: FileSystem.EncodingType.Base64,
    });

    // Check if sharing is available
    if (!(await Sharing.isAvailableAsync())) {
      Alert.alert(
        'Sharing Not Available',
        'Sharing is not available on this device',
        [{ text: 'OK' }]
      );
      return false;
    }

    // Share the file
    await Sharing.shareAsync(fileUri, {
      mimeType: 'image/png',
      dialogTitle: 'Share Chart',
      UTI: 'public.image',
    });

    // Clean up the temporary file after a delay
    setTimeout(async () => {
      try {
        await FileSystem.deleteAsync(fileUri, { idempotent: true });
      } catch (error) {
        // Ignore cleanup errors
      }
    }, 10000);

    return true;
  } catch (error) {
    console.error('Share error:', error);
    Alert.alert(
      'Share Failed',
      'Unable to share the chart. Please try again.',
      [{ text: 'OK' }]
    );
    return false;
  }
};