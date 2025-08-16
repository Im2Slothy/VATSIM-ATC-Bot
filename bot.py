import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from database import DatabaseManager

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

class MyBot(commands.AutoShardedBot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        db_manager = DatabaseManager()
        await db_manager.setup()
        
        # Load cogs
        await self.load_extension("cogs.atc_cog")
        await self.load_extension("cogs.lookup_cog")
        await self.load_extension("cogs.airport_cog")
        await self.load_extension("cogs.flight_tracker_cog")        

        await self.tree.sync()


    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        print('-------')

bot = MyBot()
bot.run(DISCORD_TOKEN)