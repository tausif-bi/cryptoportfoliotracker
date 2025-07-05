import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  Alert,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { authService } from '../services/authService';

const LoginScreen = ({ navigation }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleLogin = async () => {
    if (!email || !password) {
      Alert.alert(
        '📝 Missing Information', 
        'Please enter both email and password to continue.',
        [{ text: 'OK', style: 'default' }]
      );
      return;
    }

    setLoading(true);
    try {
      console.log('🔐 Attempting login...');
      const result = await authService.login(email, password);
      console.log('Login result:', result);
      
      if (result.success) {
        console.log('✅ Login successful! Navigating to Main...');
        // Navigate directly without alert for web compatibility
        navigation.replace('Main');
      } else {
        // Show the detailed error message from the backend
        const errorMessage = result.message || 'Invalid credentials';
        console.log('❌ Login failed:', errorMessage);
        Alert.alert(
          '❌ Login Failed', 
          errorMessage,
          [{ text: 'Try Again', style: 'default' }]
        );
      }
    } catch (error) {
      console.error('🌐 Connection error:', error);
      Alert.alert(
        '🌐 Connection Error', 
        'Unable to connect to the server. Please check your internet connection and try again.',
        [{ text: 'OK', style: 'default' }]
      );
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = () => {
    navigation.navigate('Register');
  };

  const handleDemoMode = () => {
    // Skip authentication and go directly to main app
    navigation.replace('Main');
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <View style={styles.content}>
          {/* Header */}
          <View style={styles.header}>
            <Text style={styles.title}>Crypto Portfolio</Text>
            <Text style={styles.subtitle}>AI-Powered Trading Insights</Text>
          </View>

          {/* Login Form */}
          <View style={styles.form}>
            <TextInput
              style={styles.input}
              placeholder="Email"
              value={email}
              onChangeText={setEmail}
              keyboardType="email-address"
              autoCapitalize="none"
              autoComplete="email"
            />
            
            <TextInput
              style={styles.input}
              placeholder="Password"
              value={password}
              onChangeText={setPassword}
              secureTextEntry
              autoComplete="password"
            />

            <TouchableOpacity 
              style={[styles.button, styles.loginButton]}
              onPress={handleLogin}
              disabled={loading}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.buttonText}>Login</Text>
              )}
            </TouchableOpacity>

            <TouchableOpacity 
              style={[styles.button, styles.registerButton]}
              onPress={handleRegister}
              disabled={loading}
            >
              <Text style={[styles.buttonText, styles.registerButtonText]}>
                Create Account
              </Text>
            </TouchableOpacity>

            <TouchableOpacity 
              style={styles.demoButton}
              onPress={handleDemoMode}
              disabled={loading}
            >
              <Text style={styles.demoButtonText}>Continue with Demo</Text>
            </TouchableOpacity>
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1a1a1a',
  },
  keyboardView: {
    flex: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 30,
  },
  header: {
    alignItems: 'center',
    marginBottom: 50,
  },
  title: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 16,
    color: '#888',
    textAlign: 'center',
  },
  form: {
    gap: 15,
  },
  input: {
    backgroundColor: '#2a2a2a',
    borderRadius: 12,
    padding: 15,
    fontSize: 16,
    color: '#fff',
    borderWidth: 1,
    borderColor: '#333',
  },
  button: {
    borderRadius: 12,
    padding: 15,
    alignItems: 'center',
    marginTop: 10,
  },
  loginButton: {
    backgroundColor: '#4CAF50',
  },
  registerButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#4CAF50',
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  registerButtonText: {
    color: '#4CAF50',
  },
  demoButton: {
    marginTop: 20,
    padding: 10,
    alignItems: 'center',
  },
  demoButtonText: {
    fontSize: 14,
    color: '#888',
    textDecorationLine: 'underline',
  },
});

export default LoginScreen;