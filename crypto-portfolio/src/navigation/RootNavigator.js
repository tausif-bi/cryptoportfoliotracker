import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';

// Import screens
import LandingPage from '../screens/LandingPage';
import AuthNavigator from './AuthNavigator';

const Stack = createStackNavigator();

const RootNavigator = () => {
  return (
    <Stack.Navigator
      initialRouteName="Landing"
      screenOptions={{
        headerShown: false,
        gestureEnabled: false,
      }}
    >
      <Stack.Screen 
        name="Landing" 
        component={LandingPage}
        options={{
          gestureEnabled: false,
          cardStyle: { flex: 1 },
        }}
      />
      <Stack.Screen 
        name="Auth" 
        component={AuthNavigator}
        options={{
          gestureEnabled: false,
        }}
      />
    </Stack.Navigator>
  );
};

export default RootNavigator;