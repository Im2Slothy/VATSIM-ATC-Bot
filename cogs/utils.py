import discord
import datetime

def create_controller_embed(controller_data: dict) -> discord.Embed:
    """Creates a standardized embed for online VATSIM controller data."""
    logon_time = datetime.datetime.fromisoformat(controller_data['logon_time'].replace('Z', '+00:00'))
    
    embed = discord.Embed(
        title=f"📡 Controller Online: {controller_data['callsign']}",
        description=f"**{controller_data['name']}** (`{controller_data['cid']}`)",
        color=discord.Color.blue(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    embed.add_field(name="Frequency", value=f"`{controller_data['frequency']}`", inline=True)
    embed.add_field(name="Online Since", value=discord.utils.format_dt(logon_time, style='R'), inline=True)
    
    if controller_data.get('text_atis'):
        login_message = "\n".join(controller_data['text_atis'])
        embed.add_field(name="Controller Message", value=f"```\n{login_message}\n```", inline=False)

    embed.set_footer(text="Last Updated")
    return embed

def create_pilot_embed(pilot_data: dict) -> discord.Embed:
    """Creates a standardized embed for online VATSIM pilot data."""
    flight_plan = pilot_data.get('flight_plan')
    logon_time = datetime.datetime.fromisoformat(pilot_data['logon_time'].replace('Z', '+00:00'))

    embed = discord.Embed(
        title=f"✈️ Live Flight: {pilot_data['callsign']}",
        description=f"**{pilot_data['name']}** (`{pilot_data['cid']}`)",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc)
    )
    
    if flight_plan:
        embed.add_field(name="Departure", value=f"`{flight_plan['departure']}`", inline=True)
        embed.add_field(name="Arrival", value=f"`{flight_plan['arrival']}`", inline=True)
        embed.add_field(name="Aircraft", value=f"`{flight_plan['aircraft_short']}`", inline=True)
        if flight_plan.get('route'):
            embed.add_field(name="Route", value=f"```\n{flight_plan['route']}\n```", inline=False)
    
    embed.add_field(name="Altitude", value=f"`{pilot_data['altitude']}` ft", inline=True)
    embed.add_field(name="Speed", value=f"`{pilot_data['groundspeed']}` kts", inline=True)
    embed.add_field(name="Heading", value=f"`{pilot_data['heading']}°`", inline=True)
    
    embed.set_footer(text=f"Online Since: {logon_time.strftime('%Y-%m-%d %H:%M:%S')} UTC | Last Updated")
    return embed