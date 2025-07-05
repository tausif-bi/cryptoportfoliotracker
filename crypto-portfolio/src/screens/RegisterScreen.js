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
  ScrollView,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { authService } from '../services/authService';

const RegisterScreen = ({ navigation }) => {
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  });
  const [loading, setLoading] = useState(false);

  const updateFormData = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
  };

  const validateForm = () => {
    const { username, email, password, confirmPassword } = formData;

    if (!username || !email || !password || !confirmPassword) {
      Alert.alert(
        '📝 Missing Information', 
        'Please fill in all required fields to continue.',
        [{ text: 'OK', style: 'default' }]
      );
      return false;
    }

    if (username.length < 3) {
      Alert.alert(
        '👤 Invalid Username', 
        'Username must be at least 3 characters long.',
        [{ text: 'OK', style: 'default' }]
      );
      return false;
    }

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
      Alert.alert(
        '📧 Invalid Email', 
        'Please enter a valid email address (e.g., user@example.com).',
        [{ text: 'OK', style: 'default' }]
      );
      return false;
    }

    if (password.length < 8) {
      Alert.alert(
        '🔒 Weak Password', 
        'Password must be at least 8 characters long for security.',
        [{ text: 'OK', style: 'default' }]
      );
      return false;
    }

    // Check if password contains at least one letter
    if (!/[a-zA-Z]/.test(password)) {
      Alert.alert(
        '🔒 Weak Password', 
        'Password must contain at least one letter.',
        [{ text: 'OK', style: 'default' }]
      );
      return false;
    }

    // Check if password contains at least one number
    if (!/\d/.test(password)) {
      Alert.alert(
        '🔒 Weak Password', 
        'Password must contain at least one number.',
        [{ text: 'OK', style: 'default' }]
      );
      return false;
    }

    if (password !== confirmPassword) {
      Alert.alert(
        '🔒 Password Mismatch', 
        'The passwords you entered do not match. Please try again.',
        [{ text: 'OK', style: 'default' }]
      );
      return false;
    }

    return true;
  };

  const handleRegister = async () => {
    if (!validateForm()) {
      return;
    }

    setLoading(true);
    try {
      const { username, email, password } = formData;
      const result = await authService.register(username, email, password);
      
      console.log('Registration result:', result);
      
      if (result.success) {
        Alert.alert(
          '🎉 Success!',
          'Your account has been created successfully!\n\nYou can now login with your credentials.',
          [
            {
              text: 'Continue to Login',
              onPress: () => navigation.replace('Login'),
            },
          ],
          { cancelable: false }
        );
      } else {
        // Show the detailed error message from the backend
        const errorMessage = result.message || 'Failed to create account';
        Alert.alert(
          '❌ Registration Failed', 
          errorMessage,
          [{ text: 'Try Again', style: 'default' }]
        );
      }
    } catch (error) {
      Alert.alert(
        '🌐 Connection Error', 
        'Unable to connect to the server. Please check your internet connection and try again.',
        [{ text: 'OK', style: 'default' }]
      );
    } finally {
      setLoading(false);
    }
  };

  const handleBackToLogin = () => {
    navigation.goBack();
  };

  return (
    <SafeAreaView style={styles.container}>
      <KeyboardAvoidingView 
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.keyboardView}
      >
        <ScrollView contentContainerStyle={styles.scrollContent}>
          <View style={styles.content}>
            {/* Header */}
            <View style={styles.header}>
              <Text style={styles.title}>Create Account</Text>
              <Text style={styles.subtitle}>Join the crypto trading community</Text>
            </View>

            {/* Registration Form */}
            <View style={styles.form}>
              <TextInput
                style={styles.input}
                placeholder="Username"
                value={formData.username}
                onChangeText={(value) => updateFormData('username', value)}
                autoCapitalize="none"
                autoComplete="username"
              />
              
              <TextInput
                style={styles.input}
                placeholder="Email"
                value={formData.email}
                onChangeText={(value) => updateFormData('email', value)}
                keyboardType="email-address"
                autoCapitalize="none"
                autoComplete="email"
              />
              
              <TextInput
                style={styles.input}
                placeholder="Password"
                value={formData.password}
                onChangeText={(value) => updateFormData('password', value)}
                secureTextEntry
                autoComplete="new-password"
              />

              <TextInput
                style={styles.input}
                placeholder="Confirm Password"
                value={formData.confirmPassword}
                onChangeText={(value) => updateFormData('confirmPassword', value)}
                secureTextEntry
                autoComplete="new-password"
              />

              {/* Password Requirements */}
              <View style={styles.passwordHints}>
                <Text style={styles.hintTitle}>Password Requirements:</Text>
                <Text style={styles.hintText}>• At least 8 characters long</Text>
                <Text style={styles.hintText}>• Must contain at least one letter</Text>
                <Text style={styles.hintText}>• Must contain at least one number</Text>
              </View>

              <TouchableOpacity 
                style={[styles.button, styles.registerButton]}
                onPress={handleRegister}
                disabled={loading}
              >
                {loading ? (
                  <ActivityIndicator color="#fff" />
                ) : (
                  <Text style={styles.buttonText}>Create Account</Text>
                )}
              </TouchableOpacity>

              <TouchableOpacity 
                style={[styles.button, styles.loginButton]}
                onPress={handleBackToLogin}
                disabled={loading}
              >
                <Text style={[styles.buttonText, styles.loginButtonText]}>
                  Back to Login
                </Text>
              </TouchableOpacity>
            </View>

            {/* Terms */}
            <Text style={styles.termsText}>
              By creating an account, you agree to our Terms of Service and Privacy Policy
            </Text>
          </View>
        </ScrollView>
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
  scrollContent: {
    flexGrow: 1,
  },
  content: {
    flex: 1,
    justifyContent: 'center',
    paddingHorizontal: 30,
    paddingVertical: 20,
  },
  header: {
    alignItems: 'center',
    marginBottom: 40,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    color: '#fff',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 16,
    color: '#888',
    textAlign: 'center',
  },
  form: {
    gap: 15,
    marginBottom: 30,
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
  registerButton: {
    backgroundColor: '#4CAF50',
  },
  loginButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#4CAF50',
  },
  buttonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
  loginButtonText: {
    color: '#4CAF50',
  },
  termsText: {
    fontSize: 12,
    color: '#666',
    textAlign: 'center',
    lineHeight: 16,
  },
  passwordHints: {
    backgroundColor: '#2a2a2a',
    borderRadius: 8,
    padding: 12,
    marginTop: 10,
    borderWidth: 1,
    borderColor: '#333',
  },
  hintTitle: {
    fontSize: 12,
    color: '#4CAF50',
    fontWeight: '600',
    marginBottom: 4,
  },
  hintText: {
    fontSize: 11,
    color: '#888',
    lineHeight: 16,
  },
});

export default RegisterScreen;