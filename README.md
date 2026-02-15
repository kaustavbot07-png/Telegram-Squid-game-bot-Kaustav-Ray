# Telegram XP & Level Bot

A simple yet engaging Telegram bot that gamifies group interactions. It tracks user activity in groups and awards XP (Experience Points) for every message sent. As users gain XP, they level up, with each level becoming progressively harder to reach.

## 🚀 Features

*   **Activity Tracking:** Monitors group messages and awards XP based on message length.
*   **Leveling System:** Users level up as they accumulate XP.
    *   **Scaling Difficulty:** The XP required for the next level increases quadratically, making high levels a true achievement.
    *   **Unlimited Levels:** There is no cap on the maximum level a user can reach.
*   **Leaderboard:** Displays the Top 200 active users sorted by Level and XP.
*   **Persistence:** Uses MongoDB to store user progress securely.
*   **Web Server:** Includes a built-in web server for uptime monitoring (compatible with Render, Railway, etc.).

## 🛠️ Commands

*   `/start` - Initialize your profile and see basic info.
*   `/level` - Check your current Level, XP, and progress to the next level.
*   `/top` - View the Top 200 Leaderboard.

## ⚙️ Installation & Setup

### Prerequisites

*   Python 3.9+
*   MongoDB Database (e.g., MongoDB Atlas)
*   Telegram Bot Token (from @BotFather)

### Local Setup

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Configure the Bot:**
    *   Open `bot.py` and update the `BOT_TOKEN` and `MONGODB_URIS` variables.

4.  **Run the Bot:**
    ```bash
    python bot.py
    ```

## 🏗️ Deployment

This bot is ready for deployment on platforms like Render, Railway, or Heroku.

**Docker:**
A `Dockerfile` is included (ensure it copies `bot.py` and `requirements.txt`).
```bash
docker build -t xp-bot .
docker run -p 8080:8080 xp-bot
```

## 📝 Configuration

The following variables are configured in `bot.py`:

*   `BOT_TOKEN`: Your Telegram Bot API Token.
*   `MONGODB_URIS`: List of MongoDB connection strings.
*   `WEB_SERVER_PORT`: Port for the web server (defaults to 8080).

## 📊 Leveling Formula

The XP required to reach the next level is calculated as:
`XP_Required = (Current_Level^2) * 50 + (Current_Level * 100)`

This ensures a steep progression curve!
