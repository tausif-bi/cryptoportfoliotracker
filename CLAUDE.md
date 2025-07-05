# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a crypto portfolio tracking application with AI-powered trading insights. The system consists of:

- **Frontend**: React Native mobile app (expo-based) in `crypto-portfolio/`
- **Backend**: Python Flask API with AI trading strategies in `crypto-ai-backend/`

## Common Development Commands

### Frontend (React Native/Expo)
```bash
cd crypto-portfolio
npm install                    # Install dependencies
npm start                     # Start Expo development server
npm run android               # Run on Android
npm run ios                   # Run on iOS
npm run web                   # Run in web browser
```

### Backend (Flask API)
```bash
cd crypto-ai-backend
python -m venv venv           # Create virtual environment
source venv/bin/activate      # Activate venv (Linux/Mac)
venv\Scripts\activate         # Activate venv (Windows)
pip install -r requirements.txt  # Install dependencies
python app.py                 # Start Flask development server (runs on port 5000)
```

### Testing and Debugging
- **Implementation Tests**: Run `python test_implementation.py` for comprehensive testing
- **Database Tests**: Use `python init_db.py check` to verify database connection
- **Migration Tests**: Use `python init_db.py migrate` to test data migration
- **Frontend Debug**: HomeScreen contains debug button for API connectivity testing  
- **Strategy Testing**: Run `python simulate_trades.py` to test trading strategies
- **API Testing**: All endpoints include proper validation and error handling

## Architecture Overview

### Critical Architecture Notes
- **Monolithic Backend**: The main `app.py` file contains 1900+ lines with all API endpoints, business logic, and data processing in a single file
- **No Database**: Data persistence uses JSON files (`simulated_trades.json`, `simulated_trades.csv`) and AsyncStorage
- **Hardcoded Network Config**: Frontend connects via hardcoded IP address (`192.168.0.177:5000`) - update in `exchangeService.js:8` when needed
- **Thread Safety**: Matplotlib configured with 'Agg' backend for Flask threading compatibility

### Backend Structure (`crypto-ai-backend/`)
- **app.py**: Main Flask application with all API endpoints (monolithic - needs refactoring)
- **strategies/**: Trading strategy implementations with base classes and inheritance
  - `technical/trendline_breakout.py`: Primary strategy with FIFO position tracking and chart generation
  - `arbitrage/`, `ml/`, `sentiment/`, `custom/`: Strategy category folders
- **models/portfolio_analyzer.py**: PortfolioAnalyzer class with CCXT integration and technical indicators
- **services/prediction_service.py**: ML models and prediction logic
- **simulate_trades.py**: Strategy backtesting and P&L calculation system

### Frontend Structure (`crypto-portfolio/`)
- **src/screens/**: React Native screens with bottom tab navigation
- **src/components/**: Reusable UI components (Chart uses react-native-chart-kit)
- **src/services/**: API integration layer
  - `exchangeService.js`: Primary service class with AsyncStorage credential management
  - `aiService.js`: AI analysis API calls
  - `api.js`: Base API configuration
- **src/theme/ThemeContext.js**: Dark theme implementation

### Data Flow Architecture
1. **Authentication**: JWT-based auth with access/refresh tokens and secure password hashing
2. **Data Storage**: PostgreSQL database with proper models for users, portfolios, trades, and holdings
3. **API Communication**: Frontend → Authenticated Flask API → CCXT → Exchange APIs
4. **Real-time Updates**: WebSocket connections for live price feeds and portfolio updates
5. **Chart Generation**: Interactive chart data (JSON) instead of static images
6. **Strategy Analysis**: Database-backed analysis with signal generation and P&L calculation

### Key Dependencies
- **CCXT (v4.1.22)**: Multi-exchange integration (Binance primary, LBank, Coinbase support)
- **Flask-CORS**: Cross-origin handling for React Native
- **Flask-SQLAlchemy**: Database ORM with PostgreSQL support
- **Flask-JWT-Extended**: JWT authentication with token refresh
- **Flask-SocketIO**: WebSocket support for real-time updates
- **Pandas/NumPy**: Data manipulation and technical analysis
- **TA Library**: Technical indicators (RSI, MACD, Bollinger Bands, etc.)
- **Scikit-learn**: ML models for portfolio analysis
- **React Navigation**: Bottom tabs and stack navigation

## Development Considerations

### Code Quality Issues
- **Large Files**: `app.py` is 1900+ lines and should be modularized into separate route handlers
- **No Error Handling**: Limited try/catch blocks and no proper error logging framework
- **Security Concerns**: API keys stored unencrypted, no input validation, hardcoded credentials
- **No Type Checking**: No TypeScript or Python type hints
- **Code Duplication**: Multiple functions generate similar mock data patterns

### Network Configuration
- Frontend hardcoded to `192.168.0.177:5000` in `exchangeService.js:8`
- Change IP when deploying or testing on different networks
- No environment variable configuration system
- CORS enabled for all origins (security risk)

### Exchange Integration Patterns
- **CCXT Initialization**: Each strategy creates new exchange instances (inefficient)
- **Demo Mode**: Mock data available when exchange APIs fail
- **Rate Limiting**: CCXT `enableRateLimit: True` used to prevent API abuse
- **Credential Management**: AsyncStorage stores exchange credentials locally

### Strategy Development Pattern
All trading strategies follow this inheritance pattern:
```python
class NewStrategy:
    def __init__(self, parameters):
        self.name = "Strategy Name"
        
    def fetch_data(self, symbol, timeframe, limit):
        # CCXT data fetching
        
    def generate_signals(self, df):
        # Analysis logic returns buy/sell signals
        
    def calculate_pnl(self, signals):
        # FIFO matching for P&L calculation
```

## Development Workflow

### Adding New Trading Strategies
1. Create strategy class in appropriate `crypto-ai-backend/strategies/{category}/` folder
2. Implement required methods: `fetch_data()`, `generate_signals()`, `calculate_pnl()`
3. Add strategy endpoints to `app.py` (around line 800+ where other strategies are defined)
4. Update frontend `StrategiesScreen.js` to include new strategy in selection
5. Test with `python simulate_trades.py` for backtesting

### Adding New API Endpoints
1. Add route handler in `app.py` following `/api/{resource}` pattern
2. Use `@app.route()` decorator with appropriate HTTP methods
3. Include error handling with try/catch and fallback mock data
4. Update frontend service in `exchangeService.js` or `aiService.js`
5. Test endpoint connectivity using HomeScreen debug button

### Frontend Screen Development
1. Create new screen in `src/screens/` following existing naming convention
2. Import required components from `src/components/`
3. Use `exchangeService` for API calls with async/await pattern
4. Add screen to navigation in `AppNavigator.js`
5. Handle loading states and error boundaries

### Debugging Common Issues
- **API Connection**: Use HomeScreen debug button to test backend connectivity
- **Exchange Errors**: Check Flask console for CCXT error details
- **Chart Issues**: Verify matplotlib backend is 'Agg' for threading
- **Credential Issues**: Clear AsyncStorage if authentication fails
- **Network Issues**: Update IP address in `exchangeService.js:8` for different networks

### Data Persistence Patterns
- **Backend**: JSON files in `crypto-ai-backend/` root (e.g., `simulated_trades.json`)
- **Frontend**: AsyncStorage for user preferences and credentials
- **Charts**: Base64 encoded images generated by matplotlib and returned via API
- **Strategy Results**: Stored in JSON format with FIFO trade matching