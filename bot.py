import os
import discord
from discord.ext import commands
from google import genai
from google.genai import types

# 1. Initialize Discord Bot Configuration
intents = discord.Intents.default()
intents.message_content = True  
intents.members = True # Essential to handle incoming Direct Messages smoothly
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Connects to the cloud AI engine using your environment variable
ai_client = genai.Client()

# 3. Dedicated Customer Support Profile for Norwegian Airlines
AIRLINE_KNOWLEDGE = """You are the official Customer Support Helpdesk Agent for Norwegian Airlines, an elite Roblox aviation group. 
Your primary goal is to resolve passenger issues, handle upgrade complaints, and provide flight operational info.

SUPPORT PROTOCOLS & FAQ:
- Airports: We operate across multiple airports. Do not list just one single hub. We fly to various destinations.
- Upgrade Glitches: If a passenger bought an optional upgrade/gamepass and it is glitching, instruct them to use the '!rejoin' command in-game or reconnect to the Roblox server. If that fails, tell them they are already in the right place and can continue messaging you here in DMs for direct support.
- Support Channel: Our direct customer support helpdesk is handled entirely here through Direct Messages (DMs). Passengers can message the bot anytime for private assistance.
- Flight Schedules: We announce upcoming flights in our server's announcement channels. Advise users to check pinned messages there. Do not guess or make up flight times.
- Exploiter / Troller Reports: Direct passengers to report disruptions to our active moderation team or open a claim. Do not attempt to issue punishments yourself.
- Staff Promotions: To join the Norwegian Airlines crew or earn promotions, passengers must attend official training sessions announced ahead of time in the Discord server.

TONE GUIDELINES:
- Act like an elite airport concierge helpdesk. Always be exceptionally polite, helpful, empathetic, and professional. 
- Keep answers concise, clear, and direct so players can read them easily on mobile or PC while playing Roblox."""

async def generate_ai_reply(user_prompt):
    """Helper function to run text generation through Gemini Cloud"""
    response = ai_client.models.generate_content(
        model='gemini-2.5-flash',
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=AIRLINE_KNOWLEDGE,
            temperature=0.7
        )
    )
    return response.text if response.text else "I am currently processing flight data. Could you please rephrase your request?"

@bot.event
async def on_ready():
    print(f"✈️ Norwegian Airlines Support Bot is live on Discord as {bot.user.name}!")

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
                print(f"Cloud DM AI Error: {e}")
                await message.reply("⚠️ Our support server container is handling a heavy queue. Please try your request again in a moment.")
        return 

    # HANDLE PUBLIC SERVER MENTIONS
    if bot.user.mentioned_in(message):
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if not user_prompt:
            await message.reply("Welcome to Norwegian Airlines Customer Support! Open a DM with me for private help, or ask your question here. 🛫")
            return

        async with message.channel.typing():
            try:
                reply = await generate_ai_reply(user_prompt)
                await message.reply(reply)
            except Exception as e:
                print(f"Cloud Server AI Error: {e}")
                await message.reply("⚠️ Our support server container is handling a heavy queue. Please try your request again in a moment.")

    await bot.process_commands(message)

bot.run(os.environ.get("DISCORD_TOKEN"))
