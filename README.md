# ORBS Trading Bot & Discord Stock Bot 🤖
This repository contains the source code for a suite of bots designed to assist with stock market analysis and trading. The project includes two main components: a Discord bot that provides real-time stock data and charts, and an underlying bot that implements the Opening Range Breakout System (ORBS) trading method.

## 📈 The Discord Stock Bot
The Discord bot provides a powerful and easy-to-use way to access stock information directly from your Discord server. It's built to give you real-time data and visually appealing charts to help you make informed decisions.

## ✨ Features
Real-time Stock Data: Get current prices, market cap, P/E ratios, and more.

Beautiful Charts: Generate professional-looking price charts for various time periods (1d, 5d, 1mo, 3mo).

Multi-Stock Comparison: Easily compare key metrics for up to 5 stocks at once.

Market Session Status: Stay informed about whether the market is in regular hours, pre-market, or after-hours.

User-Friendly Commands: Interact with the bot using simple slash commands.

## 🤖 How to Use
The bot uses slash commands for all its functions. Here are some examples:

Command	Description	Example
<table>
  <thead>
    <tr>
      <th>Command</th>
      <th>Description</th>
      <th>Example</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><code>/price &lt;symbol&gt;</code></td>
      <td>Get the current price and key data for a stock.</td>
      <td><code>/price AAPL</code></td>
    </tr>
    <tr>
      <td><code>/chart &lt;symbol&gt; [period]</code></td>
      <td>Generate a price chart for a stock. [period] can be 1d, 5d, 1mo, or 3mo.</td>
      <td><code>/chart TSLA 5d</code></td>
    </tr>
    <tr>
      <td><code>/compare &lt;symbol1&gt;,&lt;symbol2&gt;,...</code></td>
      <td>Compare prices and changes for multiple stocks.</td>
      <td><code>/compare GOOGL,MSFT,AMZN</code></td>
    </tr>
    <tr>
      <td><code>/help</code></td>
      <td>Display a list of all available commands.</td>
      <td><code>/help</code></td>
    </tr>
  </tbody>
</table>

# 🎯 The ORBS Trading Method Bot
The core of the project is the ORBS (Opening Range Breakout System) trading bot. This component is designed to autonomously identify and alert you to potential trading opportunities based on the ORBS strategy.

## ✨ Features
Opening Range Identification: Automatically calculates the high and low of a stock within the first 30 minutes of the trading day.

Breakout Detection: Monitors prices for breakouts above the high or below the low of the opening range.

Customizable Alerts: Can be configured to send alerts to a Discord channel, email, or other services when a breakout is detected.

Risk Management: Includes logic to help manage risk, such as setting stop-loss and take-profit levels.

# ⚠️ INSTALLATION PROCESS IS A WORK IN PROGRESS DO NOT FOLLOW YET ⚠️
# ⚙️ Installation and Setup
Prerequisites
- Python 3.8+
- A Discord Bot Token (from the Discord Developer Portal)
## Local Setup

### 1. Clone the repository:
```bash
git clone https://github.com/your-username/your-repo-name.git
cd your-repo-name
```
### 2. Create a virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```
### 3. Install dependencies:
```bash
pip install -r requirements.txt
```
*adding rest later...*
