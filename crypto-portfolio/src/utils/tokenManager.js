import AsyncStorage from '@react-native-async-storage/async-storage';
import { Alert } from 'react-native';
import { authService } from '../services/authService';

class TokenManager {
  constructor() {
    this.tokenCheckInterval = null;
    this.onTokenExpired = null;
    this.navigationRef = null;
  }

  // Set navigation reference
  setNavigation(navigationRef) {
    this.navigationRef = navigationRef;
  }

  // Set callback for token expiration
  setOnTokenExpired(callback) {
    this.onTokenExpired = callback;
  }

  // Parse JWT token to get expiration time
  parseJwt(token) {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map(c => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Error parsing JWT:', error);
      return null;
    }
  }

  // Check if token is expired or about to expire
  isTokenExpired(token, bufferMinutes = 5) {
    if (!token) return true;
    
    const payload = this.parseJwt(token);
    if (!payload || !payload.exp) return true;
    
    const expirationTime = payload.exp * 1000; // Convert to milliseconds
    const currentTime = Date.now();
    const bufferTime = bufferMinutes * 60 * 1000; // Convert minutes to milliseconds
    
    return currentTime >= (expirationTime - bufferTime);
  }

  // Start monitoring token expiration
  startTokenMonitoring() {
    // Clear any existing interval
    this.stopTokenMonitoring();

    // Check token every 30 seconds
    this.tokenCheckInterval = setInterval(async () => {
      try {
        const accessToken = await authService.getAccessToken();
        
        if (!accessToken) {
          this.handleNoToken();
          return;
        }

        // Check if token is expired or about to expire (within 5 minutes)
        if (this.isTokenExpired(accessToken, 5)) {
          await this.handleTokenExpiration();
        }
      } catch (error) {
        console.error('Error checking token:', error);
      }
    }, 30000); // 30 seconds
  }

  // Stop monitoring token expiration
  stopTokenMonitoring() {
    if (this.tokenCheckInterval) {
      clearInterval(this.tokenCheckInterval);
      this.tokenCheckInterval = null;
    }
  }

  // Handle when no token is found
  handleNoToken() {
    this.stopTokenMonitoring();
    
    // Only show alert if user is not on login screen
    if (this.navigationRef?.getCurrentRoute?.()?.name !== 'Login') {
      Alert.alert(
        'Session Expired',
        'Your session has expired. Please log in again.',
        [
          {
            text: 'OK',
            onPress: () => {
              if (this.navigationRef) {
                this.navigationRef.navigate('Login');
              }
            }
          }
        ],
        { cancelable: false }
      );
    }
  }

  // Handle token expiration
  async handleTokenExpiration() {
    try {
      // Try to refresh the token first
      const newAccessToken = await authService.refreshAccessToken();
      
      if (newAccessToken) {
        console.log('Token refreshed successfully');
        return;
      }
    } catch (error) {
      console.error('Failed to refresh token:', error);
    }

    // If refresh failed, show expiration alert
    this.stopTokenMonitoring();
    
    Alert.alert(
      'Session Expiring',
      'Your session is about to expire. Would you like to continue?',
      [
        {
          text: 'Logout',
          onPress: async () => {
            await authService.logout();
            if (this.navigationRef) {
              this.navigationRef.navigate('Login');
            }
          },
          style: 'cancel'
        },
        {
          text: 'Continue',
          onPress: async () => {
            // Try to refresh token again
            try {
              await authService.refreshAccessToken();
              this.startTokenMonitoring(); // Restart monitoring
            } catch (error) {
              // If still fails, redirect to login
              Alert.alert(
                'Session Expired',
                'Please log in again to continue.',
                [
                  {
                    text: 'OK',
                    onPress: () => {
                      if (this.navigationRef) {
                        this.navigationRef.navigate('Login');
                      }
                    }
                  }
                ]
              );
            }
          }
        }
      ],
      { cancelable: false }
    );

    // Call custom callback if provided
    if (this.onTokenExpired) {
      this.onTokenExpired();
    }
  }

  // Get remaining time until token expiration
  getTokenRemainingTime(token) {
    if (!token) return 0;
    
    const payload = this.parseJwt(token);
    if (!payload || !payload.exp) return 0;
    
    const expirationTime = payload.exp * 1000;
    const currentTime = Date.now();
    const remainingTime = expirationTime - currentTime;
    
    return Math.max(0, remainingTime);
  }

  // Format remaining time for display
  formatRemainingTime(milliseconds) {
    if (milliseconds <= 0) return 'Expired';
    
    const seconds = Math.floor(milliseconds / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);
    
    if (days > 0) return `${days} day${days > 1 ? 's' : ''}`;
    if (hours > 0) return `${hours} hour${hours > 1 ? 's' : ''}`;
    if (minutes > 0) return `${minutes} minute${minutes > 1 ? 's' : ''}`;
    return `${seconds} second${seconds > 1 ? 's' : ''}`;
  }
}

export const tokenManager = new TokenManager();