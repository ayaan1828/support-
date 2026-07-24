import os
import discord
from discord.ext import commands
import requests

intents = discord.Intents.default()
intents.message_content = True  
intents.members = True 
bot = commands.Bot(command_prefix="!", intents=intents)

# Norwegian Airlines Context Block
AIRLINE_KNOWLEDGE = """You are the official Customer Support Helpdesk Agent for Norwegian Airlines, a Roblox aviation group. Always be polite, concise, and professional. 
RULES: We operate across multiple airports. If an optional upgrade glitches, instruct the passenger to use the '!rejoin' command or reconnect. Direct Messages (DMs) are our primary support desk channel."""

def query_free_ai(user_prompt):
    """Fallback engine using a free server pipeline to avoid 400 location errors"""
    try:
        # Calls a public open-source instruction model
        api_url = "https://huggingface.co"
        headers = {"Authorization": f"Bearer {os.environ.get('HF_TOKEN', '')}"}
        
        payload = {
            "inputs": f"<|system|>\n{AIRLINE_KNOWLEDGE}\n<|user|>\n{user_prompt}\n<|assistant|>\n",
            "parameters": {"max_new_tokens": 150, "temperature": 0.7}
        }
        
        response = requests.post(api_url, headers=headers, json=payload, timeout=10)
        if response.status_code == 200:
            res_json = response.json()
            raw_text = res_json[0]['generated_text']
            # Clean out structural prompt templates if visible
            return raw_text.split("<|assistant|>\n")[-1].strip()
    except Exception as e:
        print(f"API Fetch Error: {e}")
    return "Welcome to Norwegian Airlines Customer Support! Use '!rejoin' if an item is missing, or ask your question here."

@bot.event
async def on_ready():
    print(f"✈️ Norwegian Airlines Support Bot is live as {bot.user.name}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # Handle direct message help desk tasks
    if isinstance(message.channel, discord.DMChannel):
        async with message.channel.typing():
            reply = query_free_ai(message.content)
            await message.reply(reply)
        return 

    # Handle public channel mentions
    if bot.user.mentioned_in(message):
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        if not user_prompt:
            await message.reply("Welcome to Norwegian Airlines Customer Support! Open a DM with me for private help. 🛫")
            return
        async with message.channel.typing():
            reply = query_free_ai(user_prompt)
            await message.reply(reply)

    await bot.process_commands(message)

bot.run(os.environ.get("DISCORD_TOKEN"))
