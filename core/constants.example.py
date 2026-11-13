# Copy this file to core/constants.py and fill in real values.
# core/constants.py is gitignored — never commit secrets.

# Telegram
TELEGRAM_TOKEN = "123456:your-bot-token"
TELEGRAM_CHAT_ID = 0  # bot chat that receives the upload first
PRIVATE_CHANNEL_ID = 0  # archive channel the bot message is forwarded to
PARSE_MODE = "Markdown"

# MongoDB
MONGODB_URI = "mongodb+srv://user:password@cluster.example.mongodb.net/?retryWrites=true&w=majority"

# X (Twitter) login for fetch/fetch_likes.py: copy these two cookies from x.com
# while logged in (DevTools → Application → Cookies → https://x.com).
# If X rotates ct0, the fetcher writes the new value back here automatically.
X_AUTH_TOKEN = "your-auth_token-cookie"
X_CT0 = "your-ct0-cookie"
# Optional overrides — leave empty unless the fetcher asks for them.
X_USER_ID = ""  # the number after "u%3D" in your twid cookie
X_LIKES_QUERY_ID = ""
