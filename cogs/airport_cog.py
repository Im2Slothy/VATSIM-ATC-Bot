import discord
from discord import app_commands
from discord.ext import commands
import datetime
import aiohttp

VATSIM_DATA_URL = "https://data.vatsim.net/v3/vatsim-data.json"

class AirportCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="activity", description="Shows all online activity for a specific airport.")
    @app_commands.describe(icao="The 4-letter ICAO code of the airport (e.g., KLAX).")
    async def airport_activity(self, interaction: discord.Interaction, icao: str):
        await interaction.response.defer(ephemeral=True)
        icao = icao.upper()

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(VATSIM_DATA_URL) as response:
                    if response.status != 200:
                        await interaction.followup.send("Could not retrieve data from VATSIM.", ephemeral=True)
                        return
                    vatsim_data = await response.json()
        except aiohttp.ClientError:
            await interaction.followup.send("An error occurred while trying to contact the VATSIM API.", ephemeral=True)
            return

        # Handle both 4-letter and 3-letter identifiers
        short_icao = icao[1:] if len(icao) == 4 else None
        banned_frequencies = ["199.998", "199.997", "199.999"]

        controllers = [
            c for c in vatsim_data.get('controllers', []) 
            if (c['callsign'].startswith(icao) or (short_icao and c['callsign'].startswith(short_icao)))
            and c['frequency'] not in banned_frequencies
        ]
        atis_list = [a for a in vatsim_data.get('atis', []) if a['callsign'].startswith(icao) or (short_icao and a['callsign'].startswith(short_icao))]
        
        # Flight plans use the full ICAO
        departures = [p for p in vatsim_data.get('pilots', []) if p.get('flight_plan') and p['flight_plan']['departure'] == icao]
        arrivals = [p for p in vatsim_data.get('pilots', []) if p.get('flight_plan') and p['flight_plan']['arrival'] == icao]

        embed = discord.Embed(
            title=f"Activity at {icao}",
            color=discord.Color.og_blurple(),
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        if controllers:
            controller_text = "\n".join(f"**`{c['callsign']}`** ({c['frequency']}) - {c['name']}" for c in sorted(controllers, key=lambda x: x['callsign']))
            embed.add_field(name="📡 Online Controllers", value=controller_text, inline=False)
        else:
            embed.add_field(name="📡 Online Controllers", value="None", inline=False)

        if atis_list:
            atis_text = "\n".join(f"**`{a['callsign']}`** ({a['frequency']})" for a in sorted(atis_list, key=lambda x: x['callsign']))
            embed.add_field(name="📄 Active ATIS", value=atis_text, inline=False)

        if departures:
            dep_text = " ".join(f"`{p['callsign']}`" for p in departures[:20]) # Limit to 20 to avoid huge fields
            embed.add_field(name="🛫 Departures", value=dep_text, inline=False)

        if arrivals:
            arr_text = " ".join(f"`{p['callsign']}`" for p in arrivals[:20])
            embed.add_field(name="🛬 Arrivals", value=arr_text, inline=False)

        if not any([controllers, atis_list, departures, arrivals]):
            embed.description = "No online activity found for this airport."

        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(AirportCog(bot))
