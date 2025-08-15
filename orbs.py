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
from typing import Optional, Tuple, List, Callable
import threading
import os
from dotenv import load_dotenv
import tkinter as tk
from tkinter import scrolledtext, messagebox
import queue

load_dotenv()

class TradingApp:

    def __init__(self, bot):
        self.bot = bot
        self.bot_thread = None
        self.is_running = False
        
        
        self.message_queue = queue.Queue()
        

        self.window = tk.Tk()
        self.window.title('ORBS Trading Bot')
        self.window.geometry('800x600')
        self.window.configure(bg='#34495e')
        
        main_frame = tk.Frame(self.window, bg='#34495e', padx=10, pady=10)
        main_frame.pack(expand=True, fill='both')

        title_label = tk.Label(main_frame, text='ORBS Trading Bot', font=('Helvetica', 16, 'bold'), fg='#ecf0f1', bg='#2c3e50', relief='groove', bd=2, pady=5)
        title_label.pack(fill='x', pady=(0, 10))

        self.output_text = scrolledtext.ScrolledText(main_frame, wrap='word', bg='#2c3e50', fg='#ecf0f1', font=('Consolas', 10), relief='sunken', bd=2)
        self.output_text.pack(expand=True, fill='both', pady=(0, 10))
        self.output_text.config(state=tk.DISABLED) 

        button_frame = tk.Frame(main_frame, bg='#34495e')
        button_frame.pack(fill='x', pady=(0, 10))

        self.start_button = tk.Button(button_frame, text='Start Bot', command=self.start_bot, font=('Helvetica', 12, 'bold'), bg='#27ae60', fg='#ecf0f1', activebackground='#2ecc71', relief='raised', padx=10, pady=5)
        self.start_button.pack(side='left', expand=True, padx=5)
        
        self.stop_button = tk.Button(button_frame, text='Stop Bot', command=self.stop_bot, font=('Helvetica', 12, 'bold'), bg='#c0392b', fg='#ecf0f1', activebackground='#e74c3c', relief='raised', state=tk.DISABLED, padx=10, pady=5)
        self.stop_button.pack(side='left', expand=True, padx=5)
        
        self.exit_button = tk.Button(button_frame, text='Exit', command=self.exit_app, font=('Helvetica', 12, 'bold'), bg='#95a5a6', fg='#ecf0f1', activebackground='#bdc3c7', relief='raised', padx=10, pady=5)
        self.exit_button.pack(side='left', expand=True, padx=5)

        self.window.protocol("WM_DELETE_WINDOW", self.exit_app)

        self.bot.set_logging_callback(self.log_message)

        self.window.after(100, self.check_queue)
    
    def check_queue(self):
        while not self.message_queue.empty():
            message = self.message_queue.get()
            self.log_to_gui(message)
        self.window.after(100, self.check_queue)

    def log_message(self, message):
        self.message_queue.put(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {message}")
        
    def log_to_gui(self, message):
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, message + "\n")
        self.output_text.see(tk.END) 
        self.output_text.config(state=tk.DISABLED)

    def start_bot(self):
        if not self.is_running:
            self.is_running = True
            self.bot.should_run = True
            self.bot_thread = threading.Thread(target=self.bot.run, daemon=True)
            self.bot_thread.start()
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
            self.log_message("Bot started.")

    def stop_bot(self):
        if self.is_running:
            self.is_running = False
            self.bot.should_run = False
            if self.bot_thread and self.bot_thread.is_alive():
                self.log_message("Stopping bot... This may take a moment.")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.log_message("Bot stopped.")

    def exit_app(self):
        if self.is_running:
            self.stop_bot()
        self.window.destroy()

    def run(self):
        self.window.mainloop()

@dataclass
class ORBSLevel:
    symbol: str
    orb_high: float
    orb_low: float
    orb_width: float
    orb_start_time: datetime
    orb_end_time: datetime

class NotificationService:
    def __init__(self, email_config: Optional[dict] = None, discord_webhook: Optional[str] = None, discord_role_id: Optional[str] = None, log_callback: Optional[Callable] = None):
        self.email_config = email_config
        self.discord_webhook = discord_webhook
        self.discord_role_id = discord_role_id
        self.log_callback = log_callback or (lambda msg: None) # Default to a no-op function

    def set_logging_callback(self, callback: Callable):
        self.log_callback = callback
    
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
            
            self.log_callback(f"Email sent: {subject}")
        except Exception as e:
            self.log_callback(f"Failed to send email: {e}")
            
    def send_discord_notification(self, message: str, ping_role: Optional[str] = None):
        if not self.discord_webhook:
            return
        
        try:
            if ping_role:
                message = f"<@&{ping_role}> {message}"
                
            data = {"content": message}
            response = requests.post(self.discord_webhook, json=data)
            if response.status_code == 204:
                self.log_callback("Discord notification sent")
            else:
                self.log_callback(f"Discord notification failed: {response.status_code}")
        except Exception as e:
            self.log_callback(f"Failed to send Discord notification: {e}")
            
    def notify(self, title: str, message:str):
        gui_message = f"\n📈 {title}\n📊 {message}\n{'-' * 50}"
        self.log_callback(gui_message)
        
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
        notification_service: Optional["NotificationService"] = None,
        log_callback: Optional[Callable] = None
        ):
        
        self.symbols = symbols
        self.orb_minutes = orb_minutes
        self.execution_timeframes = execution_timeframes
        self.notification_service = notification_service or NotificationService()
        self.set_logging_callback(log_callback)
        
        self.orbs_levels = {}
        self.active_signals = set()
        self.market_open_hours = 9
        self.market_open_minute = 30
        self.market_close_hour = 16

        self.last_status_update_time = None
        self.STATUS_UPDATE_INTERVAL_MINUTES = 10

        self.pre_market_notified_today = False
        self.market_open_notified_today = False

        self.should_run = False
        
    def set_logging_callback(self, callback: Optional[Callable]):
        """Sets the function to call for logging messages."""
        self.log_callback = callback or (lambda msg: None)

    def is_market_hours(self) -> bool:
        """Checks if the current time is within regular market hours."""
        now = datetime.now()
        current_time = now.time()
        
        if now.weekday() >= 5: 
            return False
        
        market_open = now.replace(
            hour=self.market_open_hours, 
            minute=self.market_open_minute, 
            second=0, 
            microsecond=0
        ).time()
        
        market_close = now.replace(
            hour=self.market_close_hour, 
            minute=0, 
            second=0, 
            microsecond=0
        ).time()
        
        return market_open <= current_time <= market_close
    
    def get_stock_data(self, symbol: str, period: str = '1d', interval: str = "1m") -> pd.DataFrame:
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period, interval=interval)
            
            if data.empty:
                self.log_callback(f"No data received for {symbol}")
                return pd.DataFrame()
            
            if isinstance(data.index, pd.DatetimeIndex):
                if data.index.tz is None:
                    data.index = data.index.tz_localize("US/Eastern")
                else:
                    data.index = data.index.tz_convert("US/Eastern")
                
            return data
        except Exception as e:
            self.log_callback(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
        
    def calculate_orbs_levels(self, symbol: str) -> Optional[ORBSLevel]:
        data = self.get_stock_data(symbol, period='1d', interval='1m')
        
        if data.empty:
            return None
        
        data_index = data.index
        
        if not isinstance(data_index, pd.DatetimeIndex) or data_index.tz is None:
            self.log_callback(f"Invalid index type or timezone for {symbol}. Cannot calculate ORBS levels.")
            return None
        
        now = datetime.now().replace(tzinfo=data_index.tz)
        
        market_open_today = now.replace(
            hour=self.market_open_hours, 
            minute=self.market_open_minute, 
            second=0,
            microsecond=0
        )
        
        orb_end_time = market_open_today + timedelta(minutes=self.orb_minutes)
        
        orb_data = data[(data.index >= market_open_today) & (data.index <= orb_end_time)]
        
        if orb_data.empty:
            self.log_callback(f"No data available for ORB period for {symbol}")
            return None

        if 'High' not in orb_data.columns or 'Low' not in orb_data.columns:
            self.log_callback(f"Missing required columns in ORB data for {symbol}")
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
        
        self.log_callback(f"ORBS levels calculated for {symbol}: High={orb_high:.2f}, Low={orb_low:.2f}, Width={orb_width:.2f}")
        
        return orbs_level
    
    def check_breakout(self, symbol: str, timeframe: str) -> Optional[str]:
        """Checks if a breakout has occurred for a given symbol and timeframe."""
        if symbol not in self.orbs_levels:
            self.log_callback(f"No ORBS levels found for {symbol}")
            return None
        
        orbs = self.orbs_levels[symbol]
        
        data = self.get_stock_data(symbol, period='1d', interval=timeframe)
        
        if data.empty or len(data) < 2:
            return None
        
        latest_candle = data.iloc[-2]
        current_candle = data.iloc[-1]

        if isinstance(data.index, pd.DatetimeIndex) and len(data.index) > 0:
            current_time = data.index[-1]

            if isinstance(current_time, pd.Timestamp):
                current_time = current_time.to_pydatetime()
        else:
            self.log_callback(f"Invalid timestamp data for {symbol}")
            return None
        
        if current_time <= orbs.orb_end_time:
            return None

        signal_id = f"{symbol}_{timeframe}_{current_time.strftime('%H%M')}"
        
        if signal_id in self.active_signals:
            return None
        
        breakout_type = None

        if latest_candle['Close'] > orbs.orb_high:
            breakout_type = "BULLISH"
            self.active_signals.add(signal_id)

        elif latest_candle['Close'] < orbs.orb_low:
            breakout_type = "BEARISH"
            self.active_signals.add(signal_id)
        
        return breakout_type
    
    def generate_trade_signal(self, symbol: str, breakout_type: str, timeframe: str):
        """Generates a detailed trade signal and sends a notification."""
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
            entry_reason = f"Price broke above ORB high (${orbs.orb_high:.2f})"
            
        elif breakout_type == "BEARISH":
            signal_type = "PUT"
            direction = "🔴 SHORT"
            entry_reason = f"Price broke below ORB low (${orbs.orb_low:.2f})"

        orb_start_str = orbs.orb_start_time.strftime('%H:%M') if orbs.orb_start_time else "N/A"
        orb_end_str = orbs.orb_end_time.strftime('%H:%M') if orbs.orb_end_time else "N/A"
        
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
• ORB Period: {orb_start_str} - {orb_end_str}

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
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """Gets the current price of a stock."""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period='1d', interval='1m')
            if not data.empty:
                return float(data['Close'].iloc[-1])
        except Exception as e:
            self.log_callback(f"Error getting current price for {symbol}: {e}")
        return None
    
    def update_orbs_levels(self):
        """Calculates ORBS levels for all tracked symbols."""
        for symbol in self.symbols:
            orbs_level = self.calculate_orbs_levels(symbol)
            if orbs_level:
                self.orbs_levels[symbol] = orbs_level
    
    def scan_orbs_levels(self):
        """Scans for breakout signals on all symbols and timeframes."""
        signals = []
        
        for symbol in self.symbols:
            if symbol not in self.orbs_levels:
                continue
            
            for timeframe in self.execution_timeframes:
                breakout_type = self.check_breakout(symbol, timeframe)
                
                if breakout_type:
                    signal = self.generate_trade_signal(symbol, breakout_type, timeframe)
                    if signal:  
                        signals.append(signal)

                    time.sleep(1)
                    
        return signals
    
    def reset_daily_data(self):
        """Resets the bot's state at the start of a new day."""
        self.orbs_levels.clear()
        self.active_signals.clear()
        self.pre_market_notified_today = False
        self.market_open_notified_today = False
        self.log_callback("Daily data reset completed")
        
    def run(self):
        """Main loop for the trading bot."""
        self.log_callback("ORBS Trading Bot started")
        self.log_callback(f"Watching symbols: {', '.join(self.symbols)}")
        self.log_callback(f"Execution timeframes: {', '.join(self.execution_timeframes)}")
        
        last_update_day = None
        orbs_calculated_today = False
        
        try:
            while self.should_run:
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
                        
                    self.log_callback("Market closed. Waiting...")
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
                    self.log_callback("Calculating ORBS levels...")
                    self.update_orbs_levels()
                    orbs_calculated_today = True
                    self.last_status_update_time = current_time 
                    
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
                                self.log_callback(status_msg)
                                
                    signals = self.scan_orbs_levels()
                    
                    if signals:
                        self.log_callback(f"Generated {len(signals)} signals")
                
                time.sleep(10)
                
        except Exception as e:
            self.log_callback(f"Unexpected error: {e}")
            self.should_run = False 
            
if __name__ == "__main__":
    
    SYMBOLS = ["SPY"] 

    email_config = {
        'smtp_server': os.getenv("EMAIL_SMTP_SERVER"),
        'smtp_port': int(os.getenv("EMAIL_SMTP_PORT", 587)),
        'from_email': os.getenv("EMAIL_FROM"),
        'password': os.getenv("EMAIL_PASSWORD"),
        'to_email': os.getenv("EMAIL_TO"),
    }
    
    if not all(email_config.values()):
        email_config = None
        
    discord_webhook = os.getenv("DISCORD_WEBHOOK")
    discord_role_id = os.getenv("DISCORD_ROLE_ID")
    
    notifier = NotificationService(
        email_config=email_config, 
        discord_webhook=discord_webhook, 
        discord_role_id=discord_role_id
    )
    
    bot_logic = ORBSTradingBot(
        symbols=SYMBOLS,
        orb_minutes=30,
        execution_timeframes=['1m', '2m', '5m'],
        notification_service=notifier
    )

    app = TradingApp(bot_logic)
    app.run()