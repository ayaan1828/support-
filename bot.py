import os
import discord
from discord.ext import commands
from discord import app_commands
from google import genai
from google.genai import types

# 1. Initialize Discord Bot Configuration
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Fetch API Credentials from Fusion Panel Settings
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()

# 3. Dynamic Application Memory Storage
SERVER_CONFIG = {
    "info_documents": "We operate across multiple airports. If optional upgrades glitch, use !rejoin or reconnect.",
    "departments": "General Flight Support, Premium/First Class Priority Desk, Staff HR",
    "dm_log_channel_id": None,      
    "takeover_channel_id": None     
}

ACTIVE_CLAIMS = {} 

# 4. Standard Airline Guidelines Context
BASE_KNOWLEDGE = """You are the official Customer Support Helpdesk Agent for Norwegian Airlines, an elite Roblox aviation group. 
Your primary goal is to resolve passenger issues, handle upgrade complaints, and provide flight operational info.

SUPPORT PROTOCOLS & FAQ:
- Airports: We operate across multiple airports. Do not list just one single hub. We fly to various destinations.
- Upgrade Glitches: If a passenger bought an optional upgrade/gamepass and it is glitching, instruct them to use the '!rejoin' command in-game or reconnect to the Roblox server. If that fails, tell them they can continue messaging you here in DMs for direct support.
- Support Channel: Our direct customer support helpdesk is handled entirely here through Direct Messages (DMs). Passengers can message the bot anytime for private assistance.
- Flight Schedules: We announce upcoming flights in our server's announcement channels. Advise users to check pinned messages there. Do not guess or make up flight times.
- Exploiter / Troller Reports: Direct passengers to report disruptions to our active moderation team or open a claim. Do not attempt to issue punishments yourself.
- Staff Promotions: To join the Norwegian Airlines crew or earn promotions, passengers must attend official training sessions announced ahead of time in the Discord server.

TONE GUIDELINES:
- Act like an elite airport concierge helpdesk. Always be exceptionally polite, helpful, empathetic, and professional. 
- Keep answers concise, clear, and direct so players can read them easily on mobile or PC while playing Roblox."""

async def generate_ai_reply(user_prompt):
    """Helper function to run text generation through active Gemini Cloud endpoint"""
    if not API_KEY:
        return "⚠️ Configuration Error: The server's 'GEMINI_API_KEY' environment variable is empty."
        
    ai_client = genai.Client(api_key=API_KEY)
    full_context = f"{BASE_KNOWLEDGE}\n\nCURRENT SERVER SETTINGS:\n{SERVER_CONFIG['info_documents']}\nDEPARTMENTS:\n{SERVER_CONFIG['departments']}"
    
    response = ai_client.models.generate_content(
        model='gemini-3.6-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=full_context,
            temperature=0.7
        )
    )
    return response.text if response.text else "I am processing flight data. Could you please rephrase your request?"

# 5. Application Commands Interface Setup
@bot.event
async def on_ready():
    print("🔄 Synchronizing global slash commands...")
    try:
        await bot.tree.sync() 
        print(f"✈️ Norwegian Airlines Support Bot is active as {bot.user.name} and commands are synced!")
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
        await interaction.response.send_message("❌ Invalid user ID. Please provide a valid numeric Discord ID.", ephemeral=True)
        return

    ACTIVE_CLAIMS[passenger_user_id] = interaction.user.id
    await interaction.response.send_message(
        f"✅ **Session Claimed!** You have taken over support for **{passenger.name}**.\n"
        f"The AI is now **PAUSED** for this user. Any message you type in this channel will be sent straight to their DMs. "
        f"They can text you back here.", 
        ephemeral=False
    )

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
        await interaction.response.send_message("❌ Invalid user ID. Please provide a valid numeric Discord ID.", ephemeral=True)
        return

    if passenger_user_id in ACTIVE_CLAIMS:
        del ACTIVE_CLAIMS[passenger_user_id]
        await interaction.response.send_message(f"🔒 **Session Closed!** Support for **{passenger.name}** has been wrapped up. The AI is now **RE-ENABLED** for this user.")
        try:
            await passenger.send("🔒 *This support session has been closed by Norwegian Airlines staff. The AI Automated Helpdesk is now active to assist you again.*")
        except Exception:
            pass
    else:
        await interaction.response.send_message(f"⚠️ This passenger (**{passenger.name}**) does not have an active human claim session open.", ephemeral=True)

# Command: /configure
@bot.tree.command(name="configure", description="Configure AI guidelines, corporate departments, and channel outputs.")
@app_commands.checks.has_permissions(manage_roles=True)
@app_commands.describe(
    documents="Custom rules or update details the AI should read to answer passenger prompts.",
    departments="List of custom organizational support divisions.",
    dm_logs="The text channel where normal AI-passenger DM chat logs mirror into.",
    takeover_channel="The hub channel where support representatives monitor and execute /claim commands."
)
async def configure(
    interaction: discord.Interaction, 
    documents: str = None, 
    departments: str = None, 
    dm_logs: discord.TextChannel = None, 
    takeover_channel: discord.TextChannel = None
):
    if documents:
        SERVER_CONFIG["info_documents"] = documents
    if departments:
        SERVER_CONFIG["departments"] = departments
    if dm_logs:
        SERVER_CONFIG["dm_log_channel_id"] = dm_logs.id
    if takeover_channel:
        SERVER_CONFIG["takeover_channel_id"] = takeover_channel.id

    status_summary = (
        f"🛠️ **Norwegian Airlines AI Configuration Updated!**\n\n"
        f"📂 **Documents Status:** Updated\n"
        f"🏢 **Departments Listed:** {SERVER_CONFIG['departments']}\n"
        f"📋 **DM Logs Feed Channel:** <#{SERVER_CONFIG['dm_log_channel_id']}>\n"
        f"🚨 **Human Takeover Hub:** <#{SERVER_CONFIG['takeover_channel_id']}>"
    )
    await interaction.response.send_message(status_summary, ephemeral=True)

@configure.error
async def configure_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Access Denied: You need the `Manage Roles` permission to modify configurations.", ephemeral=True)

# 6. Messaging Router Pipeline Logic
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
                    await takeover_channel.send(f"💬 **[Human Claim] {message.author.name} (ID: {passenger_id}):** {message.content}")
                    return
            return

        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(message.content)
                await message.reply(reply)
                
                log_chan_id = SERVER_CONFIG["dm_log_channel_id"]
                if log_chan_id:
                    log_channel = bot.get_channel(log_chan_id)
                    if log_channel:
                        await log_channel.send(f"📬 **DM Log** | User: **{message.author.name}** (ID: `{passenger_id}`)\n**Q:** {message.content}\n**A:** {reply}")
            except Exception as e:
                await message.reply(f"⚠️ Helpdesk API Error Encountered:\n```{str(e)}```")
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
                await passenger_user.send(f"✈️ **Norwegian Airlines Staff Support ({message.author.name}):** {message.content}")
                await message.add_reaction("✅")
            except Exception as e:
                await message.channel.send(f"❌ Failed to route message to passenger DMs: {e}")
        return

    # C: HANDLING PUBLIC SERVER MENTIONS (@bot)
    if bot.user.mentioned_in(message):
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if not user_prompt:
            await message.reply("Welcome to Norwegian Airlines Customer Support! Open a private DM with me for direct assistance. 🛫")
            return

        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(user_prompt)
                await message.reply(reply)
            except Exception as e:
                await message.reply(f"⚠️ Helpdesk API Error Encountered:\n```{str(e)}```")

    await bot.process_commands(message)

# Pre-flight safety check for token variables
if not DISCORD_TOKEN:
    raise ValueError("CRITICAL ERROR: DISCORD_TOKEN is missing or completely unreadable on the settings page.")

bot.run(DISCORD_TOKEN)

