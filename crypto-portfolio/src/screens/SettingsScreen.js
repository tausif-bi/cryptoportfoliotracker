import React, { useState, useEffect, useContext } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  TextInput,
  Modal,
  Alert,
  Switch,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { Ionicons } from '@expo/vector-icons';
import { CommonActions, useNavigation } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import exchangeService from '../services/exchangeService';
import aiService from '../services/aiService';
import { authService } from '../services/authService';
import { ThemeContext, useTheme } from '../theme/ThemeContext';

const SettingsScreen = ({ navigation }) => {
  const rootNavigation = useNavigation();
  const themeContext = useContext(ThemeContext);
  const { theme } = useTheme();
  const [showExchangeModal, setShowExchangeModal] = useState(false);
  const [selectedExchange, setSelectedExchange] = useState('binance');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [apiPassword, setApiPassword] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const [currentExchange, setCurrentExchange] = useState(null);
  const [aiEnabled, setAiEnabled] = useState(true);
  const [notifications, setNotifications] = useState(true);
  const [darkMode, setDarkMode] = useState(themeContext?.isDarkMode ?? true);
  const [backendUrl, setBackendUrl] = useState('http://localhost:5000/api');
  
  // Add loading state to prevent race conditions
  const [isLoading, setIsLoading] = useState(true);

  // Comment out themeContext if causing issues
  // const themeContext = useContext(ThemeContext);

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      console.log('Loading settings...');
      setIsLoading(true);
      
      // Check if exchange is connected
      const savedCredentials = await AsyncStorage.getItem('exchange_credentials');
      console.log('Checking saved credentials:', savedCredentials ? 'Found' : 'Not found');
      
      if (savedCredentials) {
        try {
          const credentials = JSON.parse(savedCredentials);
          setIsConnected(true);
          setCurrentExchange(credentials.exchangeName);
          console.log('Restored connection to:', credentials.exchangeName);
        } catch (parseError) {
          console.error('Error parsing credentials:', parseError);
          // Clear corrupted credentials
          await AsyncStorage.removeItem('exchange_credentials');
          setIsConnected(false);
          setCurrentExchange(null);
        }
      } else {
        setIsConnected(false);
        setCurrentExchange(null);
        console.log('No saved credentials found');
      }
      
      // Load other app settings
      try {
        const settings = await AsyncStorage.getItem('app_settings');
        if (settings) {
          const parsed = JSON.parse(settings);
          setAiEnabled(parsed.aiEnabled ?? true);
          setNotifications(parsed.notifications ?? true);
          setBackendUrl(parsed.backendUrl ?? 'http://localhost:5000/api');
          console.log('App settings loaded');
        }
        
        // Sync dark mode with ThemeContext
        if (themeContext?.isDarkMode !== undefined) {
          setDarkMode(themeContext.isDarkMode);
          console.log('Dark mode synced with theme context:', themeContext.isDarkMode);
        }
      } catch (settingsError) {
        console.error('Error loading app settings:', settingsError);
      }
      
    } catch (error) {
      console.error('Error in loadSettings:', error);
      // On error, ensure we're in disconnected state
      setIsConnected(false);
      setCurrentExchange(null);
    } finally {
      setIsLoading(false);
    }
  };

  const saveSettings = async () => {
    try {
      const settings = {
        aiEnabled,
        notifications,
        darkMode,
        backendUrl,
      };
      await AsyncStorage.setItem('app_settings', JSON.stringify(settings));
      
      // Update AI service URL
      aiService.setBackendURL(backendUrl);
      
      Alert.alert('Success', 'Settings saved successfully');
    } catch (error) {
      console.error('Error saving settings:', error);
      Alert.alert('Error', 'Failed to save settings');
    }
  };

  const connectExchange = async () => {
    try {
      // For demo mode, use dummy credentials
      if (selectedExchange === 'demo') {
        await exchangeService.initializeExchange(
          'demo',
          'demo-api-key',
          'demo-api-secret',
          null
        );
        
        setIsConnected(true);
        setCurrentExchange('demo');
        setShowExchangeModal(false);
        
        Alert.alert('Success', 'Connected to Demo Mode with synthetic data');
        return;
      }
      
      if (!apiKey || !apiSecret) {
        Alert.alert('Error', 'Please enter API key and secret');
        return;
      }
      
      await exchangeService.initializeExchange(
        selectedExchange,
        apiKey,
        apiSecret,
        apiPassword || null
      );
      
      setIsConnected(true);
      setCurrentExchange(selectedExchange);
      setShowExchangeModal(false);
      
      // Clear form
      setApiKey('');
      setApiSecret('');
      setApiPassword('');
      
      Alert.alert('Success', 'Exchange connected successfully');
    } catch (error) {
      console.error('Error connecting exchange:', error);
      Alert.alert('Error', 'Failed to connect exchange. Please check your credentials.');
    }
  };

  // FIXED DISCONNECT FUNCTION - This is the key fix!
  const disconnectExchange = async () => {
    console.log('Disconnect button pressed');
    
    // Skip Alert.alert for web compatibility, go straight to disconnect
    console.log('Starting disconnect process...');
    
    try {
      // Step 1: Clear AsyncStorage FIRST
      console.log('Step 1: Clearing AsyncStorage...');
      await AsyncStorage.multiRemove([
        'exchange_credentials',
        'portfolio_data', 
        'trade_history',
        'portfolio_analysis_cache'
      ]);
      console.log('AsyncStorage cleared successfully');
      
      // Step 2: Clear exchangeService state
      console.log('Step 2: Clearing exchangeService...');
      exchangeService.exchangeName = null;
      exchangeService.apiKey = null;
      exchangeService.apiSecret = null;
      console.log('ExchangeService cleared');
      
      // Step 3: Update component state IMMEDIATELY
      console.log('Step 3: Updating component state...');
      setIsConnected(false);
      setCurrentExchange(null);
      setApiKey('');
      setApiSecret('');
      setApiPassword('');
      console.log('Component state updated');
      
      // Step 4: Verify AsyncStorage is actually cleared
      const verification = await AsyncStorage.getItem('exchange_credentials');
      console.log('Verification - credentials after clear:', verification);
      
      console.log('✅ Exchange disconnected successfully');
      
    } catch (error) {
      console.error('❌ Error during disconnect:', error);
    }
  };

  // Fixed toggle functions
  const handleDarkModeToggle = async (value) => {
    console.log('Dark mode toggled:', value);
    
    try {
      setDarkMode(value);
      
      // Update theme context to actually apply the theme change
      if (themeContext && themeContext.setDarkMode) {
        await themeContext.setDarkMode(value);
        console.log('Theme context updated successfully');
      }
      
      console.log('Dark mode saved:', value);
    } catch (error) {
      console.error('Error saving dark mode:', error);
    }
  };

  const handleNotificationsToggle = async (value) => {
    console.log('Notifications toggled:', value);
    
    try {
      setNotifications(value);
      
      const settings = await AsyncStorage.getItem('app_settings');
      const parsed = settings ? JSON.parse(settings) : {};
      parsed.notifications = value;
      await AsyncStorage.setItem('app_settings', JSON.stringify(parsed));
      
      console.log('Notifications saved:', value);
      
    } catch (error) {
      console.error('Error saving notifications:', error);
    }
  };

  const handleAiToggle = async (value) => {
    console.log('AI toggled:', value);
    
    try {
      setAiEnabled(value);
      
      const settings = await AsyncStorage.getItem('app_settings');
      const parsed = settings ? JSON.parse(settings) : {};
      parsed.aiEnabled = value;
      await AsyncStorage.setItem('app_settings', JSON.stringify(parsed));
      
      console.log('AI enabled saved:', value);
      
    } catch (error) {
      console.error('Error saving AI setting:', error);
    }
  };


  const exchanges = exchangeService.constructor.getSupportedExchanges();

  const handleLogout = async () => {
    console.log('=== LOGOUT BUTTON PRESSED ===');
    
    // Skip Alert.alert for web compatibility, go straight to logout
    try {
      console.log('=== STARTING LOGOUT PROCESS ===');
      console.log('Navigation object:', navigation);
      console.log('Root navigation object:', rootNavigation);
      
      // Call logout service
      await authService.logout();
      console.log('✅ Auth service logout completed');
      
      // Try immediate navigation
      console.log('🔄 Attempting navigation reset...');
      
      // Try multiple navigation approaches
      try {
        // Approach 1: Use root navigation
        console.log('Trying approach 1: root navigation reset');
        rootNavigation.dispatch(
          CommonActions.reset({
            index: 0,
            routes: [{ name: 'AuthLoading' }],
          })
        );
        console.log('✅ Root navigation reset dispatched');
      } catch (nav1Error) {
        console.log('❌ Approach 1 failed:', nav1Error);
        
        try {
          // Approach 2: Use prop navigation
          console.log('Trying approach 2: prop navigation reset');
          navigation.dispatch(
            CommonActions.reset({
              index: 0,
              routes: [{ name: 'AuthLoading' }],
            })
          );
          console.log('✅ Prop navigation reset dispatched');
        } catch (nav2Error) {
          console.log('❌ Approach 2 failed:', nav2Error);
          
          try {
            // Approach 3: Navigate to AuthLoading directly
            console.log('Trying approach 3: direct navigation');
            navigation.navigate('AuthLoading');
            console.log('✅ Direct navigation attempted');
          } catch (nav3Error) {
            console.log('❌ Approach 3 failed:', nav3Error);
            console.log('All navigation approaches failed');
          }
        }
      }
      
      console.log('✅ Logout process completed');
      
    } catch (error) {
      console.error('❌ Logout error:', error);
    }
  };

  // Create dynamic styles based on theme
  const styles = createStyles(theme);

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Settings</Text>
      </View>

      {/* Exchange Connection */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Exchange Connection</Text>
        
        {isConnected ? (
          <View style={styles.connectedCard}>
            <LinearGradient
              colors={['#00F89E20', '#00F89E10']}
              style={styles.connectedGradient}
            >
              <View style={styles.connectedInfo}>
                <Ionicons name="checkmark-circle" size={24} color="#00F89E" />
                <View style={styles.connectedText}>
                  <Text style={styles.connectedLabel}>Connected to</Text>
                  <Text style={styles.connectedExchange}>{currentExchange}</Text>
                </View>
              </View>
              <TouchableOpacity 
                onPress={disconnectExchange}
                style={styles.disconnectButtonContainer}
                activeOpacity={0.7}
              >
                <Text style={styles.disconnectButton}>Disconnect</Text>
              </TouchableOpacity>
            </LinearGradient>
          </View>
        ) : (
          <TouchableOpacity 
            style={styles.connectButton}
            onPress={() => setShowExchangeModal(true)}
            activeOpacity={0.8}
          >
            <LinearGradient
              colors={['#00D4FF', '#0099CC']}
              style={styles.connectGradient}
            >
              <Ionicons name="link-outline" size={20} color={theme.colors.text} />
              <Text style={styles.connectText}>Connect Exchange</Text>
            </LinearGradient>
          </TouchableOpacity>
        )}
      </View>


      {/* AI Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>AI & Analysis</Text>
        
        <View style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Ionicons name="bulb-outline" size={24} color="#00D4FF" />
            <Text style={styles.settingLabel}>AI Insights</Text>
          </View>
          <Switch
            value={aiEnabled}
            onValueChange={handleAiToggle}
            trackColor={{ false: '#151A21', true: '#00D4FF40' }}
            thumbColor={aiEnabled ? '#00D4FF' : '#8B95A7'}
            ios_backgroundColor="#151A21"
          />
        </View>
        
        <View style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Ionicons name="server-outline" size={24} color="#00D4FF" />
            <Text style={styles.settingLabel}>Backend URL</Text>
          </View>
        </View>
        <TextInput
          style={styles.urlInput}
          value={backendUrl}
          onChangeText={setBackendUrl}
          placeholder="http://localhost:5000/api"
          placeholderTextColor="#8B95A7"
        />
      </View>

      {/* App Settings */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>App Settings</Text>
        
        <View style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Ionicons name="notifications-outline" size={24} color="#00D4FF" />
            <Text style={styles.settingLabel}>Notifications</Text>
          </View>
          <Switch
            value={notifications}
            onValueChange={handleNotificationsToggle}
            trackColor={{ false: '#151A21', true: '#00D4FF40' }}
            thumbColor={notifications ? '#00D4FF' : '#8B95A7'}
            ios_backgroundColor="#151A21"
          />
        </View>
        
        <View style={styles.settingItem}>
          <View style={styles.settingLeft}>
            <Ionicons name="moon-outline" size={24} color="#00D4FF" />
            <Text style={styles.settingLabel}>Dark Mode</Text>
          </View>
          <Switch
            value={darkMode}
            onValueChange={handleDarkModeToggle}
            trackColor={{ false: '#151A21', true: '#00D4FF40' }}
            thumbColor={darkMode ? '#00D4FF' : '#8B95A7'}
            ios_backgroundColor="#151A21"
          />
        </View>
      </View>

      {/* Save Button */}
      <TouchableOpacity 
        style={styles.saveButton} 
        onPress={saveSettings}
        activeOpacity={0.8}
      >
        <LinearGradient
          colors={['#00D4FF', '#0099CC']}
          style={styles.saveGradient}
        >
          <Text style={styles.saveText}>Save Settings</Text>
        </LinearGradient>
      </TouchableOpacity>

      {/* Account Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Account</Text>
        
        <TouchableOpacity 
          style={styles.logoutButton}
          onPress={handleLogout}
          activeOpacity={0.8}
        >
          <View style={styles.settingLeft}>
            <Ionicons name="log-out-outline" size={24} color="#FF3B5C" />
            <Text style={[styles.settingLabel, { color: '#FF3B5C' }]}>Logout</Text>
          </View>
          <Ionicons name="chevron-forward" size={20} color="#FF3B5C" />
        </TouchableOpacity>
      </View>

      {/* About Section */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About</Text>
        <View style={styles.aboutItem}>
          <Text style={styles.aboutLabel}>Version</Text>
          <Text style={styles.aboutValue}>1.0.0</Text>
        </View>
        <View style={styles.aboutItem}>
          <Text style={styles.aboutLabel}>Developer</Text>
          <Text style={styles.aboutValue}>Crypto Portfolio Tracker</Text>
        </View>
      </View>

      {/* Exchange Connection Modal */}
      <Modal
        visible={showExchangeModal}
        animationType="slide"
        transparent={true}
        onRequestClose={() => setShowExchangeModal(false)}
      >
        <View style={styles.modalContainer}>
          <View style={styles.modalContent}>
            <View style={styles.modalHeader}>
              <Text style={styles.modalTitle}>Connect Exchange</Text>
              <TouchableOpacity onPress={() => setShowExchangeModal(false)}>
                <Ionicons name="close" size={24} color="#8B95A7" />
              </TouchableOpacity>
            </View>

            <ScrollView style={styles.modalBody}>
              <Text style={styles.inputLabel}>Select Exchange</Text>
              <ScrollView horizontal showsHorizontalScrollIndicator={false}>
                {exchanges.map((exchange) => (
                  <TouchableOpacity
                    key={exchange}
                    style={[
                      styles.exchangeOption,
                      selectedExchange === exchange && styles.exchangeOptionActive
                    ]}
                    onPress={() => setSelectedExchange(exchange)}
                  >
                    <Text style={[
                      styles.exchangeOptionText,
                      selectedExchange === exchange && styles.exchangeOptionTextActive
                    ]}>
                      {exchange.toUpperCase()}
                    </Text>
                  </TouchableOpacity>
                ))}
              </ScrollView>

              {/* Demo mode notice */}
              {selectedExchange === 'demo' && (
                <View style={styles.warningBox}>
                  <Ionicons name="information-circle" size={20} color="#00D4FF" />
                  <Text style={styles.warningText}>
                    Demo mode - No API credentials required. Just click Connect to use synthetic data with 1000+ trades.
                  </Text>
                </View>
              )}
              
              {/* LBank notice */}
              {selectedExchange === 'lbank2' && (
                <View style={[styles.warningBox, { borderColor: '#FF6B6B30', backgroundColor: '#FF6B6B10' }]}>
                  <Ionicons name="alert-circle" size={20} color="#FF6B6B" />
                  <Text style={[styles.warningText, { color: '#FF6B6B' }]}>
                    Important: LBank requires the API Secret (not RSA private key). 
                    In your LBank API settings, use the "Secret Key" field, NOT the RSA private key option.
                    The secret should be a short alphanumeric string, not a long RSA key.
                  </Text>
                </View>
              )}
              
              {/* Hide API inputs for demo mode */}
              {selectedExchange !== 'demo' && (
                <>
                  <Text style={styles.inputLabel}>API Key</Text>
                  <TextInput
                    style={styles.input}
                    value={apiKey}
                    onChangeText={setApiKey}
                    placeholder="Enter your API key"
                    placeholderTextColor="#8B95A7"
                  />

                  <Text style={styles.inputLabel}>API Secret</Text>
                  <TextInput
                    style={styles.input}
                    value={apiSecret}
                    onChangeText={setApiSecret}
                    placeholder="Enter your API secret"
                    placeholderTextColor="#8B95A7"
                    secureTextEntry
                  />
                </>
              )}

              {/* Show password field for exchanges that require it */}
              {['kucoin', 'okex', 'mexc'].includes(selectedExchange) && (
                <>
                  <Text style={styles.inputLabel}>API Password (required for {selectedExchange})</Text>
                  <TextInput
                    style={styles.input}
                    value={apiPassword}
                    onChangeText={setApiPassword}
                    placeholder="Enter your API password"
                    placeholderTextColor="#8B95A7"
                    secureTextEntry
                  />
                </>
              )}

              <View style={styles.warningBox}>
                <Ionicons name="warning" size={20} color="#FFB800" />
                <Text style={styles.warningText}>
                  Only use API keys with read-only permissions. Never share your API credentials.
                </Text>
              </View>

              <TouchableOpacity style={styles.connectModalButton} onPress={connectExchange}>
                <LinearGradient
                  colors={['#00D4FF', '#0099CC']}
                  style={styles.connectModalGradient}
                >
                  <Text style={styles.connectModalText}>Connect</Text>
                </LinearGradient>
              </TouchableOpacity>
            </ScrollView>
          </View>
        </View>
      </Modal>
    </ScrollView>
  );
};

const createStyles = (theme) => StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.colors.background,
  },
  header: {
    paddingHorizontal: 20,
    paddingTop: 60,
    paddingBottom: 20,
  },
  headerTitle: {
    fontSize: 28,
    fontWeight: 'bold',
    color: theme.colors.text,
  },
  section: {
    paddingHorizontal: 20,
    marginBottom: 30,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: theme.colors.text,
    marginBottom: 16,
  },
  connectedCard: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  connectedGradient: {
    padding: 20,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: '#00F89E30',
    borderRadius: 16,
  },
  connectedInfo: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  connectedText: {
    marginLeft: 12,
  },
  connectedLabel: {
    fontSize: 12,
    color: '#8B95A7',
  },
  connectedExchange: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    textTransform: 'capitalize',
  },
  disconnectButtonContainer: {
    padding: 5,
  },
  disconnectButton: {
    fontSize: 14,
    color: '#FF3B5C',
    fontWeight: '600',
  },
  connectButton: {
    borderRadius: 16,
    overflow: 'hidden',
  },
  connectGradient: {
    padding: 16,
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 16,
  },
  connectText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
    marginLeft: 8,
  },
  settingItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 12,
    marginBottom: 12,
  },
  settingLeft: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  settingLabel: {
    fontSize: 16,
    color: theme.colors.text,
    marginLeft: 12,
  },
  urlInput: {
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 12,
    color: theme.colors.text,
    fontSize: 14,
    marginTop: -8,
  },
  saveButton: {
    marginHorizontal: 20,
    marginBottom: 20,
    borderRadius: 16,
    overflow: 'hidden',
  },
  saveGradient: {
    padding: 16,
    alignItems: 'center',
    borderRadius: 16,
  },
  saveText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  aboutItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  aboutLabel: {
    fontSize: 14,
    color: '#8B95A7',
  },
  aboutValue: {
    fontSize: 14,
    color: theme.colors.text,
  },
  logoutButton: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: theme.colors.surface,
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#FF3B5C20',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: '#151A21',
    borderTopLeftRadius: 24,
    borderTopRightRadius: 24,
    maxHeight: '80%',
  },
  modalHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#1A1F29',
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: '600',
    color: '#FFFFFF',
  },
  modalBody: {
    padding: 20,
  },
  inputLabel: {
    fontSize: 14,
    color: '#8B95A7',
    marginBottom: 8,
    marginTop: 16,
  },
  input: {
    backgroundColor: '#1A1F29',
    padding: 16,
    borderRadius: 12,
    color: '#FFFFFF',
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#2A2F39',
  },
  exchangeOption: {
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: '#1A1F29',
    marginRight: 10,
    borderWidth: 1,
    borderColor: '#2A2F39',
  },
  exchangeOptionActive: {
    backgroundColor: '#00D4FF20',
    borderColor: '#00D4FF',
  },
  exchangeOptionText: {
    fontSize: 14,
    color: '#8B95A7',
    fontWeight: '500',
  },
  exchangeOptionTextActive: {
    color: '#00D4FF',
  },
  warningBox: {
    flexDirection: 'row',
    backgroundColor: '#FFB80010',
    padding: 16,
    borderRadius: 12,
    marginTop: 20,
    borderWidth: 1,
    borderColor: '#FFB80030',
  },
  warningText: {
    fontSize: 12,
    color: '#FFB800',
    marginLeft: 8,
    flex: 1,
    lineHeight: 18,
  },
  connectModalButton: {
    marginTop: 20,
    borderRadius: 16,
    overflow: 'hidden',
  },
  connectModalGradient: {
    padding: 16,
    alignItems: 'center',
    borderRadius: 16,
  },
  connectModalText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#FFFFFF',
  },
});

export default SettingsScreen;