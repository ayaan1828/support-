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

# 4. Dynamic Training Storage
SERVER_CONFIG = {
    "trained_knowledge_base": "We operate across multiple airports. If optional upgrades glitch, use !rejoin or reconnect.",
    "departments": "General Flight Support, Premium/First Class Priority Desk, Staff HR",
    "dm_log_channel_id": None,      
    "takeover_channel_id": None     
}

ACTIVE_CLAIMS = {} 

# 5. Core Personality Constraints
BASE_KNOWLEDGE = """You are the official Customer Support Helpdesk Agent for Norwegian Airlines, an elite Roblox aviation group. 
Your primary goal is to resolve passenger issues, handle upgrade complaints, and provide flight operational info based strictly on our uploaded documents.

TONE GUIDELINES:
- Act like an elite airport concierge helpdesk. Always be exceptionally polite, helpful, empathetic, and professional. 
- Keep answers concise, clear, and direct so players can read them easily on mobile or PC while playing Roblox. Do not include emojis in your responses."""

async def generate_ai_reply(user_prompt):
    """Helper function to run text generation using dynamically trained knowledge logs"""
    if not API_KEY:
        return "Configuration Error: The server's 'GEMINI_API_KEY' environment variable is empty."
        
    ai_client = genai.Client(api_key=API_KEY)
    
    # Inject the freshly trained document data straight into the active system context
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

# Command: /claim 
@bot.tree.command(name="claim", description="Claim a passenger's DM support session to pause the AI and take over manually.")
@app_commands.describe(passenger_id="The Discord User ID of the passenger you want to take over support for.")
async def claim(interaction: discord.Interaction, passenger_id: str):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside the server.", ephemeral=True)
        return

    try:
        passenger_user_id = int(passenger_id)
        passenger = await bot.fetch_user(passenger_user_id)
    except Exception:
        await interaction.response.send_message("Invalid user ID. Please provide a valid numeric Discord ID.", ephemeral=True)
        return

    ACTIVE_CLAIMS[passenger_user_id] = interaction.user.id
    
    embed = discord.Embed(
        title="Session Claimed",
        description=f"You have taken over support for {passenger.name}.\nThe AI is now paused for this user. Any message you type in this channel will be sent straight to their DMs.",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=False)
    # Command: /unclaim (Close Ticket)
@bot.tree.command(name="unclaim", description="Close an active support session and return the passenger back to the AI assistant.")
@app_commands.describe(passenger_id="The Discord User ID of the passenger whose session you want to close.")
async def unclaim(interaction: discord.Interaction, passenger_id: str):
    if not interaction.guild:
        await interaction.response.send_message("This command can only be used inside the server.", ephemeral=True)
        return

    try:
        passenger_user_id = int(passenger_id)
        passenger = await bot.fetch_user(passenger_user_id)
    except Exception:
        await interaction.response.send_message("Invalid user ID. Please provide a valid numeric Discord ID.", ephemeral=True)
        return

    if passenger_user_id in ACTIVE_CLAIMS:
        del ACTIVE_CLAIMS[passenger_user_id]
        
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
        await interaction.response.send_message(f"This passenger ({passenger.name}) does not have an active human claim session open.", ephemeral=True)

# Command: /upload (Train Bot on custom text files or web links)
@bot.tree.command(name="upload", description="Provide a website link, Roblox rule page, or text document link to train the AI assistant.")
@is_admin_or_override()
@app_commands.describe(
    url="The full web link or text file URL (e.g. pastebin, roblox group link) containing training documentation."
)
async def upload(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=True) # Give the script time to download the file
    
    try:
        # Fetch the content from the provided URL link
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            scraped_text = response.text
            
            # If the text is overly long, clip it to fit structural limits smoothly
            if len(scraped_text) > 40000:
                scraped_text = scraped_text[:40000]
                
            # Permanently update the active working data registry
            SERVER_CONFIG["trained_knowledge_base"] = scraped_text
            
            embed = discord.Embed(
                title="AI Support Training Complete", 
                description=f"The bot has read the provided source document successfully.\nCharacter count incorporated into memory: {len(scraped_text)} characters.\nAll passenger answers will now reflect these updated rules.", 
                color=discord.Color.green()
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(f"Failed to fetch content from URL. Server returned status code: {response.status_code}", ephemeral=True)
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
        SERVER_CONFIG["dm_log_channel_id"] = dm_logs.id
    if takeover_channel:
        SERVER_CONFIG["takeover_channel_id"] = takeover_channel.id

    status_summary = (
        f"Departments Listed: {SERVER_CONFIG['departments']}\n"
        f"DM Logs Feed Channel: <#{SERVER_CONFIG['dm_log_channel_id']}>\n"
        f"Human Takeover Hub: <#{SERVER_CONFIG['takeover_channel_id']}>"
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

    # A: ROUTING DM CHAT TRAFFIC
    if isinstance(message.channel, discord.DMChannel):
        passenger_id = message.author.id

        if passenger_id in ACTIVE_CLAIMS:
            takeover_chan_id = SERVER_CONFIG["takeover_channel_id"]
            if takeover_chan_id:
                takeover_channel = bot.get_channel(takeover_chan_id)
                if takeover_channel:
                    embed = discord.Embed(description=message.content, color=discord.Color.orange())
                    embed.set_author(name=f"{message.author.name} (ID: {passenger_id})", icon_url=message.author.display_avatar.url)
                    await takeover_channel.send(embed=embed)
                    return
            return

        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(message.content)
                
                passenger_embed = discord.Embed(description=reply, color=discord.Color.light_gray())
                passenger_embed.set_author(name="Norwegian Airlines AI Assistant", icon_url=bot.user.display_avatar.url)
                await message.reply(embed=passenger_embed)
                
                log_chan_id = SERVER_CONFIG["dm_log_channel_id"]
                if log_chan_id:
                    log_channel = bot.get_channel(log_chan_id)
                    if log_channel:
                        log_embed = discord.Embed(color=discord.Color.blue())
                        log_embed.set_author(name=f"DM Log | User: {message.author.name} (ID: {passenger_id})", icon_url=message.author.display_avatar.url)
                        log_embed.add_field(name="Passenger Question", value=message.content, inline=False)
                        log_embed.add_field(name="AI Assistant Response", value=reply, inline=False)
                        await log_channel.send(embed=log_embed)
            except Exception as e:
                await message.reply(f"Helpdesk API Error Encountered:\n```{str(e)}```")
        return 

    # B: ROUTING HUMAN AGENT REPLIES BACK TO PASSENGER DMs
    if message.channel.id == SERVER_CONFIG["takeover_channel_id"]:
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

