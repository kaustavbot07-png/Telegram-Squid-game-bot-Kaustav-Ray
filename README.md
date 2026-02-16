# XP & Leveling Telegram Bot

A Python Telegram Bot that tracks user activity, awards XP for messages, and maintains a global leaderboard.

## Features

*   **XP System:** Users earn XP for every message sent in any group where the bot is present.
    *   **Daily Limit:** Max 2000 XP per day per user to prevent farming.
    *   **Leveling:** Unlimited levels with increasing difficulty.
*   **Leaderboard:** `/top` command displays the top 200 players globally.
    *   **Medals:** Top 3 players receive 🥇, 🥈, 🥉 badges.
*   **Multi-Database Support:** Configure multiple MongoDB URIs. The bot automatically spills over to the next database if one becomes full or unreachable.
    *   **Failover:** If a write fails (e.g., DB full), the bot seamlessly migrates the user to the next available database.
    *   **Data Integrity:** Reads are performed across all connected databases, resolving conflicts using the "Last Write Wins" strategy.
*   **User Profiles:**
    *   **Custom Names:** Users can set a unique display name using `/changename`.
    *   **Validation:** Names must be alphabetic only (A-Z) and unique across all databases.
*   **Web Server:** Includes a built-in web server for uptime monitoring (compatible with services like UptimeRobot).

## Commands

*   `/start` - Register with the bot and start tracking.
*   `/level` - Check your current Level, XP, and progress bar.
*   `/top` - View the global leaderboard (Top 200).
*   `/changename <new_name>` - Change your display name on the leaderboard. (Must be unique and alphabetic).

## Configuration

Open `bot.py` and configure the following variables at the top of the file:

*   `BOT_TOKEN`: Your Telegram Bot API Token.
*   `ADMIN_ID`: The Telegram ID of the bot administrator.
*   `LOG_CHANNEL_ID`: The ID of the channel where logs (new users, level ups) are sent.
*   `MONGODB_URIS`: A list of MongoDB connection strings. The bot will connect to all of them.
*   `MAX_XP_PER_DAY`: Maximum XP a user can earn in 24 hours (Default: 2000).

```python
MONGODB_URIS = [
    "mongodb+srv://user:pass@cluster0.mongodb.net/...",
    "mongodb+srv://user:pass@cluster1.mongodb.net/...",
]
```

## Installation & Usage

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd <repository_name>
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the bot:**
    ```bash
    python3 bot.py
    ```

## Requirements

*   Python 3.7+
*   `python-telegram-bot`
*   `pymongo`
*   `aiohttp`
*   `dnspython`

## Notes

*   The bot uses a **single-file architecture** (`bot.py`) for simplicity.
*   It is designed to run globally across all chats; no `TARGET_GROUP_ID` is required.
*   The built-in web server listens on port `8080` (or the `PORT` environment variable).
