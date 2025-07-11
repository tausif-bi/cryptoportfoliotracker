import React, { useRef, useEffect } from 'react';
import { StatusBar } from 'react-native';
import { NavigationContainer } from '@react-navigation/native';
import RootNavigator from './src/navigation/RootNavigator';
import { ThemeProvider } from './src/theme/ThemeContext';
import { tokenManager } from './src/utils/tokenManager';
import { authService } from './src/services/authService';

export default function App() {
  const navigationRef = useRef();

  useEffect(() => {
    // Initialize auth service
    authService.initialize();

    // Set navigation reference for token manager
    tokenManager.setNavigation(navigationRef.current);

    // Start token monitoring when app starts
    const checkAuthAndStartMonitoring = async () => {
      const isAuthenticated = await authService.checkAuthStatus();
      if (isAuthenticated) {
        tokenManager.startTokenMonitoring();
      }
    };

    checkAuthAndStartMonitoring();

    // Cleanup on unmount
    return () => {
      tokenManager.stopTokenMonitoring();
    };
  }, []);

  return (
    <ThemeProvider>
      <StatusBar barStyle="light-content" backgroundColor="#0B0E11" />
      <NavigationContainer ref={navigationRef}>
        <RootNavigator />
      </NavigationContainer>
    </ThemeProvider>
  );
}