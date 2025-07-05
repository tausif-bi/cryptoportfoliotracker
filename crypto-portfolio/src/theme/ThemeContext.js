// src/theme/ThemeContext.js

import React, { createContext, useContext, useState, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

// Create the theme context
const ThemeContext = createContext();

// Theme configuration
const lightTheme = {
  colors: {
    primary: '#00D4FF',
    secondary: '#00F89E',
    background: '#FFFFFF',
    surface: '#F5F5F5',
    card: '#FFFFFF',
    text: '#000000',
    textSecondary: '#666666',
    border: '#E0E0E0',
    error: '#FF3B5C',
    warning: '#FFB800',
    success: '#00F89E',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
  },
};

const darkTheme = {
  colors: {
    primary: '#00D4FF',
    secondary: '#00F89E',
    background: '#0B0E11',
    surface: '#151A21',
    card: '#1A1F29',
    text: '#FFFFFF',
    textSecondary: '#8B95A7',
    border: '#2A2F39',
    error: '#FF3B5C',
    warning: '#FFB800',
    success: '#00F89E',
  },
  spacing: {
    xs: 4,
    sm: 8,
    md: 16,
    lg: 24,
    xl: 32,
  },
  borderRadius: {
    sm: 8,
    md: 12,
    lg: 16,
    xl: 24,
  },
};

// Theme provider component
export const ThemeProvider = ({ children }) => {
  const [isDarkMode, setIsDarkMode] = useState(true); // Default to dark mode for this release
  const [isLoading, setIsLoading] = useState(true);

  // Load theme preference on app start
  useEffect(() => {
    loadThemePreference();
  }, []);

  const loadThemePreference = async () => {
    try {
      const savedTheme = await AsyncStorage.getItem('dark_mode');
      if (savedTheme !== null) {
        setIsDarkMode(JSON.parse(savedTheme));
      }
    } catch (error) {
      console.error('Error loading theme preference:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const setDarkMode = async (value) => {
    try {
      setIsDarkMode(value);
      await AsyncStorage.setItem('dark_mode', JSON.stringify(value));
    } catch (error) {
      console.error('Error saving theme preference:', error);
    }
  };

  const toggleDarkMode = () => {
    setDarkMode(!isDarkMode);
  };

  const theme = isDarkMode ? darkTheme : lightTheme;

  const value = {
    theme,
    isDarkMode,
    setDarkMode,
    toggleDarkMode,
    isLoading,
  };

  if (isLoading) {
    return null; // or a loading spinner
  }

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

// Custom hook to use theme
export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

// Export the context for direct usage if needed
export { ThemeContext };