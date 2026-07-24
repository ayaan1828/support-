import os
import discord
from discord.ext import commands
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

# 1. Initialize Discord Bot Configuration
intents = discord.Intents.default()
intents.message_content = True  
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. Download and Cache the Local Independent AI Model (Runs 100% locally on CPU)
MODEL_NAME = "Qwen/Qwen2.5-1.5B-Instruct"

print("📥 Loading local AI model into server memory (this may take a few minutes on first boot)...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME, torch_dtype=torch.float32, device_map="cpu")
print("✅ Local AI engine is fully packed and ready!")

# 3. Define your Roblox Airline's System Profile
AIRLINE_KNOWLEDGE = """You are the official AI Support Agent for our Roblox aviation group. 
Answer passenger questions politely, professionally, and briefly.

OUR RULES & INFORMATION:
- Main Hub: Your Hub Airport
- Promos: Attend flights hosted by staff or pass training.
- Economy Class is free. First Class requires buying our Roblox Group Gamepass.
- Trolling or exploiting results in an instant kick or ban."""

@bot.event
async def on_ready():
    print(f"✈️ Independent Airline Bot is live on Discord as {bot.user.name}!")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if bot.user.mentioned_in(message):
        user_prompt = message.content.replace(f"<@{bot.user.id}>", "").strip()
        
        if not user_prompt:
            await message.reply("Hello! How can I assist you with your flight today? 🛫")
            return

        async with message.channel.typing():
            try:
                # Format prompt structure using the local tokenizer
                messages = [
                    {"role": "system", "content": AIRLINE_KNOWLEDGE},
                    {"role": "user", "content": user_prompt}
                ]
                text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                model_inputs = tokenizer([text], return_tensors="pt").to("cpu")

                # Generate the text locally using your server container's hardware
                with torch.no_grad():
                    generated_ids = model.generate(
                        **model_inputs,
                        max_new_tokens=150, # Keep responses short so the server panel handles it fast
                        temperature=0.7
                    )
                
                # Trim out the prompt text to fetch only the clean AI response
                generated_ids = [output_ids[len(input_ids):] for input_ids, output_ids in zip(model_inputs.input_ids, generated_ids)]
                bot_reply = tokenizer.batch_decode(generated_ids, skip_special_tokens=True)[0]

                await message.reply(bot_reply if bot_reply.strip() else "I'm processing that flight data. Could you phrase it differently?")
                
            except Exception as e:
                print(f"Local AI Error: {e}")
                await message.reply("⚠️ Server container is processing a heavy queue. Please try again in a moment.")

    await bot.process_commands(message)

bot.run(os.environ.get("DISCORD_TOKEN"))
