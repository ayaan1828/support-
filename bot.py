import os
import discord
from discord.ext import commands
from discord import app_commands
from google import genai
from google.genai import types
import requests

# 1. Initialize Discord Bot Configuration
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Fetch API Credentials from Fusion Panel Settings
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()

# 3. Global Hardcoded Override Permission
OVERRIDE_USER_ID = 1433433247735353370

# 4. Dynamic Training & Thread Storage Workspace Registry
SERVER_CONFIG = {
    "trained_knowledge_base": "We operate across multiple airports. If optional upgrades glitch, use !rejoin or reconnect.",
    "departments": "General Flight Support, Premium/First Class Priority Desk, Staff HR",
    "dm_log_thread_id": None,      
    "takeover_thread_id": None,    
    "requests_thread_id": None     
}

ACTIVE_CLAIMS = {} 

# 5. Core Personality Constraints
BASE_KNOWLEDGE = """You are the official Customer Support Helpdesk Agent for Norwegian Airlines, an elite Roblox aviation group. 
Your primary goal is to resolve passenger issues, handle upgrade complaints, and provide flight operational info based strictly on our uploaded documents.

HUMAN ASSISTANCE PROTOCOL:
If a passenger explicitly asks to talk to a real person, a manager, a staff member, or a human agent AND they present a valid reason (like a complicated bug, structural complaint, or staff report), politely inform them that you are lodging a human assistance request alert for them. Tell them our flight representatives have been notified and will message them shortly right here in their DMs.

TONE GUIDELINES:
- Act like an elite airport concierge helpdesk. Always be exceptionally polite, helpful, empathetic, and professional. 
- Keep answers concise, clear, and direct so players can read them easily on mobile or PC while playing Roblox. Do not include emojis in your responses."""

async def generate_ai_reply(user_prompt):
    """Helper function to run text generation using dynamically trained knowledge logs"""
    if not API_KEY:
        return "Configuration Error: The server's 'GEMINI_API_KEY' environment variable is empty."
        
    ai_client = genai.Client(api_key=API_KEY)
    full_context = f"{BASE_KNOWLEDGE}\n\nTRAINED AIRLINE KNOWLEDGE AND RULES:\n{SERVER_CONFIG['trained_knowledge_base']}\n\nDEPARTMENTS:\n{SERVER_CONFIG['departments']}"
    
    response = ai_client.models.generate_content(
        model='gemini-3.6-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=full_context,
            temperature=0.7
        )
    )
    return response.text if response.text else "I am processing flight data. Could you please rephrase your request?"
    # Custom Permission Check: Grant access if user has Manage Roles OR is the hardcoded ID
def is_admin_or_override():
    def predicate(interaction: discord.Interaction) -> bool:
        if interaction.user.id == OVERRIDE_USER_ID:
            return True
        if interaction.permissions.manage_roles:
            return True
        raise app_commands.MissingPermissions(["manage_roles"])
    return app_commands.check(predicate)

# 6. Application Commands Interface Setup
@bot.event
async def on_ready():
    print("Synchronizing global slash commands...")
    try:
        await bot.tree.sync() 
        print(f"Norwegian Airlines Support Bot is active as {bot.user.name} and commands are synced!")
    except Exception as e:
        print(f"Error syncing commands: {e}")

# Command: /claim (Native Selection)
@bot.tree.command(name="claim", description="Claim a passenger's DM support session to pause the AI and take over manually.")
@app_commands.describe(passenger="Select the server member you want to take over support for from the member list.")
async def claim(interaction: discord.Interaction, passenger: discord.Member):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside the server.", ephemeral=True)
        return

    ACTIVE_CLAIMS[passenger.id] = interaction.user.id
    
    embed = discord.Embed(
        title="Session Claimed",
        description=f"You have taken over support for {passenger.name}.\nThe AI is now paused for this user. Any message you type in the designated takeover thread will be sent straight to their DMs.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)

# Command: /unclaim (Native Selection)
@bot.tree.command(name="unclaim", description="Close an active support session and return the passenger back to the AI assistant.")
@app_commands.describe(passenger="Select the server member whose session you want to close.")
async def unclaim(interaction: discord.Interaction, passenger: discord.Member):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside the server.", ephemeral=True)
        return

    if passenger.id in ACTIVE_CLAIMS:
        del ACTIVE_CLAIMS[passenger.id]
        
        staff_embed = discord.Embed(
            title="Session Closed",
            description=f"Support for {passenger.name} has been wrapped up. The AI is now re-enabled for this user.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=staff_embed)
        
        try:
            passenger_embed = discord.Embed(
                description="This support session has been closed by Norwegian Airlines staff. The AI Automated Helpdesk is now active to assist you again.",
                color=discord.Color.red()
            )
            passenger_embed.set_author(name="Norwegian Airlines AI Assistant", icon_url=bot.user.display_avatar.url)
            await passenger.send(embed=passenger_embed)
        except Exception:
            pass
    else:
        await interaction.response.send_message(f"This member ({passenger.name}) does not have an active human claim session open.", ephemeral=True)
        # Command: /autoconfigure (Auto-Creates Channel & Target Sub-Threads)
@bot.tree.command(name="autoconfigure", description="Instantly provisions the #norwegian-helpdesk channel and sets up all support threads.")
@is_admin_or_override()
async def autoconfigure(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside a server.", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    try:
        channel = discord.utils.get(guild.text_channels, name="norwegian-helpdesk")
        if not channel:
            channel = await guild.create_text_channel(name="norwegian-helpdesk", topic="Central Hub for Norwegian Airlines Automated AI and Human Support Streams.")

        log_thread = discord.utils.get(channel.threads, name="dm-logs")
        if not log_thread:
            log_thread = await channel.create_thread(name="dm-logs", type=discord.ChannelType.public_thread)

        takeover_thread = discord.utils.get(channel.threads, name="human-takeover")
        if not takeover_thread:
            takeover_thread = await channel.create_thread(name="human-takeover", type=discord.ChannelType.public_thread)

        requests_thread = discord.utils.get(channel.threads, name="human-requests")
        if not requests_thread:
            requests_thread = await channel.create_thread(name="human-requests", type=discord.ChannelType.public_thread)

        SERVER_CONFIG["dm_log_thread_id"] = log_thread.id
        SERVER_CONFIG["takeover_thread_id"] = takeover_thread.id
        SERVER_CONFIG["requests_thread_id"] = requests_thread.id

        summary = (
            f"Workspace Setup Successful!\n\n"
            f"Master Hub Channel: <#{channel.id}>\n"
            f"Logs Thread: <#{log_thread.id}>\n"
            f"Takeover Chat Thread: <#{takeover_thread.id}>\n"
            f"Staff Handover Alerts: <#{requests_thread.id}>"
        )
        embed = discord.Embed(title="Infrastructure Configured", description=summary, color=discord.Color.green())
        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.followup.send(f"Workspace Configuration Failed: {str(e)}", ephemeral=True)

# Command: /upload
@bot.tree.command(name="upload", description="Provide a website link, Roblox rule page, or text document link to train the AI assistant.")
@is_admin_or_override()
@app_commands.describe(url="The web link or text file URL containing training documentation.")
async def upload(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=True)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code == 200:
            scraped_text = response.text
            if len(scraped_text) > 40000:
                scraped_text = scraped_text[:40000]
            SERVER_CONFIG["trained_knowledge_base"] = scraped_text
            embed = discord.Embed(title="AI Support Training Complete", description=f"The bot has read the provided source document successfully.\nCharacter count incorporated into memory: {len(scraped_text)} characters.", color=discord.Color.green())
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to fetch content from URL. Status code: {response.status_code}", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Training Exception Encountered: {str(e)}", ephemeral=True)

# Command: /configure
@bot.tree.command(name="configure", description="Configure corporate departments and channel outputs.")
@is_admin_or_override()  
@app_commands.describe(
    departments="List of custom organizational support divisions.",
    dm_logs="The text channel where normal AI-passenger DM chat logs mirror into.",
    takeover_channel="The hub channel where support representatives monitor and execute /claim commands."
)
async def configure(
    interaction: discord.Interaction, 
    departments: str = None, 
    dm_logs: discord.TextChannel = None, 
    takeover_channel: discord.TextChannel = None
):
    if departments:
        SERVER_CONFIG["departments"] = departments
    if dm_logs:
        SERVER_CONFIG["dm_log_thread_id"] = dm_logs.id
    if takeover_channel:
        SERVER_CONFIG["takeover_thread_id"] = takeover_channel.id

    status_summary = (
        f"Departments Listed: {SERVER_CONFIG['departments']}\n"
        f"DM Logs Feed Channel: <#{SERVER_CONFIG['dm_log_thread_id']}>\n"
        f"Human Takeover Hub: <#{SERVER_CONFIG['takeover_thread_id']}>"
    )
    
    embed = discord.Embed(title="Norwegian Airlines AI Configuration Updated", description=status_summary, color=discord.Color.green())
    await interaction.response.send_message(embed=embed, ephemeral=True)

@configure.error
async def configure_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("Access Denied: You need the Manage Roles permission to modify configurations.", ephemeral=True)

# 7. Messaging Router Pipeline Logic
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # A: ROUTING INBOUND DM TRAFFIC FROM PASSENGERS
    if isinstance(message.channel, discord.DMChannel):
        passenger_id = message.author.id

        if passenger_id in ACTIVE_CLAIMS:
            takeover_th_id = SERVER_CONFIG["takeover_thread_id"]
            if takeover_th_id:
                takeover_thread = bot.get_channel(takeover_th_id)
                if takeover_thread:
                    embed = discord.Embed(description=message.content, color=discord.Color.orange())
                    embed.set_author(name=f"{message.author.name} (ID: {passenger_id})", icon_url=message.author.display_avatar.url)
                    await takeover_thread.send(embed=embed)
                    return
            return

        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(message.content)
                
                passenger_embed = discord.Embed(description=reply, color=discord.Color.light_gray())
                passenger_embed.set_author(name="Norwegian Airlines AI Assistant", icon_url=bot.user.display_avatar.url)
                await message.reply(embed=passenger_embed)
                
                if "human assistance request alert" in reply.lower() or "notified" in reply.lower():
                    req_th_id = SERVER_CONFIG["requests_thread_id"]
                    if req_th_id:
                        req_thread = bot.get_channel(req_th_id)
                        if req_thread:
                            req_embed = discord.Embed(title="Human Assistance Requested", description=f"Passenger **{message.author.name}** requires human agent intervention.\nUser Profile ID: `{passenger_id}`\n\n**Reason Prompt:** {message.content}", color=discord.Color.gold())
                            req_embed.set_thumbnail(url=message.author.display_avatar.url)
                            await req_thread.send(content="@here", embed=req_embed)
                
                log_th_id = SERVER_CONFIG["dm_log_thread_id"]
                if log_th_id:
                    log_thread = bot.get_channel(log_th_id)
                    if log_thread:
                        log_embed = discord.Embed(color=discord.Color.blue())
                        log_embed.set_author(name=f"DM Log | User: {message.author.name}", icon_url=message.author.display_avatar.url)
                        log_embed.add_field(name="Passenger Question", value=message.content, inline=False)
                        log_embed.add_field(name="AI Response", value=reply, inline=False)
                        await log_thread.send(embed=log_embed)
            except Exception as e:
                await message.reply(f"Helpdesk API Error Encountered:\n```{str(e)}```")
        return 

    # B: ROUTING HUMAN AGENT REPLIES BACK TO PASSENGER DMs
    if message.channel.id == SERVER_CONFIG["takeover_thread_id"]:
        target_passenger_id = None
        for p_id, s_id in ACTIVE_CLAIMS.items():
            if s_id == message.author.id:
                target_passenger_id = p_id
                break
        
        if target_passenger_id:
            try:
                passenger_user = await bot.fetch_user(target_passenger_id)
                staff_embed = discord.Embed(description=message.content, color=discord.Color.blue())
                staff_embed.set_author(name=message.author.name, icon_url=message.author.display_avatar.url)
                
                await passenger_user.send(embed=staff_embed)
                await message.add_reaction("✅")
            except Exception as e:
                await message.channel.send(f"Failed to route message to passenger DMs: {e}")
        return

    # C: HANDLING PUBLIC SERVER MENTIONS (@bot)
    if bot.user.mentioned_in(message):
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not user_prompt:
            embed = discord.Embed(description="Welcome to Norwegian Airlines Customer Support! Open a private DM with me for direct assistance.", color=discord.Color.light_gray())
            embed.set_author(name="Norwegian Airlines AI Assistant", icon_url=bot.user.display_avatar.url)
            await message.reply(embed=embed)
            return

        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(user_prompt)
                public_embed = discord.Embed(description=reply, color=discord.Color.light_gray())
                                public_embed.set_author(name="Norwegian Airlines AI Assistant", icon_url=bot.user.display_avatar.url)
                await message.reply(embed=public_embed)
            except Exception as e:
                await message.reply(f"Helpdesk API Error Encountered:\n```{str(e)}```")

    await bot.process_commands(message)

# Pre-flight safety check for token variables
if not DISCORD_TOKEN:
    raise ValueError("CRITICAL ERROR: DISCORD_TOKEN is missing or completely unreadable on the settings page.")

bot.run(DISCORD_TOKEN)


        

    
