import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';

// Import auth screens
import AuthLoadingScreen from '../screens/AuthLoadingScreen';
import LoginScreen from '../screens/LoginScreen';
import RegisterScreen from '../screens/RegisterScreen';

// Import main app navigator
import AppNavigator from './AppNavigator';

const Stack = createStackNavigator();

const AuthNavigator = () => {
  return (
    <Stack.Navigator
      initialRouteName="AuthLoading"
      screenOptions={{
        headerShown: false,
        gestureEnabled: false, // Disable swipe back for auth screens
      }}
    >
      <Stack.Screen 
        name="AuthLoading" 
        component={AuthLoadingScreen}
        options={{
          gestureEnabled: false,
        }}
      />
      <Stack.Screen 
        name="Login" 
        component={LoginScreen}
        options={{
          gestureEnabled: false,
        }}
      />
      <Stack.Screen 
        name="Register" 
        component={RegisterScreen}
        options={{
          gestureEnabled: true, // Allow back gesture from register to login
        }}
      />
      <Stack.Screen 
        name="Main" 
        component={AppNavigator}
        options={{
          gestureEnabled: false, // Don't allow swiping back to auth
        }}
      />
    </Stack.Navigator>
  );
};

export default AuthNavigator;