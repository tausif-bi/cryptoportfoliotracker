import React, { useState, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeContext';
import { authService } from '../services/authService';
import { tokenManager } from '../utils/tokenManager';

const SessionTimer = ({ style }) => {
  const { theme } = useTheme();
  const [remainingTime, setRemainingTime] = useState('');
  const [isExpiringSoon, setIsExpiringSoon] = useState(false);

  useEffect(() => {
    // Update remaining time every second
    const updateTimer = async () => {
      try {
        const accessToken = await authService.getAccessToken();
        if (accessToken) {
          const remaining = tokenManager.getTokenRemainingTime(accessToken);
          const formatted = tokenManager.formatRemainingTime(remaining);
          setRemainingTime(formatted);
          
          // Check if expiring soon (less than 5 minutes)
          setIsExpiringSoon(remaining < 5 * 60 * 1000);
        } else {
          setRemainingTime('No session');
        }
      } catch (error) {
        console.error('Error updating session timer:', error);
      }
    };

    // Initial update
    updateTimer();

    // Update every second
    const interval = setInterval(updateTimer, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleRefreshToken = async () => {
    try {
      await authService.refreshAccessToken();
      // Timer will update automatically on next interval
    } catch (error) {
      console.error('Failed to refresh token:', error);
    }
  };

  return (
    <TouchableOpacity 
      style={[styles.container, style]} 
      onPress={handleRefreshToken}
      activeOpacity={0.7}
    >
      <View style={[
        styles.timerBox, 
        { 
          backgroundColor: theme.colors.card,
          borderColor: isExpiringSoon ? theme.colors.error : theme.colors.border
        }
      ]}>
        <Ionicons 
          name="time-outline" 
          size={16} 
          color={isExpiringSoon ? theme.colors.error : theme.colors.textSecondary} 
        />
        <Text style={[
          styles.timerText,
          { 
            color: isExpiringSoon ? theme.colors.error : theme.colors.textSecondary
          }
        ]}>
          {remainingTime}
        </Text>
        {isExpiringSoon && (
          <Ionicons 
            name="refresh" 
            size={16} 
            color={theme.colors.error} 
          />
        )}
      </View>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    alignSelf: 'flex-end',
  },
  timerBox: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    gap: 6,
  },
  timerText: {
    fontSize: 12,
    fontWeight: '500',
  },
});

export default SessionTimer;