import discord
from discord import app_commands
from discord.ext import commands
import aiohttp
import datetime

from .utils import create_controller_embed, create_pilot_embed

VATSIM_DATA_URL = "https://data.vatsim.net/v3/vatsim-data.json"

class LookupCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    lookup = app_commands.Group(name="lookup", description="Commands to look up live VATSIM data.")

    @lookup.command(name="atc", description="Look up a specific, currently online ATC controller.")
    @app_commands.describe(callsign="The full callsign of the controller (e.g., PHL_TWR).")
    async def lookup_atc(self, interaction: discord.Interaction, callsign: str):
        await interaction.response.defer(ephemeral=True)
        
        # Fetches fresh data every time
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(VATSIM_DATA_URL) as response:
                    if response.status != 200:
                        await interaction.followup.send("Could not retrieve data from VATSIM.", ephemeral=True)
                        return
                    data = await response.json()
        except aiohttp.ClientError:
            await interaction.followup.send("An error occurred while trying to contact the VATSIM API.", ephemeral=True)
            return

        found_controller = None
        for controller in data.get('controllers', []):
            if controller['callsign'].upper() == callsign.upper():
                found_controller = controller
                break
        
        if not found_controller:
            await interaction.followup.send(f"No controller found with the callsign `{callsign.upper()}`.")
            return

        embed = create_controller_embed(found_controller)
        # Override footer and timestamp for lookup context
        logon_time = datetime.datetime.fromisoformat(found_controller['logon_time'].replace('Z', '+00:00'))
        embed.set_footer(text="Logged on at (UTC)").timestamp = logon_time
        await interaction.followup.send(embed=embed)


    @lookup.command(name="atis", description="Get the current ATIS for an airport.")
    @app_commands.describe(airport="The ICAO code of the airport (e.g., KPHL).")
    async def lookup_atis(self, interaction: discord.Interaction, airport: str):
        await interaction.response.defer(ephemeral=True)
        
        # Fetches fresh data every time
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(VATSIM_DATA_URL) as response:
                    if response.status != 200:
                        await interaction.followup.send("Could not retrieve data from VATSIM.", ephemeral=True)
                        return
                    data = await response.json()
        except aiohttp.ClientError:
            await interaction.followup.send("An error occurred while trying to contact the VATSIM API.", ephemeral=True)
            return

        airport_upper = airport.upper()
        prefixes_to_check = {airport_upper}
        if len(airport_upper) == 3:
            prefixes_to_check.add(f"K{airport_upper}")
        elif len(airport_upper) == 4 and airport_upper.startswith('K'):
            prefixes_to_check.add(airport_upper[1:])

        matching_atis_list = []
        for atis in data.get('atis', []):
            if any(atis['callsign'].startswith(prefix) for prefix in prefixes_to_check):
                matching_atis_list.append(atis)
        
        if not matching_atis_list:
            await interaction.followup.send(f"No active ATIS found for `{airport.upper()}`.")
            return
            
        embed = discord.Embed(
            title=f"📄 ATIS for {airport.upper()}",
            color=discord.Color.dark_green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        # Bless Gemini for being smart asf
        for atis in sorted(matching_atis_list, key=lambda a: a['callsign']):
            atis_type_name = atis['callsign'].replace(f"{airport.upper()}_", "").replace("_ATIS", "")
            if atis_type_name in ['D', 'A']:
                atis_type_name = {'D': 'Departure', 'A': 'Arrival'}.get(atis_type_name, atis_type_name)
            
            atis_field_name = f"ATIS ({atis_type_name}) - {atis['frequency']}" if atis_type_name else f"ATIS - {atis['frequency']}"
            
            atis_text = '\n'.join(atis['text_atis'])
            embed.add_field(name=atis_field_name, value=f"```\n{atis_text}\n```", inline=False)
            
        await interaction.followup.send(embed=embed)
        
    @lookup.command(name="pilot", description="Look up a specific, currently online pilot.")
    @app_commands.describe(cid="The VATSIM CID of the pilot to look up.")
    async def lookup_pilot(self, interaction: discord.Interaction, cid: str):
        await interaction.response.defer(ephemeral=True)

        # Fetches fresh data every time
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(VATSIM_DATA_URL) as response:
                    if response.status != 200:
                        await interaction.followup.send("Could not retrieve data from VATSIM.", ephemeral=True)
                        return
                    data = await response.json()
        except aiohttp.ClientError:
            await interaction.followup.send("An error occurred while trying to contact the VATSIM API.", ephemeral=True)
            return

        found_pilot = None
        for pilot in data.get('pilots', []):
            if str(pilot['cid']) == cid:
                found_pilot = pilot
                break

        if not found_pilot:
            await interaction.followup.send(f"No online pilot found with the CID `{cid}`.", ephemeral=True)
            return
            
        embed = create_pilot_embed(found_pilot)
        # Override footer and timestamp for lookup context
        logon_time = datetime.datetime.fromisoformat(found_pilot['logon_time'].replace('Z', '+00:00'))
        embed.set_footer(text="Logged on at (UTC)").timestamp = logon_time
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(LookupCog(bot))