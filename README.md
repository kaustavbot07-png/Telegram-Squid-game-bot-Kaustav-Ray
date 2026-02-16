# XP & Leveling Telegram Bot

A Python Telegram Bot that tracks user activity, awards XP for messages, and maintains a global leaderboard.

## Features

*   **XP System:** Users earn XP for every message sent in the group.
*   **Leveling:** Unlimited levels with increasing difficulty.
*   **Leaderboard:** `/top` command displays the top 200 players globally.
*   **Multi-Database Support:** Configure multiple MongoDB URIs. The bot automatically spills over to the next database if one becomes full or unreachable.
*   **Data Integrity:** Reads are performed across all connected databases, resolving conflicts using the "Last Write Wins" strategy.
*   **Web Server:** Includes a built-in web server for uptime monitoring (compatible with services like UptimeRobot).

## Commands

*   `/start` - Register with the bot and start tracking.
*   `/level` - Check your current Level, XP, and progress bar.
*   `/top` - View the global leaderboard (Top 200).
*   `/changename <new_name>` - Change your display name on the leaderboard.

## Configuration

Open `bot.py` and configure the following variables at the top of the file:

*   `BOT_TOKEN`: Your Telegram Bot API Token.
*   `ADMIN_ID`: The Telegram ID of the bot administrator.
*   `LOG_CHANNEL_ID`: The ID of the channel where logs (new users, level ups) are sent.
*   `MONGODB_URIS`: A list of MongoDB connection strings. The bot will connect to all of them.

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
*   It is designed to run on platforms like Heroku, Railway, or VPS.
*   The built-in web server listens on port `8080` (or the `PORT` environment variable).
