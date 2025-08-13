import pandas as pd
from pandas import Timestamp
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import time
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from dataclasses import dataclass
from typing import Optional, Tuple, List
import logging
from typing import cast
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

@dataclass
class ORBSLevel:
    symbol: str
    orb_high: float
    orb_low: float
    orb_width: float
    orb_start_time: datetime
    orb_end_time: datetime
    
class NotificationService:
    def __init__(self, email_config: Optional[dict] = None, discord_webhook: Optional[str] = None, discord_role_id: Optional[str] = None):
        self.email_config = email_config
        self.discord_webhook = discord_webhook
        self.discord_role_id = discord_role_id
    def send_email(self, subject: str, body: str):
        if not self.email_config:
            return
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from_email']
            msg['To'] = self.email_config['to_email']
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(self.email_config['smtp_server'], self.email_config['smtp_port'])
            server.starttls()
            server.login(self.email_config['from_email'], self.email_config['password'])
            server.send_message(msg)
            server.quit()
            
            logging.info(f"Email sent: {subject}")
        except Exception as e:
            logging.error(f"Failed tro send email: {e}")
            
    def send_discord_notification(self, message: str, ping_role: Optional[str] = None):
        if not self.discord_webhook:
            return
        
        try:
            
            if ping_role:
                message = f"<@&{ping_role}> {message}"
                
            data = {"content": message}
            response = requests.post(self.discord_webhook, json=data)
            if response.status_code == 204:
                logging.info("Discord notification sent")
            else:
                logging.error(f"Discord notification failed: {response.status_code}")
        except Exception as e:
            logging.error(f"Failed to send Discord notification: {e}")
            
    def notify(self, title: str, message:str):
        print(f"\n 📈 {title}")
        print(f"\n 📊 {message}")
        print("-" * 50)
        
        if self.email_config:
            self.send_email(title, message)
            
        if self.discord_webhook:
            self.send_discord_notification(f"**{title}**\n{message}", self.discord_role_id)
            
class ORBSTradingBot:
    
    def __init__(
        self, 
        symbols: List[str],
        orb_minutes: int = 15,
        execution_timeframes: List[str] = ["1m", "2m", "5m"],
        notification_service: Optional["NotificationService"] = None
        ):
        
        self.symbols = symbols
        self.orb_minutes = orb_minutes
        self.execution_timeframes = execution_timeframes
        self.notification_service = notification_service or NotificationService()
        
        self.orbs_levels = {}
        self.active_signals = set()
        self.market_open_hours = 9
        self.market_open_minute = 30
        self.market_close_hour = 16
        self.last_status_update_time = None
        self.STATUS_UPDATE_INTERVAL_MINUTES = 5
        self.pre_market_notified_today = False
        self.market_open_notified_today = False
        
    def is_market_hours(self) -> bool:
        now = datetime.now()
        current_time = now.time()
        
        if now.weekday() >= 5: 
            return False
        
        market_open = datetime.now().replace(
            hour=self.market_open_hours, 
            minute=self.market_open_minute, 
            second=0, 
            microsecond=0
        ).time()
        
        market_close = datetime.now().replace(
            hour=self.market_close_hour, 
            minute=0, 
            second=0, 
            microsecond=0
        ).time()
        
        return market_open <= current_time <= market_close
    
    def get_stock_data(self, symbol: str, period: str = '1d', interval: str = "1m") -> pd.DataFrame:
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period = period, interval= interval)
            
            if data.empty:
                logging.error(f"No data recieved for {symbol}")
                return pd.DataFrame()
            
            data.index = cast(pd.DatetimeIndex, data.index)
            
            if data.index.tz is None:
                data.index = data.index.tz_localize("US/Eastern")
            else:
                data.index = data.index.tz_convert("US/Eastern")
                
            return data
        except Exception as e:
            logging.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
        
    def calculate_orbs_levels(self, symbol: str) -> Optional[ORBSLevel]:
        
        data = self.get_stock_data(symbol, period='1d', interval='1m')
        
        if data.empty:
            return None
        
        data_index = cast(pd.DatetimeIndex, data.index)
        now = datetime.now().replace(tzinfo=data_index.tz)
        
        market_open_today = now.replace(hour=self.market_open_hours, minute=self.market_open_minute, second=0,microsecond=0)

        orb_end_time = market_open_today + timedelta(minutes=self.orb_minutes)
        
        orb_data = data[(data.index >= market_open_today) & (data.index <= orb_end_time)]
        
        if orb_data.empty:
            logging.warning(f"No data available for ORB period for {symbol}")
            return None
        
        orb_high = orb_data['High'].max()
        orb_low = orb_data['Low'].min()
        orb_width = orb_high - orb_low
        
        orbs_level = ORBSLevel(
            symbol=symbol,
            orb_high=orb_high,
            orb_low=orb_low,
            orb_width=orb_width,
            orb_start_time=market_open_today,
            orb_end_time=orb_end_time
        )
        
        logging.info(f"ORBS levels calculated for {symbol}: High={orb_high:.2f}, Low={orb_low:.2f}, Width={orb_width:.2f}")
        
        return orbs_level
    
    def check_breakout(self, symbol: str, timeframe: str) -> Optional[str]:
        
        if symbol not in self.orbs_levels:
            logging.warning(f"No ORBS levels found for {symbol}")
            return None
        
        orbs = self.orbs_levels[symbol]
        
        data = self.get_stock_data(symbol, period='1d', interval=timeframe)
        
        if data.empty or len(data) < 2:
            return None
        
        latest_candle = data.iloc[-2] 
        current_candle = data.iloc[-1] 
        current_time = cast(Timestamp, current_candle.name)
        
        if current_time <= orbs.orb_end_time:
            return None
        
        
        signal_id = f"{symbol}_{timeframe}_{current_time.strftime('%H%M')}"
        
        if signal_id in self.active_signals:
            return None
        
        breakout_type = None
        
        # Bullish breakout (close above ORB high)
        if latest_candle['Close'] > orbs.orb_high:
            breakout_type = "BULLISH"
            self.active_signals.add(signal_id)
            
        # Bearish breakout (close below ORB low)
        elif latest_candle['Close'] < orbs.orb_low:
            breakout_type = "BEARISH"
            self.active_signals.add(signal_id)
        
        return breakout_type
    
    def generate_trade_signal(self, symbol:str , breakout_type: str, timeframe: str):
        orbs = self.orbs_levels[symbol]
        current_price = self.get_current_price(symbol)
        
        if current_price is None:
            return None
        
        signal_type = "UNKNOWN"
        direction = "❓UNKNOWN"
        entry_reason = "Unknown breakout type"
        
        if breakout_type == "BULLISH":
            signal_type = "CALL"
            direction = "🟢 LONG"
            entry_reason = f"Price broke above ORB high ({orbs.orb_high:.2f})"
            
        elif breakout_type == "BEARISH":
            signal_type = "PUT"
            direction = "🔴 SHORT"
            entry_reason = f"Price broke below ORB low ({orbs.orb_low:.2f})"
        
        message = f"""
        🎯 ORBS BREAKOUT SIGNAL
        ━━━━━━━━━━━━━━━━━━━━
        📈 Symbol: {symbol}
        🎨 Signal: {signal_type} Options
        📊 Direction: {direction}
        ⏰ Timeframe: {timeframe}
        💰 Current Price: ${current_price:.2f}

        📋 ORB Details:
        • ORB High: ${orbs.orb_high:.2f}
        • ORB Low: ${orbs.orb_low:.2f}
        • ORB Width: ${orbs.orb_width:.2f}
        • ORB Period: {orbs.orb_start_time.strftime('%H:%M')} - {orbs.orb_end_time.strftime('%H:%M')}

        🔍 Entry Reason:
        {entry_reason}

        🎯 Suggested Action:
        Buy {signal_type} options on Robinhood

        ⏱️ Signal Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        """
        
        title = f"🚨 {symbol} {signal_type} SIGNAL - ORBS Breakout"
        
        self.notification_service.notify(title, message.strip())
        
        return {
            'symbol': symbol,
            'signal_type': signal_type,
            'breakout_type': breakout_type,
            'current_price': current_price,
            'orb_high': orbs.orb_high,
            'orb_low': orbs.orb_low,
            'timeframe': timeframe,
            'timestamp': datetime.now()
        }
    
    def get_current_price(self, symbol: str) -> float:
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                return data['Close'].iloc[-1]
        except:
            pass
        return 0.0
    
    def update_orbs_levels(self):
        for symbol in self.symbols:
            orbs_level = self.calculate_orbs_levels(symbol)
            if orbs_level:
                self.orbs_levels[symbol] = orbs_level
    
    def scan_orbs_levels(self):
        
        signals = []
        
        for symbol in self.symbols:
            if symbol not in self.orbs_levels:
                continue
            
            for timeframe in self.execution_timeframes:
                breakout_type = self.check_breakout(symbol, timeframe)
                
                if breakout_type:
                    signal = self.generate_trade_signal(symbol, breakout_type, timeframe)
                    signals.append(signal)
                    
                    # Avoid spam
                    time.sleep(1)
                    
        return signals
    
    def reset_daily_data(self):
        self.orbs_levels.clear()
        self.active_signals.clear()
        logging.info("Daily data reset completed")
        
    def run(self):
        logging.info("ORBS Trading Bot started")
        logging.info(f"Watching symbols: {', '.join(self.symbols)}")
        logging.info(f"Execution timeframes: {', '.join(self.execution_timeframes)}")
        
        last_update_day = None
        orbs_calculated_today = False
        
        try:
            while True:
                current_time = datetime.now()
                current_day = current_time.date()
                
                if last_update_day and current_day != last_update_day:
                    self.reset_daily_data()
                    orbs_calculated_today = False
                    
                last_update_day = current_day
                
                if not self.is_market_hours():
                    if (
                        current_time.hour == 9
                        and current_time.minute == 0
                        and not self.pre_market_notified_today
                    ):
                        pre_market_message = f"🔔 Market opens in 30 minutes! Time to get ready to watch {', '.join(self.symbols)}."
                        self.notification_service.notify("⏰ Pre-Market Alert", pre_market_message)
                        self.pre_market_notified_today = True
                        
                    logging.info("Market closed. Waiting...")
                    time.sleep(300)
                    continue
                
                if (
                current_time.hour == 9
                and current_time.minute == 30
                and not self.market_open_notified_today
                ):
                    market_open_message = f"🟢 The market is officially open! The ORBS bot is now waiting for the 30-minute range to form for {', '.join(self.symbols)}."
                    self.notification_service.notify("🎉 Market Open!", market_open_message)
                    self.market_open_notified_today = True

                market_open_time = current_time.replace(
                    hour=self.market_open_hours,
                    minute=self.market_open_minute,
                    second=0,
                    microsecond=0
                )
                orb_end_time = market_open_time + timedelta(minutes=self.orb_minutes)
                
                if current_time >= orb_end_time and not orbs_calculated_today:
                    logging.info("Calculating ORBS level...")
                    self.update_orbs_levels()
                    orbs_calculated_today = True
                    
                    if self.orbs_levels:
                        levels_msg = "📊 Today's ORBS Levels:\n"
                        for symbol, orbs in self.orbs_levels.items():
                            levels_msg += f"\n{symbol}:"
                            levels_msg += f"\n  • High: ${orbs.orb_high:.2f}"
                            levels_msg += f"\n  • Low: ${orbs.orb_low:.2f}"
                            levels_msg += f"\n  • Width: ${orbs.orb_width:.2f}"
                            
                        self.notification_service.notify("🎯 ORBS Levels Calculated", levels_msg)
                        
                if orbs_calculated_today and self.orbs_levels:
                    if (
                        self.last_status_update_time is None
                        or (current_time - self.last_status_update_time).total_seconds() > self.STATUS_UPDATE_INTERVAL_MINUTES * 60
                    ):
                        self.last_status_update_time = current_time
                        
                        for symbol, orbs in self.orbs_levels.items():
                            current_price = self.get_current_price(symbol)
                            if current_price:
                                status_msg = f"🔍 Current status for {symbol}:\n"
                                status_msg += f"  • Current Price: ${current_price:.2f}\n"
                                status_msg += f"  • ORB High: ${orbs.orb_high:.2f}\n"
                                status_msg += f"  • ORB Low: ${orbs.orb_low:.2f}"
                                logging.info(status_msg)
                                
                    signals = self.scan_orbs_levels()
                    
                    if signals:
                        logging.info(f"Generated {len(signals)} signals")
                
                time.sleep(10) # Using a hardcoded interval to prevent the user's previous `check_interval` error
                
        except KeyboardInterrupt:
            logging.info("Bot stopped by silly man")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise

# def test_discord_notification(discord_webhook, discord_role_id = None):
#     print("Testing Discord notification...")
#     notification_service = NotificationService(discord_webhook=discord_webhook, discord_role_id=discord_role_id)
#     notification_service.send_discord_notification(
#         "🧪 **ORBS Bot Test** - Rise and shine Lets make some money!", discord_role_id
#     )
#     print("Test Discord message sent!")  
if __name__ == "__main__":
    
    SYMBOLS = ["SPY"] 
    
    email_config = {
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'from_email': 'orbstradingbot@gmail.com',
        'password': 'avzb mtfv voer psts',
        'to_email': ['dihyah.adib@gmail.com', 'Muhammad242m@gmail.com', 'ayat25541234@gmail.com']
    }
    
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    discord_role_id = os.getenv("DISCORD_ROLE_ID")
    # Initialize notification service
    notification_service = NotificationService(
        email_config=email_config,
        discord_webhook=discord_webhook
    )
    # test_discord_notification(discord_webhook, discord_role_id)
    bot = ORBSTradingBot(
        symbols=SYMBOLS,
        orb_minutes=30,  # 15-minute opening range
        execution_timeframes=['1m', '2m', '5m'],
        notification_service=notification_service
    )
    bot.run()

