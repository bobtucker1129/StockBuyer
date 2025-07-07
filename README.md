# Stock Market Trading Agent

An intelligent algorithmic trading system that researches the stock market and executes daily trades to generate wealth.

## 🎯 Features

- **Research-Driven Trading**: Analyzes financial news, social sentiment, and technical indicators
- **Dual Mode Operation**: Virtual (paper trading) vs Real (live trading)
- **Configurable Capital**: Control your trading account size
- **Daily Trading Cycles**: Automated research and execution
- **Learning System**: Adapts strategies based on performance
- **Web Dashboard**: Real-time monitoring and control

## 🚀 Quick Start

### Virtual Mode (No Accounts Needed)

1. **Install dependencies**:
```bash
pip install -r requirements.txt
```

2. **Configure settings** in `config.yaml`:
```yaml
trading:
  mode: "virtual"  # Paper trading - no real money
  account_balance: 10000.0  # Your virtual account size
```

3. **Run the trading agent**:
```bash
python main.py
```

4. **Access the web dashboard** at `http://localhost:8000`

### Real Mode (Requires Trading Account)

1. **Create a trading account**:
   - **Alpaca Markets** (Recommended): [alpaca.markets](https://alpaca.markets)
   - **TD Ameritrade**: [tdameritrade.com](https://www.tdameritrade.com)
   - **Interactive Brokers**: [interactivebrokers.com](https://www.interactivebrokers.com)

2. **Get API credentials** from your chosen platform

3. **Configure API keys** in `config.yaml`:
```yaml
trading:
  mode: "real"
  account_balance: 10000.0
  alpaca_api_key: "your_api_key_here"
  alpaca_secret_key: "your_secret_key_here"
```

4. **Run the agent**:
```bash
python main.py
```

## 📊 Trading Modes

### Virtual Mode (Paper Trading)
- ✅ **No accounts needed**
- ✅ **No real money risked**
- ✅ **Perfect for testing strategies**
- ✅ **Immediate setup**
- ✅ **Learn without risk**

### Real Mode (Live Trading)
- 💰 **Real money, real trades**
- 📈 **Real profits and losses**
- 🔐 **Requires trading platform account**
- ⚠️ **Risk of financial loss**
- 🎯 **For experienced traders**

## 🏦 Recommended Trading Platforms

### Alpaca Markets (Best for Beginners)
- **Free account** with $0 minimum
- **Commission-free trading**
- **Excellent API** for algorithmic trading
- **Paper trading** available for testing
- **Easy setup** process

**Setup Steps**:
1. Visit [alpaca.markets](https://alpaca.markets)
2. Click "Get Started"
3. Create free account
4. Go to "Paper Trading" section
5. Generate API keys
6. Add keys to `config.yaml`

### TD Ameritrade
- More established platform
- Good API for automated trading
- Requires more verification
- Commission-free trading

### Interactive Brokers
- Professional-grade platform
- Lower fees for high volume
- More complex setup
- Advanced features

## ⚙️ Configuration

Edit `config.yaml` to customize your trading:

```yaml
trading:
  mode: "virtual"  # or "real"
  account_balance: 10000.0  # Your account size
  risk_percentage: 2.0  # Risk per trade (%)
  max_position_size: 5.0  # Max position size (%)
  stop_loss_percentage: 3.0  # Stop loss (%)
  take_profit_percentage: 6.0  # Take profit (%)

research:
  news_sources:
    - "https://finance.yahoo.com/news"
    - "https://www.marketwatch.com/news"
  sentiment_threshold: 0.3
  trend_analysis_window: 14
```

## 🛡️ Safety Features

- **Virtual mode by default** - no risk of losing money
- **Risk management** - stop-loss and position sizing
- **Daily limits** - prevents over-trading
- **Portfolio monitoring** - real-time P&L tracking
- **Web dashboard** - full control and visibility

## 📈 How It Works

1. **Research Phase**: Scrapes news, analyzes sentiment, identifies trends
2. **Analysis Phase**: Calculates risk scores and potential returns
3. **Trading Phase**: Executes trades based on research
4. **Monitoring Phase**: Tracks positions and manages risk
5. **Learning Phase**: Adapts strategies based on performance

## 🎮 Getting Started (Recommended)

**Start with Virtual Mode**:
1. Install the system
2. Run in virtual mode for 1-2 weeks
3. Monitor performance and learn
4. Only switch to real mode when comfortable

**Virtual Mode Benefits**:
- Learn how the system works
- Test different strategies
- Build confidence
- No financial risk

## ⚠️ Important Disclaimers

- **Not financial advice** - This is educational software
- **Past performance doesn't guarantee future results**
- **Real trading involves risk of loss**
- **Start with virtual mode** to learn
- **Only trade with money you can afford to lose**

## 🆘 Need Help?

1. **Start with virtual mode** - no risk, full learning
2. **Monitor the web dashboard** - see how it works
3. **Read the logs** - understand the decision process
4. **Adjust settings** - customize to your risk tolerance

## 📁 Project Structure

```
stock_market_agent/
├── main.py                 # Main entry point
├── config.yaml            # Configuration file
├── requirements.txt       # Python dependencies
├── src/
│   ├── trading_agent.py   # Main trading logic
│   ├── research_engine.py # News and analysis
│   ├── trading_engine.py  # Order execution
│   ├── portfolio_manager.py # Position tracking
│   ├── web_dashboard.py   # Web interface
│   └── models/            # Data models
└── README.md             # This file
```

---

**Ready to start? Begin with virtual mode and learn how the system works!** 🚀 