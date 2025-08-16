# VATSIM ATC & Flight Tracker Discord Bot

**Python 3.8+ | discord.py 2.0+ | License: MIT**

A powerful, asynchronous Discord bot designed to provide real-time VATSIM notifications and flight tracking for Discord communities. Built with `discord.py` and `aiosqlite`.

## 🌟 Features

- **Live ATC Notifications** – Get instant updates in a designated channel when an ATC position for a specific airport or center comes online.
- **Persistent Pilot Tracking** – Track a pilot’s flight from takeoff to touchdown with a live-updating embed.
- **Persistent Controller Tracking** – Monitor a specific controller’s session with continuous updates.
- **Role Pinging** – Automatically ping a role when a tracked pilot or controller first comes online.
- **Live Data Lookups** – Slash commands to look up currently online pilots, controllers, or ATIS info.
- **Airport Activity Overview** – Get a summary of departures, arrivals, and controllers for any airport.
- **Permission System** – Assign a specific role (besides Admin) that can configure bot settings.

## ⚙️ Setup & Installation

### Prerequisites

1. Python 3.8+
2. A Discord Bot Token from [Discord Developer Portal](https://discord.com/developers/applications)

### Clone the Repository

```bash
git clone https://github.com/Im2SlothyVATSIM-ATC-Bot.git
cd vatsim-tracker-bot
```

### Install Dependencies

```bash
python -m venv venv
source venv/bin/activate
# (On Windows: venv\Scripts\activate)
pip install -r requirements.txt
```

### Create a .env File

```
DISCORD_TOKEN="YOUR_DISCORD_BOT_TOKEN_HERE"
```

### Run the Bot

```bash
python bot.py
```

The first time you run the bot, it will automatically create a `vatsim_bot.db` file for persistent storage.

## 🚀 Usage

All commands are available as slash commands:

- `/help` – Show the main help embed with a list of commands
- `/atcnotify add <identifier> <channel> [role]` – Set up ATC notifications for an airport
- `/track-pilot <cid> <channel> [role]` – Begin tracking a pilot, optional role ping
- `/track-controller <cid> <channel> [role]` – Begin tracking a controller, optional role ping
- `/untrack-pilot <cid>` – Stop tracking a pilot
- `/untrack-controller <cid>` – Stop tracking a controller
- `/lookup <pilot|atc|atis> <query>` – Look up live VATSIM data

## 🤝 Contributing

- Fork the repo
- Create a new branch (`git checkout -b feature-xyz`)
- Commit your changes (`git commit -m 'Add feature xyz'`)
- Push to your fork and submit a PR

## 📄 License

This project is licensed under the MIT License – see the LICENSE file for details.

## 👨‍💻 Created by Chris! -- Enjoy :)
