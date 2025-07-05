import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE_URL = 'http://localhost:5000/api';

class AuthService {
  constructor() {
    this.accessToken = null;
    this.refreshToken = null;
    this.isInitialized = false;
  }

  // Initialize service and load tokens from storage
  async initialize() {
    if (this.isInitialized) return;
    
    try {
      const accessToken = await AsyncStorage.getItem('accessToken');
      const refreshToken = await AsyncStorage.getItem('refreshToken');
      
      this.accessToken = accessToken;
      this.refreshToken = refreshToken;
      this.isInitialized = true;
    } catch (error) {
      console.log('Error initializing auth service:', error);
    }
  }

  // Store tokens securely
  async storeTokens(accessToken, refreshToken) {
    this.accessToken = accessToken;
    this.refreshToken = refreshToken;
    
    try {
      await AsyncStorage.setItem('accessToken', accessToken);
      await AsyncStorage.setItem('refreshToken', refreshToken);
    } catch (error) {
      console.log('Error storing tokens:', error);
    }
  }

  // Clear tokens from memory and storage
  async clearTokens() {
    this.accessToken = null;
    this.refreshToken = null;
    
    try {
      await AsyncStorage.removeItem('accessToken');
      await AsyncStorage.removeItem('refreshToken');
      await AsyncStorage.removeItem('userInfo');
    } catch (error) {
      console.log('Error clearing tokens:', error);
    }
  }

  // Register new user
  async register(username, email, password) {
    try {
      const response = await fetch(`${BASE_URL}/auth/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username,
          email,
          password,
        }),
      });

      const data = await response.json();
      console.log('Registration response status:', response.status);
      console.log('Registration response data:', data);

      if (response.ok) {
        return {
          success: true,
          message: data.message,
          user: data.user,
        };
      } else {
        console.log('Registration error details:', data);
        return {
          success: false,
          message: data.message || data.error || 'Registration failed',
          details: data
        };
      }
    } catch (error) {
      console.log('Registration error:', error);
      return {
        success: false,
        message: 'Network error. Please try again.',
      };
    }
  }

  // Login user
  async login(email, password) {
    try {
      const response = await fetch(`${BASE_URL}/auth/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          username_or_email: email,
          password,
        }),
      });

      const data = await response.json();

      if (response.ok) {
        // Store tokens and user info
        await this.storeTokens(data.access_token, data.refresh_token);
        await AsyncStorage.setItem('userInfo', JSON.stringify(data.user));

        return {
          success: true,
          user: data.user,
          tokens: {
            accessToken: data.access_token,
            refreshToken: data.refresh_token,
          },
        };
      } else {
        console.log('Login error details:', data);
        return {
          success: false,
          message: data.message || data.error || 'Login failed',
          details: data
        };
      }
    } catch (error) {
      console.log('Login error:', error);
      return {
        success: false,
        message: 'Network error. Please try again.',
      };
    }
  }

  // Logout user
  async logout() {
    try {
      // Call logout endpoint if token exists
      if (this.accessToken) {
        await fetch(`${BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${this.accessToken}`,
            'Content-Type': 'application/json',
          },
        });
      }
    } catch (error) {
      console.log('Logout API error:', error);
    } finally {
      // Always clear local tokens
      await this.clearTokens();
    }
  }

  // Refresh access token
  async refreshAccessToken() {
    if (!this.refreshToken) {
      throw new Error('No refresh token available');
    }

    try {
      const response = await fetch(`${BASE_URL}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${this.refreshToken}`,
          'Content-Type': 'application/json',
        },
      });

      const data = await response.json();

      if (response.ok) {
        this.accessToken = data.access_token;
        await AsyncStorage.setItem('accessToken', data.access_token);
        return data.access_token;
      } else {
        // Refresh token is invalid, need to re-login
        await this.clearTokens();
        throw new Error('Refresh token expired');
      }
    } catch (error) {
      await this.clearTokens();
      throw error;
    }
  }

  // Check if user is authenticated
  async checkAuthStatus() {
    await this.initialize();
    
    if (!this.accessToken) {
      return false;
    }

    try {
      // Try to get user profile to verify token
      const response = await fetch(`${BASE_URL}/auth/profile`, {
        headers: {
          'Authorization': `Bearer ${this.accessToken}`,
        },
      });

      if (response.ok) {
        return true;
      } else if (response.status === 401) {
        // Token expired, try to refresh
        try {
          await this.refreshAccessToken();
          return true;
        } catch (refreshError) {
          return false;
        }
      } else {
        return false;
      }
    } catch (error) {
      console.log('Auth status check error:', error);
      return false;
    }
  }

  // Get current user info
  async getCurrentUser() {
    try {
      const userInfo = await AsyncStorage.getItem('userInfo');
      return userInfo ? JSON.parse(userInfo) : null;
    } catch (error) {
      console.log('Error getting user info:', error);
      return null;
    }
  }

  // Make authenticated API request
  async authenticatedRequest(url, options = {}) {
    await this.initialize();

    // Prepare headers
    const headers = {
      'Content-Type': 'application/json',
      ...options.headers,
    };

    // Add auth token if available
    if (this.accessToken) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    try {
      const response = await fetch(url, {
        ...options,
        headers,
      });

      // Handle token expiration
      if (response.status === 401 && this.refreshToken) {
        try {
          await this.refreshAccessToken();
          // Retry request with new token
          headers['Authorization'] = `Bearer ${this.accessToken}`;
          return await fetch(url, {
            ...options,
            headers,
          });
        } catch (refreshError) {
          // Refresh failed, user needs to login again
          await this.clearTokens();
          throw new Error('Authentication expired');
        }
      }

      return response;
    } catch (error) {
      throw error;
    }
  }

  // Get access token (for direct use)
  async getAccessToken() {
    await this.initialize();
    return this.accessToken;
  }

  // Check if user is logged in (without network call)
  isLoggedIn() {
    return !!this.accessToken;
  }
}

export const authService = new AuthService();