import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# 1. Initialize Discord Bot Configuration
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Safely Fetch API Credentials
# If the Fusion panel drops the key, this forces a readable visual flag
API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "").strip()

# 3. Dedicated Customer Support Profile for Norwegian Airlines
AIRLINE_KNOWLEDGE = """You are the official Customer Support Helpdesk Agent for Norwegian Airlines, an elite Roblox aviation group. 
Your primary goal is to resolve passenger issues, handle upgrade complaints, and provide flight operational info.

SUPPORT PROTOCOLS & FAQ:
- Airports: We operate across multiple airports. We fly to various destinations.
- Upgrade Glitches: If a passenger bought an optional upgrade/gamepass and it is glitching, instruct them to use the '!rejoin' command in-game. If that fails, tell them they are already in the right place and can continue messaging you here in DMs for direct support.
- Support Channel: Our direct customer support helpdesk is handled entirely here through Direct Messages (DMs). Passengers can message the bot anytime for private assistance.
- Flight Schedules: We announce upcoming flights in our server's announcement channels. Advise users to check pinned messages there. Do not guess or make up flight times."""

async def generate_ai_reply(user_prompt):
    """Helper function to run text generation through Gemini Cloud"""
    if not API_KEY:
        return "⚠️ Configuration Error: The server's 'GEMINI_API_KEY' environment variable is empty. Please verify your keys in the Fusion Panel."
        
    ai_client = genai.Client(api_key=API_KEY)
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=AIRLINE_KNOWLEDGE,
            temperature=0.7
        )
    )
    return response.text if response.text else "I am processing flight data. Could you please rephrase your request?"

@bot.event
async def on_ready():
    print(f"✈️ Norwegian Airlines Support Bot is active as {bot.user.name}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # HANDLE DIRECT MESSAGES
    if isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(message.content)
                await message.reply(reply)
            except Exception as e:
                # Forces the real system error to print straight into the Discord chat for debugging
                await message.reply(f"⚠️ API Error Encountered:\n```{str(e)}```")
        return 

    # HANDLE PUBLIC SERVER MENTIONS
    if bot.user.mentioned_in(message):
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if not user_prompt:
            await message.reply("Welcome to Norwegian Airlines Customer Support! Open a DM with me for private help. 🛫")
            return

        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(user_prompt)
                await message.reply(reply)
            except Exception as e:
                await message.reply(f"⚠️ API Error Encountered:\n```{str(e)}```")

    await bot.process_commands(message)

# Force runtime crash if the token is completely missing
if not DISCORD_TOKEN:
    raise ValueError("CRITICAL: DISCORD_TOKEN variable is completely empty or missing from your settings page.")

bot.run(DISCORD_TOKEN)
