# Telegram-Squid-game-bot-Kaustav-Ray

# .env
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
PORT=8080
MONGODB_URI_1=mongodb://localhost:27017/
MONGODB_URI_2=mongodb+srv://user:pass@cluster1.mongodb.net/
MONGODB_URI_3=mongodb+srv://user:pass@cluster2.mongodb.net/
MONGODB_URI_4=mongodb+srv://user:pass@cluster3.mongodb.net/

# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot.py .

CMD ["python", "bot.py"]

# docker-compose.yml
version: '3.8'

services:
  bot:
    build: .
    ports:
      - "8080:8080"
    env_file:
      - .env
    restart: unless-stopped
    environment:
      - BOT_TOKEN=${BOT_TOKEN}
      - PORT=8080
      - MONGODB_URI_1=${MONGODB_URI_1}
      - MONGODB_URI_2=${MONGODB_URI_2}
      - MONGODB_URI_3=${MONGODB_URI_3}



      // render.yaml (for Render.com deployment)
{
  "services": [
    {
      "type": "web",
      "name": "squid-game-bot",
      "env": "python",
      "buildCommand": "pip install -r requirements.txt",
      "startCommand": "python bot.py",
      "envVars": [
        {
          "key": "BOT_TOKEN",
          "sync": false
        },
        {
          "key": "PORT",
          "value": "8080"
        },
        {
          "key": "MONGODB_URI_1",
          "sync": false
        },
        {
          "key": "MONGODB_URI_2",
          "sync": false
        }
      ]
    }
  ]
}


# railway.json (for Railway deployment)
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python bot.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}




📋 DEPLOYMENT INSTRUCTIONS:
Method 1: Local
bash
pip install -r requirements.txt
python bot.py
Method 2: Docker
bash
docker-compose up -d



Method 3: Render.com (FREE)
Push code to GitHub

Connect Render to GitHub

Create Web Service

Add environment variables

Deploy!

Method 4: Railway (FREE)
Push to GitHub

Import on Railway

Add env variables

Deploy!

Method 5: Heroku



bash
heroku create squid-game-bot
heroku config:set BOT_TOKEN=your_token
git push heroku main
🌐 UPTIMEROBOT SETUP:
Go to https://uptimerobot.com

Create account (FREE)

Add New Monitor

Type: HTTP(s)

URL: http://your-app-url/health

Interval: 5 minutes

Monitor! ✅

✅ ALL FEATURES:

✅ Web server on port 8080

✅ Health check endpoint

✅ Status monitoring

✅ Stats dashboard

✅ Multiple MongoDB URIs

✅ Multi-user support

✅ Button spam protection

✅ User isolation

✅ Automatic failover

✅ Production ready!

✅ NEW! Game animations – each game now has its own dramatic animation sequence

