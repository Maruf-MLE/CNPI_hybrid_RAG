# Quick Fix: Use existing messenger_bot credentials temporarily for Answer Bot

# OPTION 1: Same Facebook Page (Quick Test)
# Copy these values to ANSWER_BOT_* in Render Environment Variables:

ANSWER_BOT_VERIFY_TOKEN=cnpi_bot_Xk29fLq7
ANSWER_BOT_APP_SECRET=c305f2981fc7d328db653e91d93ba5fe
ANSWER_BOT_PAGE_ACCESS_TOKEN=EAAWc3pczaFIBSgpwIVgq2zCmSZCfSqyRJjSYnDiRCcOP55bcxTv2mKSZB7EZBZCp1dciZBsU70hQslPdrcAOtBYCz4cUxRS5GmrcpYvcMB7bxcBwlSC9sSZAGTIDE66B939FMKry2wJjtr7wF7dvZA3ZBwh9qPRNOkozuZCqbDXa6EGZCPRhUWhAZCQBycMllZAWZBpHSDmTBUw3dKwZDZD
ANSWER_BOT_ALLOWED_PSIDS=
RAG_API_URL=https://cnpi-hybrid-rag-1.onrender.com/api/chat/

# IMPORTANT: Same page will ONLY work with ONE webhook URL at a time!
# Either use /webhook/ (messenger_bot) OR /answer-webhook/ (answer_bot), not both.

# =========================================================================
# OPTION 2: Create New Facebook Page (Recommended for Production)
# =========================================================================

Steps:
1. Create new Facebook Page for Answer Bot
2. Get new credentials from CNGPIchat app
3. Configure webhook for /answer-webhook/

# =========================================================================
# Current Webhook Configuration Check
# =========================================================================

# In CNGPIchat App Dashboard → Messenger → Settings → Webhooks:
# Which URL is configured?
# A) https://cnpi-hybrid-rag-1.onrender.com/webhook/  (messenger_bot)
# B) https://cnpi-hybrid-rag-1.onrender.com/answer-webhook/  (answer_bot)

# Log shows: Answer Bot Webhook GET verification successful
# This means /answer-webhook/ is configured ✅

# But you need to:
# 1. Add ANSWER_BOT credentials to Render Environment Variables
# 2. Subscribe the PAGE to /answer-webhook/ webhook
