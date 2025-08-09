import discord
from discord.ext import commands
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import asyncio
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
import logging
from typing import Optional, Dict, Any
import pytz
import os
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Set up matplotlib for better-looking plots
plt.style.use('dark_background')
sns.set_palette("husl")

class StockData:
    """Handle stock data fetching and analysis"""
    
    @staticmethod
    def get_stock_info(symbol: str) -> Optional[Dict[str, Any]]:
        """Get comprehensive stock information"""
        try:
            ticker = yf.Ticker(symbol.upper())
            
            # Get basic info
            info = ticker.info
            
            # Get recent data
            hist_1d = ticker.history(period='1d', interval='1m')
            hist_5d = ticker.history(period='5d', interval='15m')
            
            if hist_1d.empty and hist_5d.empty:
                return None
            
            # Use the most recent data available
            current_data = hist_1d if not hist_1d.empty else hist_5d
            
            # Get current price (last available)
            current_price = current_data['Close'].iloc[-1] if not current_data.empty else info.get('currentPrice', 0)
            
            # Get previous close for change calculation
            previous_close = info.get('previousClose', current_price)
            
            # Calculate change
            price_change = current_price - previous_close
            percent_change = (price_change / previous_close) * 100 if previous_close != 0 else 0
            
            # Determine market session
            market_session = StockData.get_market_session()
            
            # Get additional stats
            day_high = current_data['High'].max() if not current_data.empty else info.get('dayHigh', current_price)
            day_low = current_data['Low'].min() if not current_data.empty else info.get('dayLow', current_price)
            volume = current_data['Volume'].sum() if not current_data.empty else info.get('volume', 0)
            
            return {
                'symbol': symbol.upper(),
                'company_name': info.get('longName', symbol.upper()),
                'current_price': current_price,
                'previous_close': previous_close,
                'price_change': price_change,
                'percent_change': percent_change,
                'day_high': day_high,
                'day_low': day_low,
                'volume': volume,
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'market_session': market_session,
                'last_update': datetime.now(),
                'hist_data': current_data
            }
            
        except Exception as e:
            logging.error(f"Error fetching data for {symbol}: {e}")
            return None
    
    @staticmethod
    def get_market_session() -> str:
        """Determine current market session"""
        now = datetime.now(pytz.timezone('US/Eastern'))
        current_time = now.time()
        weekday = now.weekday()
        
        # Weekend
        if weekday >= 5:  # Saturday = 5, Sunday = 6
            return "Weekend (Market Closed)"
        
        # Market hours (9:30 AM - 4:00 PM ET)
        market_open = datetime.strptime("09:30", "%H:%M").time()
        market_close = datetime.strptime("16:00", "%H:%M").time()
        
        # Pre-market (4:00 AM - 9:30 AM ET)
        premarket_start = datetime.strptime("04:00", "%H:%M").time()
        
        # After-hours (4:00 PM - 8:00 PM ET)
        afterhours_end = datetime.strptime("20:00", "%H:%M").time()
        
        if market_open <= current_time <= market_close:
            return "Regular Market Hours"
        elif premarket_start <= current_time < market_open:
            return "Pre-Market"
        elif market_close < current_time <= afterhours_end:
            return "After-Hours"
        else:
            return "Market Closed"
    
    @staticmethod
    def create_price_chart(symbol: str, period: str = '1d') -> Optional[io.BytesIO]:
        """Create a price chart for the stock"""
        try:
            ticker = yf.Ticker(symbol)
            
            # Determine interval based on period
            if period == '1d':
                data = ticker.history(period='1d', interval='5m')
                title_period = "Today"
            elif period == '5d':
                data = ticker.history(period='5d', interval='15m')
                title_period = "5 Days"
            elif period == '1mo':
                data = ticker.history(period='1mo', interval='1h')
                title_period = "1 Month"
            else:
                data = ticker.history(period='3mo', interval='1d')
                title_period = "3 Months"
            
            if data.empty:
                return None
            
            # Create the plot
            fig, ax = plt.subplots(figsize=(12, 8))
            fig.patch.set_facecolor('#2f3136')
            ax.set_facecolor('#36393f')
            
            # Plot the price line
            ax.plot(data.index, data['Close'], color='#00d4aa', linewidth=2, label='Price')
            
            # Fill area under the curve
            ax.fill_between(data.index, data['Close'], alpha=0.3, color='#00d4aa')
            
            # Add volume subplot
            ax2 = ax.twinx()
            ax2.bar(data.index, data['Volume'], alpha=0.3, color='#7289da', width=0.0008)
            ax2.set_ylabel('Volume', color='#7289da')
            ax2.tick_params(axis='y', labelcolor='#7289da')
            
            # Formatting
            ax.set_title(f'{symbol.upper()} - {title_period}', fontsize=16, color='white', fontweight='bold')
            ax.set_xlabel('Time', color='white')
            ax.set_ylabel('Price ($)', color='white')
            
            # Format x-axis
            if period == '1d':
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                ax.xaxis.set_major_locator(mdates.HourLocator(interval=2))
            else:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            
            # Rotate x-axis labels
            plt.xticks(rotation=45)
            
            # Grid
            ax.grid(True, alpha=0.3, color='white')
            
            # Price info
            current_price = data['Close'].iloc[-1]
            price_change = current_price - data['Close'].iloc[0]
            percent_change = (price_change / data['Close'].iloc[0]) * 100
            
            # Add price info text
            color = '#00ff41' if price_change >= 0 else '#ff4757'
            change_symbol = '+' if price_change >= 0 else ''
            
            info_text = f'${current_price:.2f} ({change_symbol}${price_change:.2f}, {change_symbol}{percent_change:.2f}%)'
            ax.text(0.02, 0.98, info_text, transform=ax.transAxes, fontsize=12, 
                   color=color, fontweight='bold', verticalalignment='top',
                   bbox=dict(boxstyle='round', facecolor='black', alpha=0.8))
            
            # Tight layout
            plt.tight_layout()
            
            # Save to BytesIO
            buffer = io.BytesIO()
            plt.savefig(buffer, format='PNG', facecolor='#2f3136', dpi=150, bbox_inches='tight')
            buffer.seek(0)
            plt.close()
            
            return buffer
            
        except Exception as e:
            logging.error(f"Error creating chart for {symbol}: {e}")
            return None

class StockBot(commands.Bot):
    """Discord bot for stock data"""
    
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
    
    async def on_ready(self):
        print(f'{self.user} has connected to Discord!')
        
        # Sync slash commands
        try:
            synced = await self.tree.sync()
            print(f'Synced {len(synced)} command(s)')
        except Exception as e:
            print(f'Failed to sync commands: {e}')
    
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            return
        print(f'Error: {error}')

# Create bot instance
bot = StockBot()

@bot.tree.command(name="price", description="Get current stock price and basic info")
async def price_command(interaction: discord.Interaction, symbol: str):
    """Get current stock price"""
    await interaction.response.defer()
    
    try:
        stock_data = StockData.get_stock_info(symbol)
        
        if not stock_data:
            await interaction.followup.send(f"❌ Could not find data for symbol: {symbol.upper()}")
            return
        
        # Create embed
        embed = discord.Embed(
            title=f"📈 {stock_data['symbol']} - {stock_data['company_name']}",
            color=0x00ff41 if stock_data['price_change'] >= 0 else 0xff4757,
            timestamp=datetime.now()
        )
        
        # Price info
        change_emoji = "📈" if stock_data['price_change'] >= 0 else "📉"
        change_symbol = "+" if stock_data['price_change'] >= 0 else ""
        
        embed.add_field(
            name=f"{change_emoji} Current Price",
            value=f"**${stock_data['current_price']:.2f}**\n{change_symbol}${stock_data['price_change']:.2f} ({change_symbol}{stock_data['percent_change']:.2f}%)",
            inline=True
        )
        
        embed.add_field(
            name="📊 Day Range",
            value=f"**High:** ${stock_data['day_high']:.2f}\n**Low:** ${stock_data['day_low']:.2f}",
            inline=True
        )
        
        embed.add_field(
            name="📋 Previous Close",
            value=f"${stock_data['previous_close']:.2f}",
            inline=True
        )
        
        # Volume and market cap
        if stock_data['volume']:
            volume_formatted = f"{stock_data['volume']:,}"
            embed.add_field(name="📊 Volume", value=volume_formatted, inline=True)
        
        if stock_data['market_cap']:
            market_cap_b = stock_data['market_cap'] / 1e9
            embed.add_field(name="💰 Market Cap", value=f"${market_cap_b:.2f}B", inline=True)
        
        if stock_data['pe_ratio']:
            embed.add_field(name="📈 P/E Ratio", value=f"{stock_data['pe_ratio']:.2f}", inline=True)
        
        # Market session
        embed.add_field(
            name="🕐 Market Status",
            value=stock_data['market_session'],
            inline=False
        )
        
        embed.set_footer(text="Data provided by Yahoo Finance")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error fetching data for {symbol.upper()}: {str(e)}")

@bot.tree.command(name="chart", description="Get a price chart for a stock")
async def chart_command(interaction: discord.Interaction, symbol: str, period: str = "1d"):
    """Get stock chart"""
    await interaction.response.defer()
    
    valid_periods = ["1d", "5d", "1mo", "3mo"]
    if period not in valid_periods:
        await interaction.followup.send(f"❌ Invalid period. Use one of: {', '.join(valid_periods)}")
        return
    
    try:
        # Create chart
        chart_buffer = StockData.create_price_chart(symbol, period)
        
        if not chart_buffer:
            await interaction.followup.send(f"❌ Could not create chart for {symbol.upper()}")
            return
        
        # Create file
        file = discord.File(chart_buffer, filename=f"{symbol.upper()}_{period}_chart.png")
        
        # Get basic stock info for embed
        stock_data = StockData.get_stock_info(symbol)
        
        if stock_data:
            embed = discord.Embed(
                title=f"📊 {symbol.upper()} Chart ({period.upper()})",
                color=0x00d4aa,
                timestamp=datetime.now()
            )
            embed.set_image(url=f"attachment://{symbol.upper()}_{period}_chart.png")
            embed.set_footer(text=f"Market Status: {stock_data['market_session']}")
        else:
            embed = discord.Embed(
                title=f"📊 {symbol.upper()} Chart ({period.upper()})",
                color=0x00d4aa,
                timestamp=datetime.now()
            )
            embed.set_image(url=f"attachment://{symbol.upper()}_{period}_chart.png")
        
        await interaction.followup.send(embed=embed, file=file)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error creating chart for {symbol.upper()}: {str(e)}")

@bot.tree.command(name="compare", description="Compare multiple stocks")
async def compare_command(interaction: discord.Interaction, symbols: str):
    """Compare multiple stocks (comma-separated)"""
    await interaction.response.defer()
    
    try:
        symbol_list = [s.strip().upper() for s in symbols.split(',')]
        
        if len(symbol_list) > 5:
            await interaction.followup.send("❌ Maximum 5 stocks can be compared at once.")
            return
        
        embed = discord.Embed(
            title=f"📊 Stock Comparison: {', '.join(symbol_list)}",
            color=0x7289da,
            timestamp=datetime.now()
        )
        
        for symbol in symbol_list:
            stock_data = StockData.get_stock_info(symbol)
            
            if stock_data:
                change_emoji = "📈" if stock_data['price_change'] >= 0 else "📉"
                change_symbol = "+" if stock_data['price_change'] >= 0 else ""
                
                value_text = (
                    f"**${stock_data['current_price']:.2f}**\n"
                    f"{change_symbol}${stock_data['price_change']:.2f} "
                    f"({change_symbol}{stock_data['percent_change']:.2f}%)"
                )
                
                embed.add_field(
                    name=f"{change_emoji} {symbol}",
                    value=value_text,
                    inline=True
                )
            else:
                embed.add_field(
                    name=f"❌ {symbol}",
                    value="No data available",
                    inline=True
                )
        
        market_session = StockData.get_market_session()
        embed.set_footer(text=f"Market Status: {market_session}")
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Error comparing stocks: {str(e)}")

@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    """Show help information"""
    embed = discord.Embed(
        title="🤖 Stock Bot Commands",
        description="Get real-time stock data and charts!",
        color=0x00d4aa
    )
    
    embed.add_field(
        name="/price <symbol>",
        value="Get current price and basic info for a stock\nExample: `/price AAPL`",
        inline=False
    )
    
    embed.add_field(
        name="/chart <symbol> [period]",
        value="Get a price chart for a stock\nPeriods: `1d`, `5d`, `1mo`, `3mo`\nExample: `/chart TSLA 5d`",
        inline=False
    )
    
    embed.add_field(
        name="/compare <symbols>",
        value="Compare multiple stocks (comma-separated)\nExample: `/compare AAPL,GOOGL,MSFT`",
        inline=False
    )
    
    embed.add_field(
        name="📊 Features",
        value=(
            "• Works 24/7 (shows pre/post market data)\n"
            "• Real-time price updates\n"
            "• Beautiful charts and graphs\n"
            "• Market session indicators\n"
            "• Compare up to 5 stocks at once"
        ),
        inline=False
    )
    
    embed.set_footer(text="Data provided by Yahoo Finance • Bot made with ❤️")
    
    await interaction.response.send_message(embed=embed)

# Run the bot
if __name__ == "__main__":
    # Configuration
    BOT_TOKEN = os.getenv("DISCORD_TOKEN")
    
    if not BOT_TOKEN:
        print("❌ Please set your bot token before running!")
    else:
        try:
            bot.run(BOT_TOKEN)
        except discord.LoginFailure:
            print("❌ Invalid bot token! Please check your token and try again.")
        except Exception as e:
            print(f"❌ Error starting bot: {e}")