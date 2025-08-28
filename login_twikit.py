from twikit import Client

# ✅ Step 1: Create Twikit client
client = Client(language="en-US")

# ✅ Step 2: Load cookies
client.load_cookies("cookies.json")
print("🍪 Cookies loaded successfully")
print("✅ Logged in using cookies (confirmed)")






