"""
Web Dashboard - Real-time monitoring and control interface
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List
import json
import sqlite3
import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
import uvicorn
import pandas as pd

logger = logging.getLogger(__name__)


class WebDashboard:
    """Web dashboard for monitoring and controlling the trading agent"""

    def __init__(self, trading_agent):
        self.trading_agent = trading_agent
        self.app = FastAPI()
        self.active_connections: List[WebSocket] = []
        self.setup_routes()

    def setup_routes(self):
        """Setup API routes"""

        @self.app.get("/")
        async def get_dashboard():
            return HTMLResponse(self.get_dashboard_html())

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            await websocket.accept()
            self.active_connections.append(websocket)
            logger.info("connection open")

            try:
                while True:
                    # Send status updates every 5 seconds
                    status = self.trading_agent.get_status()
                    await websocket.send_text(json.dumps(status))
                    await asyncio.sleep(5)
            except WebSocketDisconnect:
                self.active_connections.remove(websocket)
                logger.info("connection closed")

        @self.app.get("/api/status")
        async def get_status():
            return self.trading_agent.get_status()

        @self.app.get("/api/strategies")
        async def get_strategies():
            """Get detailed information about all strategies"""
            try:
                strategies_info = {}

                # Check for failed strategies
                if (
                    hasattr(self.trading_agent, "strategies_failed")
                    and self.trading_agent.strategies_failed
                ):
                    logger.critical(
                        "❌ No strategies loaded in agent. Returning error to dashboard."
                    )
                    return {
                        "error": "No strategies loaded! Check your config.yaml under 'strategies:' and for errors in the logs."
                    }

                # Debug logging
                logger.info(
                    f"Number of strategies: {len(self.trading_agent.strategies)}"
                )
                logger.info(
                    f"Strategy keys: {list(self.trading_agent.strategies.keys())}"
                )
                logger.info(f"Trading agent type: {type(self.trading_agent)}")
                logger.info(f"Strategies type: {type(self.trading_agent.strategies)}")

                # Check if we have any strategies
                if not self.trading_agent.strategies:
                    logger.warning("No strategies available in trading agent")
                    return {
                        "error": "No strategies available! Check your config.yaml under 'strategies:' and for errors in the logs."
                    }

                for (
                    strategy_name,
                    strategy_data,
                ) in self.trading_agent.strategies.items():
                    logger.info(f"Processing strategy: {strategy_name}")
                    logger.info(f"Strategy data keys: {list(strategy_data.keys())}")
                    try:
                        portfolio_manager = strategy_data["portfolio_manager"]
                        portfolio_summary = portfolio_manager.get_portfolio_summary()

                        strategies_info[strategy_name] = {
                            "name": (
                                strategy_data["config"].trading.name
                                if hasattr(strategy_data["config"].trading, "name")
                                else strategy_name
                            ),
                            "description": (
                                strategy_data["config"].trading.description
                                if hasattr(
                                    strategy_data["config"].trading, "description"
                                )
                                else ""
                            ),
                            "is_active": strategy_data["is_active"],
                            "account_balance": portfolio_summary["account_balance"],
                            "total_pnl": portfolio_summary["total_pnl"],
                            "daily_pnl": portfolio_summary["daily_pnl"],
                            "positions_count": portfolio_summary["positions_count"],
                            "trades_today": portfolio_summary["trades_today"],
                            "opportunities_count": len(
                                strategy_data["daily_opportunities"]
                            ),
                            "risk_percentage": strategy_data[
                                "config"
                            ].trading.risk_percentage,
                            "max_position_size": strategy_data[
                                "config"
                            ].trading.max_position_size,
                            "max_daily_trades": strategy_data[
                                "config"
                            ].system.max_daily_trades,
                            "max_daily_loss": strategy_data[
                                "config"
                            ].system.max_daily_loss,
                        }
                        logger.info(f"Successfully processed strategy: {strategy_name}")
                    except Exception as e:
                        logger.error(f"Error processing strategy {strategy_name}: {e}")
                        strategies_info[strategy_name] = {"error": str(e)}

                logger.info(f"Returning {len(strategies_info)} strategies")
                return strategies_info
            except Exception as e:
                logger.error(f"Error getting strategies: {e}")
                return {"error": str(e)}

        @self.app.get("/api/trades/{strategy_name}")
        async def get_trades(strategy_name: str):
            """Get recent trades for a specific strategy"""
            try:
                # Use main database instead of strategy-specific database
                db_path = self.trading_agent.config.system.database_url.replace(
                    "sqlite:///", ""
                )
                if not db_path:
                    db_path = "trading_data.db"

                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT symbol, shares, price, total, type, timestamp, opportunity_score, risk_score
                    FROM trades 
                    WHERE strategy = ?
                    ORDER BY timestamp DESC 
                    LIMIT 20
                    """,
                    (strategy_name,),
                )

                trades = []
                for row in cursor.fetchall():
                    trades.append(
                        {
                            "symbol": row[0],
                            "shares": row[1],
                            "price": row[2],
                            "total": row[3],
                            "type": row[4],
                            "timestamp": row[5],
                            "opportunity_score": row[6],
                            "risk_score": row[7],
                        }
                    )

                conn.close()
                return trades

            except Exception as e:
                logger.error(f"Error getting trades for {strategy_name}: {e}")
                return []

        @self.app.get("/api/positions/{strategy_name}")
        async def get_positions(strategy_name: str):
            """Get current positions for a specific strategy"""
            try:
                conn = sqlite3.connect(f"trading_data_{strategy_name}.db")
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT symbol, shares, avg_price, current_price, total_value, pnl 
                    FROM positions 
                    WHERE shares > 0
                    ORDER BY total_value DESC
                    """
                )

                positions = []
                for row in cursor.fetchall():
                    positions.append(
                        {
                            "symbol": row[0],
                            "shares": row[1],
                            "avg_price": row[2],
                            "current_price": row[3],
                            "total_value": row[4],
                            "pnl": row[5],
                        }
                    )

                conn.close()
                return positions

            except Exception as e:
                logger.error(f"Error getting positions for {strategy_name}: {e}")
                return []

        @self.app.get("/api/opportunities")
        async def get_opportunities():
            """Get current trading opportunities and recent research data"""
            try:
                opportunities = []

                # Check if we have any strategies
                if not self.trading_agent.strategies:
                    return {"error": "No strategies available"}

                # Get opportunities from the first strategy (shared research)
                first_strategy = list(self.trading_agent.strategies.values())[0]

                # First, try to get current opportunities
                if first_strategy["daily_opportunities"]:
                    for opp in first_strategy["daily_opportunities"][:10]:
                        # Handle NaN values for JSON serialization
                        opportunities.append(
                            {
                                "symbol": opp.symbol,
                                "current_price": (
                                    float(opp.current_price)
                                    if not pd.isna(opp.current_price)
                                    else 0.0
                                ),
                                "score": (
                                    float(opp.score) if not pd.isna(opp.score) else 0.0
                                ),
                                "risk_score": (
                                    float(opp.risk_score)
                                    if not pd.isna(opp.risk_score)
                                    else 0.0
                                ),
                                "potential_return": (
                                    float(opp.potential_return)
                                    if not pd.isna(opp.potential_return)
                                    else 0.0
                                ),
                                "technical_score": (
                                    float(opp.technical_score)
                                    if not pd.isna(opp.technical_score)
                                    else 0.0
                                ),
                                "sentiment_score": (
                                    float(opp.sentiment_score)
                                    if not pd.isna(opp.sentiment_score)
                                    else 0.0
                                ),
                                "news_score": (
                                    float(opp.news_score)
                                    if not pd.isna(opp.news_score)
                                    else 0.0
                                ),
                                "type": "opportunity",
                            }
                        )

                # If no current opportunities, get recent trades from all strategies
                if not opportunities:
                    # Use main database instead of strategy-specific databases
                    db_path = self.trading_agent.config.system.database_url.replace(
                        "sqlite:///", ""
                    )
                    if not db_path:
                        db_path = "trading_data.db"

                    try:
                        conn = sqlite3.connect(db_path)
                        cursor = conn.cursor()

                        cursor.execute(
                            """
                            SELECT symbol, shares, price, total, type, timestamp, opportunity_score, risk_score, strategy
                            FROM trades 
                            ORDER BY timestamp DESC 
                            LIMIT 15
                            """
                        )

                        for row in cursor.fetchall():
                            opportunities.append(
                                {
                                    "symbol": row[0],
                                    "shares": row[1],
                                    "price": row[2],
                                    "total": row[3],
                                    "type": row[4],
                                    "timestamp": row[5],
                                    "score": row[6] if row[6] else 0.0,
                                    "risk_score": row[7] if row[7] else 0.0,
                                    "strategy": row[8],
                                    "type": "recent_trade",
                                }
                            )

                        conn.close()
                    except Exception as e:
                        logger.error(f"Error getting trades from main database: {e}")
                        # Add placeholder opportunities for each strategy
                        for strategy_name in self.trading_agent.strategies.keys():
                            opportunities.append(
                                {
                                    "symbol": "N/A",
                                    "shares": 0,
                                    "price": 0.0,
                                    "total": 0.0,
                                    "type": "No trades yet",
                                    "timestamp": "New deployment",
                                    "score": 0.0,
                                    "risk_score": 0.0,
                                    "strategy": strategy_name,
                                    "type": "info",
                                    "message": f"{strategy_name} strategy is running but no trades yet. Database will be created on first trade.",
                                }
                            )

                # If still no data, return a message
                if not opportunities:
                    return [
                        {
                            "symbol": "No opportunities",
                            "message": "No current opportunities available. Trading cycle completed. Check back after the next research cycle.",
                            "type": "info",
                        }
                    ]

                return opportunities
            except Exception as e:
                logger.error(f"Error getting opportunities: {e}")
                return {"error": str(e)}

        @self.app.post("/api/set-balance/{strategy_name}")
        async def set_strategy_balance(strategy_name: str, request: dict):
            """Set a new account balance for a specific strategy"""
            try:
                new_balance = request.get("balance", 10000.0)

                # Update the config file
                with open("config.yaml", "r") as f:
                    config = yaml.safe_load(f)

                if "strategies" in config and strategy_name in config["strategies"]:
                    config["strategies"][strategy_name]["account_balance"] = float(
                        new_balance
                    )

                    with open("config.yaml", "w") as f:
                        yaml.dump(config, f, default_flow_style=False)

                    # Update the strategy's portfolio manager
                    strategy_data = self.trading_agent.strategies[strategy_name]
                    strategy_data["portfolio_manager"].account_balance = float(
                        new_balance
                    )

                    return {
                        "message": f"Balance updated for {strategy_name}",
                        "new_balance": float(new_balance),
                    }
                else:
                    return {"error": f"Strategy {strategy_name} not found"}

            except Exception as e:
                logger.error(f"Error setting balance for {strategy_name}: {e}")
                return {"error": str(e)}

        @self.app.post("/api/reset/{strategy_name}")
        async def reset_strategy(strategy_name: str):
            """Reset a specific strategy's portfolio"""
            try:
                import os

                # Delete the strategy's database file
                db_file = f"trading_data_{strategy_name}.db"
                if os.path.exists(db_file):
                    os.remove(db_file)

                # Reset the strategy's portfolio manager
                strategy_data = self.trading_agent.strategies[strategy_name]
                config = strategy_data["config"]

                strategy_data["portfolio_manager"].account_balance = (
                    config.trading.account_balance
                )
                strategy_data["portfolio_manager"].positions = {}
                strategy_data["portfolio_manager"].total_pnl = 0.0
                strategy_data["portfolio_manager"].daily_pnl = 0.0
                strategy_data["portfolio_manager"].trades_today = 0

                return {
                    "message": f"Strategy {strategy_name} reset successfully",
                    "new_balance": config.trading.account_balance,
                }

            except Exception as e:
                logger.error(f"Error resetting {strategy_name}: {e}")
                return {"error": str(e)}

        @self.app.get("/api/version")
        async def get_version():
            """Get the current version of the application"""
            return {"version": "2.0.0", "deployment": "railway-fixed"}

    def get_dashboard_html(self) -> str:
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Multi-Strategy Stock Market Trading Agent</title>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body { font-family: Arial, sans-serif; background: #f8f9fa; color: #222; margin: 0; padding: 0; }
                #container { max-width: 1400px; margin: 40px auto; background: #fff; border-radius: 8px; box-shadow: 0 2px 8px #0001; padding: 32px; }
                h1 { color: #2c3e50; text-align: center; margin-bottom: 32px; }
                .strategies-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 24px; margin-bottom: 32px; }
                .strategy-card { background: #fff; border: 2px solid #e9ecef; border-radius: 8px; padding: 20px; box-shadow: 0 2px 4px #0001; }
                .strategy-card.turbo { border-color: #dc3545; }
                .strategy-card.moderate { border-color: #28a745; }
                .strategy-card.risky { border-color: #ffc107; }
                .strategy-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
                .strategy-name { font-size: 1.2em; font-weight: bold; }
                .strategy-status { padding: 4px 8px; border-radius: 4px; font-size: 0.8em; }
                .status-active { background: #d4edda; color: #155724; }
                .status-inactive { background: #f8d7da; color: #721c24; }
                .metrics { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; margin-bottom: 16px; }
                .metric { background: #f8f9fa; padding: 8px; border-radius: 4px; }
                .metric-label { font-size: 0.8em; color: #666; }
                .metric-value { font-size: 1.1em; font-weight: bold; }
                .positive { color: #28a745; }
                .negative { color: #dc3545; }
                .controls { display: flex; gap: 8px; margin-top: 16px; }
                .btn { padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; font-size: 0.9em; }
                .btn-primary { background: #007bff; color: white; }
                .btn-success { background: #28a745; color: white; }
                .btn-danger { background: #dc3545; color: white; }
                .btn-warning { background: #ffc107; color: #212529; }
                .opportunities { margin-top: 24px; }
                .opportunities h3 { color: #2c3e50; margin-bottom: 16px; }
                .opportunity-list { background: #f8f9fa; padding: 16px; border-radius: 4px; }
                .opportunity-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #dee2e6; }
                .opportunity-item:last-child { border-bottom: none; }
                .no-opportunities { text-align: center; color: #666; font-style: italic; }
                .error-message { color: #dc3545; background: #f8d7da; border: 1px solid #dc3545; padding: 16px; border-radius: 8px; margin-bottom: 24px; text-align: center; font-weight: bold; }
                .links { margin-top: 24px; text-align: center; }
                .links a { display: inline-block; margin: 8px 16px 8px 0; padding: 8px 16px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }
                .links a:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div id="container">
                <h1>🚀 Multi-Strategy Stock Market Trading Agent</h1>
                <div id="error-message" class="error-message" style="display:none;"></div>
                <div id="strategies" class="strategies-grid">
                    <!-- Strategy cards will be populated here -->
                </div>
                
                <div class="opportunities">
                    <h3>🎯 Current Trading Opportunities</h3>
                    <div id="opportunities" class="opportunity-list">
                        Loading opportunities...
                    </div>
                </div>
                
                <div class="links">
                    <a href="/api/opportunities" target="_blank">🎯 View All Opportunities</a>
                    <a href="/api/strategies" target="_blank">📊 View Strategy Details</a>
                </div>
            </div>

            <script>
                let ws = null;
                
                function connectWebSocket() {
                    ws = new WebSocket('ws://localhost:8000/ws');
                    
                    ws.onopen = function() {
                        console.log('WebSocket connected');
                    };
                    
                    ws.onmessage = function(event) {
                        const data = JSON.parse(event.data);
                        updateDashboard(data);
                    };
                    
                    ws.onclose = function() {
                        console.log('WebSocket disconnected, reconnecting...');
                        setTimeout(connectWebSocket, 5000);
                    };
                }
                
                async function fetchStrategies() {
                    try {
                        const response = await fetch('/api/strategies');
                        const data = await response.json();
                        if (data.error) {
                            document.getElementById('error-message').innerText = data.error;
                            document.getElementById('error-message').style.display = 'block';
                            document.getElementById('strategies').style.display = 'none';
                        } else {
                            document.getElementById('error-message').style.display = 'none';
                            document.getElementById('strategies').style.display = 'grid';
                        }
                    } catch (e) {
                        document.getElementById('error-message').innerText = 'Error loading strategies: ' + e;
                        document.getElementById('error-message').style.display = 'block';
                        document.getElementById('strategies').style.display = 'none';
                    }
                }
                
                function updateDashboard(data) {
                    updateStrategies(data.strategies);
                    updateOpportunities(data.strategies);
                }
                
                function updateStrategies(strategies) {
                    const container = document.getElementById('strategies');
                    container.innerHTML = '';
                    
                    for (const [strategyName, strategy] of Object.entries(strategies)) {
                        const card = createStrategyCard(strategyName, strategy);
                        container.appendChild(card);
                    }
                }
                
                function createStrategyCard(strategyName, strategy) {
                    const card = document.createElement('div');
                    card.className = `strategy-card ${strategyName}`;
                    
                    const isActive = strategy.is_active;
                    const statusClass = isActive ? 'status-active' : 'status-inactive';
                    const statusText = isActive ? 'ACTIVE' : 'INACTIVE';
                    
                    const pnlClass = strategy.daily_pnl >= 0 ? 'positive' : 'negative';
                    const pnlSign = strategy.daily_pnl >= 0 ? '+' : '';
                    
                    card.innerHTML = `
                        <div class="strategy-header">
                            <div class="strategy-name">${strategy.name || strategyName.toUpperCase()}</div>
                            <div class="strategy-status ${statusClass}">${statusText}</div>
                        </div>
                        
                        <div class="metrics">
                            <div class="metric">
                                <div class="metric-label">Account Balance</div>
                                <div class="metric-value">$${strategy.account_balance.toFixed(2)}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Daily P&L</div>
                                <div class="metric-value ${pnlClass}">${pnlSign}$${strategy.daily_pnl.toFixed(2)}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Total P&L</div>
                                <div class="metric-value ${pnlClass}">${pnlSign}$${strategy.total_pnl.toFixed(2)}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Positions</div>
                                <div class="metric-value">${strategy.positions_count}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Trades Today</div>
                                <div class="metric-value">${strategy.trades_today}</div>
                            </div>
                            <div class="metric">
                                <div class="metric-label">Opportunities</div>
                                <div class="metric-value">${strategy.opportunities_count}</div>
                            </div>
                        </div>
                        
                        <div class="controls">
                            <button class="btn btn-primary" onclick="setBalance('${strategyName}')">💰 Set Balance</button>
                            <button class="btn btn-danger" onclick="resetStrategy('${strategyName}')">🔄 Reset</button>
                            <button class="btn btn-success" onclick="viewTrades('${strategyName}')">📊 Trades</button>
                            <button class="btn btn-warning" onclick="viewPositions('${strategyName}')">📈 Positions</button>
                        </div>
                    `;
                    
                    return card;
                }
                
                function updateOpportunities(strategies) {
                    const container = document.getElementById('opportunities');
                    
                    // Fetch opportunities directly from the API
                    fetch('/api/opportunities')
                        .then(response => response.json())
                        .then(data => {
                            if (data.error) {
                                container.innerHTML = `<div class="error-message">Error: ${data.error}</div>`;
                                return;
                            }
                            
                            if (data.length === 0) {
                                container.innerHTML = '<div class="no-opportunities">No opportunities or recent trades available.</div>';
                                return;
                            }
                            
                            // Check if it's an info message
                            if (data.length === 1 && data[0].type === 'info') {
                                container.innerHTML = `<div class="no-opportunities">${data[0].message}</div>`;
                                return;
                            }
                            
                            // Display opportunities or recent trades
                            let html = '';
                            data.forEach(item => {
                                if (item.type === 'opportunity') {
                                    html += `
                                        <div class="opportunity-item">
                                            <span><strong>${item.symbol}</strong> - $${item.current_price.toFixed(2)}</span>
                                            <span>Score: ${item.score.toFixed(3)} | Risk: ${item.risk_score.toFixed(3)}</span>
                                        </div>
                                    `;
                                } else if (item.type === 'recent_trade') {
                                    html += `
                                        <div class="opportunity-item">
                                            <span><strong>${item.symbol}</strong> - ${item.shares} shares @ $${item.price.toFixed(2)}</span>
                                            <span>${item.strategy} | ${item.timestamp}</span>
                                        </div>
                                    `;
                                }
                            });
                            
                            if (html === '') {
                                html = '<div class="no-opportunities">No opportunities or recent trades available.</div>';
                            }
                            
                            container.innerHTML = html;
                        })
                        .catch(error => {
                            console.error('Error fetching opportunities:', error);
                            container.innerHTML = '<div class="no-opportunities">Error loading opportunities. Please try again.</div>';
                        });
                }
                
                async function setBalance(strategyName) {
                    const newBalance = prompt(`Enter new balance for ${strategyName}:`, "10000");
                    if (newBalance && !isNaN(newBalance)) {
                        try {
                            const response = await fetch(`/api/set-balance/${strategyName}`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ balance: parseFloat(newBalance) })
                            });
                            const result = await response.json();
                            alert(`Balance updated for ${strategyName}: $${result.new_balance.toFixed(2)}`);
                        } catch (error) {
                            alert('Error setting balance: ' + error);
                        }
                    }
                }
                
                async function resetStrategy(strategyName) {
                    if (confirm(`Are you sure you want to reset ${strategyName}? This will delete all positions and trades.`)) {
                        try {
                            const response = await fetch(`/api/reset/${strategyName}`, { method: 'POST' });
                            const result = await response.json();
                            alert(`${strategyName} reset successfully! New balance: $${result.new_balance.toFixed(2)}`);
                            location.reload();
                        } catch (error) {
                            alert('Error resetting strategy: ' + error);
                        }
                    }
                }
                
                function viewTrades(strategyName) {
                    window.open(`/api/trades/${strategyName}`, '_blank');
                }
                
                function viewPositions(strategyName) {
                    window.open(`/api/positions/${strategyName}`, '_blank');
                }
                
                // Initialize
                connectWebSocket();
                fetchStrategies();
            </script>
        </body>
        </html>
        """

    async def start(self):
        """Start the web dashboard"""
        try:
            logger.info(f"Starting web dashboard...")
            logger.info(f"Trading agent config: {self.trading_agent.config}")
            logger.info(
                f"Dashboard host: {self.trading_agent.config.system.dashboard_host}"
            )
            logger.info(
                f"Dashboard port: {self.trading_agent.config.system.dashboard_port}"
            )

            config = uvicorn.Config(
                self.app,
                host=self.trading_agent.config.system.dashboard_host,
                port=self.trading_agent.config.system.dashboard_port,
                log_level="info",
            )
            server = uvicorn.Server(config)
            await server.serve()
        except Exception as e:
            logger.error(f"Error starting web dashboard: {e}")
            raise

    async def shutdown(self):
        """Shutdown the web dashboard"""
        logger.info("🛑 Web dashboard shutdown complete")
