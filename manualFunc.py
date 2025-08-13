# # TESTING FUNCTIONS
# def test_email_notification(email_config):
#     print("Testing email notification...")
#     notification_service = NotificationService(email_config=email_config)
#     notification_service.send_email(
#         "🧪 ORBS Bot Test Email", 
#         "If you received this email, your email notifications are working correctly!, now dont be a silly billy and pay up this bot was no short feat 🤥😡"
#     )
#     print("Test email sent!")

# def test_discord_notification(discord_webhook, discord_role_id = None):
#     print("Testing Discord notification...")
#     notification_service = NotificationService(discord_webhook=discord_webhook, discord_role_id=discord_role_id)
#     notification_service.send_discord_notification(
#         "🧪 **ORBS Bot Test** - Rise and shine Lets make some money!", discord_role_id
#     )
#     print("Test Discord message sent!")

# def test_data_fetching(symbols):
#     print("Testing data fetching...")
#     bot = ORBSTradingBot(symbols=symbols)
    
#     for symbol in symbols:
#         print(f"\nTesting {symbol}:")
#         data = bot.get_stock_data(symbol, period='1d', interval='1m')
#         if not data.empty:
#             current_price = data['Close'].iloc[-1]
#             print(f"  ✅ Data received - Current price: ${current_price:.2f}")
#             print(f"  📊 Data points: {len(data)}")
#         else:
#             print(f"  ❌ No data received")

# def manual_test_orbs_calculation(symbol="SPY"):
#     print(f"\nTesting ORBS calculation for {symbol}...")
    
#     bot = ORBSTradingBot(symbols=[symbol])
#     orbs_level = bot.calculate_orbs_levels(symbol)
    
#     if orbs_level:
#         print(f"✅ ORBS levels calculated:")
#         print(f"  High: ${orbs_level.orb_high:.2f}")
#         print(f"  Low: ${orbs_level.orb_low:.2f}")
#         print(f"  Width: ${orbs_level.orb_width:.2f}")
#         print(f"  Period: {orbs_level.orb_start_time.strftime('%H:%M')} - {orbs_level.orb_end_time.strftime('%H:%M')}")
#     else:
#         print("❌ Could not calculate ORBS levels")