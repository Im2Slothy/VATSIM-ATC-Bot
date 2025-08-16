import aiosqlite
import discord
from typing import Optional

DB_FILE = "vatsim_bot.db"

class DatabaseManager:
    """Manages the bot's SQLite database."""
    async def setup(self):
        """Initializes the database and creates tables if they don't exist."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    airport_icao TEXT NOT NULL,
                    channel_id INTEGER NOT NULL,
                    role_id INTEGER,
                    delete_on_offline BOOLEAN DEFAULT FALSE NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    guild_id INTEGER PRIMARY KEY,
                    role_id INTEGER NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS flight_trackers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER,
                    vatsim_cid TEXT NOT NULL,
                    delete_on_offline BOOLEAN DEFAULT FALSE NOT NULL,
                    role_id INTEGER,
                    ping_sent BOOLEAN NOT NULL DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS controller_trackers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    guild_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    message_id INTEGER,
                    vatsim_cid TEXT NOT NULL,
                    delete_on_offline BOOLEAN DEFAULT FALSE NOT NULL,
                    role_id INTEGER,
                    ping_sent BOOLEAN NOT NULL DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS active_notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rule_id INTEGER NOT NULL,
                    message_id INTEGER NOT NULL,
                    channel_id INTEGER NOT NULL,
                    callsign TEXT NOT NULL UNIQUE,
                    FOREIGN KEY (rule_id) REFERENCES notifications(id) ON DELETE CASCADE
                )
            """)
            await db.commit()
            print("Database setup complete.")

    # --- Notification Methods ---
    async def add_notification(self, guild_id: int, airport: str, channel_id: int, role_id: Optional[int], delete_on_offline: bool):
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "INSERT INTO notifications (guild_id, airport_icao, channel_id, role_id, delete_on_offline) VALUES (?, ?, ?, ?, ?)",
                (guild_id, airport.upper(), channel_id, role_id, delete_on_offline)
            )
            await db.commit()

    async def get_notifications_by_guild(self, guild_id: int) -> list:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, airport_icao, channel_id, role_id FROM notifications WHERE guild_id = ?", (guild_id,)) as cursor:
                return await cursor.fetchall()

    async def get_all_notifications(self) -> list:
         async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, guild_id, airport_icao, channel_id, role_id, delete_on_offline FROM notifications") as cursor:
                return await cursor.fetchall()

    async def remove_notification(self, notification_id: int):
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM notifications WHERE id = ?", (notification_id,))
            await db.commit()

    async def notification_exists(self, guild_id: int, airport: str, channel_id: int, role_id: Optional[int]) -> bool:
        """Checks if an identical notification rule already exists."""
        async with aiosqlite.connect(DB_FILE) as db:
            query = "SELECT 1 FROM notifications WHERE guild_id = ? AND airport_icao = ? AND channel_id = ? AND "
            params = [guild_id, airport.upper(), channel_id]
            if role_id is None:
                query += "role_id IS NULL"
            else:
                query += "role_id = ?"
                params.append(role_id)

            async with db.execute(query, tuple(params)) as cursor:
                return await cursor.fetchone() is not None
    
    # --- Active Notification Methods (for message deletion) ---
    async def add_active_notification(self, rule_id: int, message_id: int, channel_id: int, callsign: str):
        """Stores a sent notification message so it can be deleted later."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "INSERT OR IGNORE INTO active_notifications (rule_id, message_id, channel_id, callsign) VALUES (?, ?, ?, ?)",
                (rule_id, message_id, channel_id, callsign)
            )
            await db.commit()

    async def get_active_notification_by_callsign(self, callsign: str) -> tuple | None:
        """Retrieves an active notification's details using the controller's callsign."""
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, message_id, channel_id FROM active_notifications WHERE callsign = ?", (callsign,)) as cursor:
                return await cursor.fetchone()
    
    async def get_all_active_rule_callsign_pairs(self) -> list:
        """Gets all (rule_id, callsign) pairs to rehydrate the bot's memory."""
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT rule_id, callsign FROM active_notifications") as cursor:
                return await cursor.fetchall()

    async def remove_active_notification_by_callsign(self, callsign: str):
        """Removes an active notification record from the database."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM active_notifications WHERE callsign = ?", (callsign,))
            await db.commit()

    # --- Permission Methods ---
    async def set_management_role(self, guild_id: int, role_id: int):
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "INSERT OR REPLACE INTO permissions (guild_id, role_id) VALUES (?, ?)",
                (guild_id, role_id)
            )
            await db.commit()

    async def get_management_role(self, guild_id: int) -> int | None:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT role_id FROM permissions WHERE guild_id = ?", (guild_id,)) as cursor:
                result = await cursor.fetchone()
                return result[0] if result else None
            
    async def get_watched_airport_count(self) -> int:
        """Counts the number of unique airports being watched."""
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT COUNT(DISTINCT airport_icao) FROM notifications") as cursor:
                result = await cursor.fetchone()
                return result[0] if result else 0

    # --- Flight Tracker Methods ---
    async def add_flight_tracker(self, guild_id: int, channel_id: int, message_id: int, vatsim_cid: str, delete_on_offline: bool, role_id: Optional[int]):
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "INSERT INTO flight_trackers (guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id)
            )
            await db.commit()

    async def get_all_flight_trackers(self) -> list:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id, ping_sent FROM flight_trackers") as cursor:
                return await cursor.fetchall()

    async def get_flight_tracker_by_cid(self, guild_id: int, vatsim_cid: str) -> tuple | None:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id, ping_sent FROM flight_trackers WHERE guild_id = ? AND vatsim_cid = ?", (guild_id, vatsim_cid)) as cursor:
                return await cursor.fetchone()

    async def remove_flight_tracker(self, tracker_id: int):
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM flight_trackers WHERE id = ?", (tracker_id,))
            await db.commit()

    async def update_flight_tracker_message(self, tracker_id: int, new_message_id: int):
        """Updates the message ID for a flight tracker, used after re-posting."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE flight_trackers SET message_id = ? WHERE id = ?", (new_message_id, tracker_id))
            await db.commit()

    async def clear_flight_tracker_message(self, tracker_id: int):
        """Sets a flight tracker's message ID to NULL, used after deleting a message."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE flight_trackers SET message_id = NULL WHERE id = ?", (tracker_id,))
            await db.commit()
            
    async def set_flight_tracker_ping_status(self, tracker_id: int, status: bool):
        """Sets the ping_sent status for a flight tracker."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE flight_trackers SET ping_sent = ? WHERE id = ?", (status, tracker_id))
            await db.commit()

    # --- Controller Tracker Methods ---
    async def add_controller_tracker(self, guild_id: int, channel_id: int, message_id: int, vatsim_cid: str, delete_on_offline: bool, role_id: Optional[int]):
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute(
                "INSERT INTO controller_trackers (guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id) VALUES (?, ?, ?, ?, ?, ?)",
                (guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id)
            )
            await db.commit()

    async def get_all_controller_trackers(self) -> list:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id, ping_sent FROM controller_trackers") as cursor:
                return await cursor.fetchall()

    async def get_controller_tracker_by_cid(self, guild_id: int, vatsim_cid: str) -> tuple | None:
        async with aiosqlite.connect(DB_FILE) as db:
            async with db.execute("SELECT id, guild_id, channel_id, message_id, vatsim_cid, delete_on_offline, role_id, ping_sent FROM controller_trackers WHERE guild_id = ? AND vatsim_cid = ?", (guild_id, vatsim_cid)) as cursor:
                return await cursor.fetchone()

    async def remove_controller_tracker(self, tracker_id: int):
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("DELETE FROM controller_trackers WHERE id = ?", (tracker_id,))
            await db.commit()

    async def update_tracker_message(self, tracker_id: int, new_message_id: int):
        """Updates the message ID for a controller tracker, used after re-posting."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE controller_trackers SET message_id = ? WHERE id = ?", (new_message_id, tracker_id))
            await db.commit()

    async def clear_tracker_message(self, tracker_id: int):
        """Sets a tracker's message ID to NULL, used after deleting a message."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE controller_trackers SET message_id = NULL WHERE id = ?", (tracker_id,))
            await db.commit()

    async def set_controller_tracker_ping_status(self, tracker_id: int, status: bool):
        """Sets the ping_sent status for a controller tracker."""
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute("UPDATE controller_trackers SET ping_sent = ? WHERE id = ?", (status, tracker_id))
            await db.commit()
