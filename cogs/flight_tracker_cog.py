import discord
from discord import app_commands
from discord.ext import commands, tasks
import aiohttp
import datetime
import asyncio
from typing import Optional

from database import DatabaseManager
from .utils import create_pilot_embed

VATSIM_DATA_URL = "https://data.vatsim.net/v3/vatsim-data.json"

class FlightTrackerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_manager = DatabaseManager()
        self.update_flight_trackers.start()

    def cog_unload(self):
        self.update_flight_trackers.cancel()

    @app_commands.command(name="track-pilot", description="Continuously track a pilot's flight in a specific channel.")
    @app_commands.describe(
        cid="The VATSIM CID of the pilot to track.", 
        channel="The channel to post the tracking embed in.",
        role="The role to ping when the pilot comes online (Optional).",
        delete_on_offline="Set to True to delete the message when the pilot logs off."
    )
    async def track_pilot(self, interaction: discord.Interaction, cid: str, channel: discord.TextChannel, delete_on_offline: bool = False, role: Optional[discord.Role] = None):
        await interaction.response.defer(ephemeral=True)

        # Check if this pilot is already being tracked in this guild
        existing_tracker = await self.db_manager.get_flight_tracker_by_cid(interaction.guild_id, cid)
        if existing_tracker:
            await interaction.followup.send(f"A flight tracker for CID `{cid}` already exists in this server.", ephemeral=True)
            return

        # Create a placeholder embed
        embed = discord.Embed(
            title=f"Initializing Flight Tracker for CID: {cid}",
            description="Fetching initial data...",
            color=discord.Color.light_grey()
        )
        
        try:
            message = await channel.send(embed=embed)
        except discord.Forbidden:
            await interaction.followup.send("I don't have permission to send messages in that channel.", ephemeral=True)
            return
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {e}", ephemeral=True)
            return

        # Add to database
        role_id = role.id if role else None
        await self.db_manager.add_flight_tracker(interaction.guild_id, channel.id, message.id, cid, delete_on_offline, role_id)
        
        response_text = f"✅ Flight tracker for CID `{cid}` has been created in {channel.mention}."
        if role:
            response_text += f"\n*I will ping {role.mention} when the pilot comes online.*"
        if delete_on_offline:
            response_text += "\n*This message will be deleted when the pilot goes offline.*"
            
        await interaction.followup.send(response_text, ephemeral=True)
        
        # Immediately run an update for this new tracker
        await self.update_specific_tracker(interaction.guild_id, channel.id, message.id, cid)


    @tasks.loop(minutes=5)
    async def update_flight_trackers(self):
        all_trackers = await self.db_manager.get_all_flight_trackers()
        if not all_trackers:
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(VATSIM_DATA_URL) as response:
                    if response.status != 200:
                        print(f"Error fetching VATSIM data for flight trackers: Status {response.status}")
                        return
                    vatsim_data = await response.json()
        except aiohttp.ClientError as e:
            print(f"AIOHTTP Error fetching VATSIM data for flight trackers: {e}")
            return
            
        pilots_by_cid = {str(p['cid']): p for p in vatsim_data.get('pilots', [])}

        for tracker_data in all_trackers:
            tracker_id, guild_id, channel_id, message_id, cid, delete_on_offline, role_id, ping_sent = tracker_data
            
            channel = self.bot.get_channel(channel_id)
            if not channel:
                await self.db_manager.remove_flight_tracker(tracker_id)
                print(f"Removed tracker {tracker_id} because channel {channel_id} was not found.")
                continue
            
            pilot_data = pilots_by_cid.get(cid)
            
            if pilot_data: # Pilot is ONLINE
                embed = create_pilot_embed(pilot_data)
                content_to_send = None

                # Check if we need to send a ping for the first time
                if role_id and not ping_sent:
                    guild = self.bot.get_guild(guild_id)
                    if guild:
                        role = guild.get_role(role_id)
                        if role:
                            content_to_send = role.mention
                    # Mark ping as sent to prevent re-pinging on next update
                    await self.db_manager.set_flight_tracker_ping_status(tracker_id, True)

                if message_id:
                    try:
                        message = await channel.fetch_message(message_id)
                        # On subsequent updates, content_to_send will be None, removing the ping
                        await message.edit(content=content_to_send, embed=embed)
                        await asyncio.sleep(1)
                    except discord.NotFound:
                        # Message was deleted, so we'll post a new one
                        new_message = await channel.send(content=content_to_send, embed=embed)
                        await self.db_manager.update_flight_tracker_message(tracker_id, new_message.id)
                    except discord.Forbidden:
                        continue
                else: # No message_id, need to post a new one
                    try:
                        new_message = await channel.send(content=content_to_send, embed=embed)
                        await self.db_manager.update_flight_tracker_message(tracker_id, new_message.id)
                    except discord.Forbidden:
                        continue

            else: # Pilot is OFFLINE
                # Reset ping status if they were previously online, so they get pinged next time
                if ping_sent:
                    await self.db_manager.set_flight_tracker_ping_status(tracker_id, False)

                if message_id:
                    try:
                        message = await channel.fetch_message(message_id)
                        if delete_on_offline:
                            await message.delete()
                            await self.db_manager.clear_flight_tracker_message(tracker_id)
                        else:
                            embed = self.create_offline_embed(cid)
                            # Edit with no content to remove any lingering pings
                            await message.edit(content=None, embed=embed)
                            await asyncio.sleep(2)
                    except (discord.NotFound, discord.Forbidden):
                        await self.db_manager.clear_flight_tracker_message(tracker_id)

    @update_flight_trackers.before_loop
    async def before_update_flight_trackers(self):
        await self.bot.wait_until_ready()

    async def update_specific_tracker(self, guild_id, channel_id, message_id, cid):
        """Manually triggers an update for a single tracker."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(VATSIM_DATA_URL) as response:
                    if response.status != 200: return
                    vatsim_data = await response.json()
        except aiohttp.ClientError:
            return

        pilot_data = next((p for p in vatsim_data.get('pilots', []) if str(p['cid']) == cid), None)

        channel = self.bot.get_channel(channel_id)
        if not channel: return

        try:
            message = await channel.fetch_message(message_id)
        except (discord.NotFound, discord.Forbidden):
            return

        if pilot_data:
            embed = create_pilot_embed(pilot_data)
        else:
            embed = self.create_offline_embed(cid)
        
        await message.edit(embed=embed)

    def create_offline_embed(self, cid):
        embed = discord.Embed(
            title=f"✈️ Pilot Offline",
            description=f"The pilot with CID `{cid}` is not currently connected to the VATSIM network.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        embed.set_footer(text="Last Updated")
        return embed
        
    @app_commands.command(name="untrack-pilot", description="Stops tracking a pilot and deletes the tracking message.")
    @app_commands.describe(cid="The VATSIM CID of the pilot to untrack.")
    async def untrack_pilot(self, interaction: discord.Interaction, cid: str):
        await interaction.response.defer(ephemeral=True)

        tracker = await self.db_manager.get_flight_tracker_by_cid(interaction.guild_id, cid)
        if not tracker:
            await interaction.followup.send(f"No flight tracker found for CID `{cid}` in this server.", ephemeral=True)
            return

        # Unpack all columns to prevent errors, even if not all are used
        tracker_id, _, channel_id, message_id, _, _, _, _ = tracker
        
        # Delete the message
        try:
            channel = self.bot.get_channel(channel_id)
            if channel and message_id:
                message = await channel.fetch_message(message_id)
                await message.delete()
        except (discord.NotFound, discord.Forbidden):
            # If we can't delete the message, that's okay, we'll still remove the tracker
            pass 
        except Exception as e:
            print(f"Could not delete tracker message {message_id}: {e}")

        # Remove from database
        await self.db_manager.remove_flight_tracker(tracker_id)
        await interaction.followup.send(f"✅ The flight tracker for CID `{cid}` has been removed.", ephemeral=True)

    @untrack_pilot.autocomplete('cid')
    async def untrack_pilot_autocomplete(self, interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
        trackers = await self.db_manager.get_all_flight_trackers()
        guild_trackers = [t for t in trackers if t[1] == interaction.guild_id]

        choices = [
            app_commands.Choice(name=f"CID: {tracker[4]}", value=str(tracker[4]))
            for tracker in guild_trackers
        ]

        if current:
            return [choice for choice in choices if current.lower() in choice.value.lower()]
        
        return choices[:25]


async def setup(bot: commands.Bot):
    await bot.add_cog(FlightTrackerCog(bot))
