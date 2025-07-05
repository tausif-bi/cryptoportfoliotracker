import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createStackNavigator } from '@react-navigation/stack';
import { Ionicons } from '@expo/vector-icons';
import { useTheme } from '../theme/ThemeContext';

// Import existing screens
import HomeScreen from '../screens/HomeScreen';
import PortfolioScreen from '../screens/PortfolioScreen';
import TradesScreen from '../screens/TradesScreen';
import PnLScreen from '../screens/PnLScreen';
import SettingsScreen from '../screens/SettingsScreen';

// Import new strategy screens
import StrategiesScreen from '../screens/StrategiesScreen';
import StrategyComparisonScreen from '../screens/StrategyComparisonScreen';
import StrategyDetailScreen from '../screens/StrategyDetailScreen';

const Tab = createBottomTabNavigator();
const Stack = createStackNavigator();

// Create a stack navigator for strategies to handle navigation between strategy screens
const StrategiesStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        gestureEnabled: true,
      }}
    >
      <Stack.Screen name="StrategiesMain" component={StrategiesScreen} />
      <Stack.Screen name="StrategyComparison" component={StrategyComparisonScreen} />
      <Stack.Screen name="StrategyDetail" component={StrategyDetailScreen} />
    </Stack.Navigator>
  );
};

const AppNavigator = () => {
  const { theme } = useTheme();
  
  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        tabBarIcon: ({ focused, color, size }) => {
          let iconName;

          if (route.name === 'Home') {
            iconName = focused ? 'home' : 'home-outline';
          } else if (route.name === 'Portfolio') {
            iconName = focused ? 'pie-chart' : 'pie-chart-outline';
          } else if (route.name === 'Trades') {
            iconName = focused ? 'swap-horizontal' : 'swap-horizontal-outline';
          } else if (route.name === 'P&L') {
            iconName = focused ? 'analytics' : 'analytics-outline';
          } else if (route.name === 'Strategies') {
            iconName = focused ? 'rocket' : 'rocket-outline';
          } else if (route.name === 'Settings') {
            iconName = focused ? 'settings' : 'settings-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
        tabBarActiveTintColor: '#00D4FF',
        tabBarInactiveTintColor: theme.colors.textSecondary,
        tabBarStyle: {
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.border,
          borderTopWidth: 1,
          paddingBottom: 8,
          paddingTop: 8,
          height: 80,
        },
        tabBarLabelStyle: {
          fontSize: 12,
          fontWeight: '600',
        },
        headerShown: false,
      })}
    >
      <Tab.Screen 
        name="Home" 
        component={HomeScreen}
        options={{ tabBarLabel: 'Home' }}
      />
      <Tab.Screen 
        name="Portfolio" 
        component={PortfolioScreen}
        options={{ tabBarLabel: 'Portfolio' }}
      />
      <Tab.Screen 
        name="Trades" 
        component={TradesScreen}
        options={{ tabBarLabel: 'Trades' }}
      />
      <Tab.Screen 
        name="P&L" 
        component={PnLScreen}
        options={{ tabBarLabel: 'P&L' }}
      />
      <Tab.Screen 
        name="Strategies" 
        component={StrategiesStack}
        options={{ tabBarLabel: 'Strategies' }}
      />
      <Tab.Screen 
        name="Settings" 
        component={SettingsScreen}
        options={{ tabBarLabel: 'Settings' }}
      />
    </Tab.Navigator>
  );
};

export default AppNavigator;