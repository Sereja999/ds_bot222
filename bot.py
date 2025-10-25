import discord
from discord.ext import commands
import asyncio
from datetime import datetime
import os
from flask import Flask
from threading import Thread
import requests

# Flask app для поддержания активности
app = Flask('')

@app.route('/')
def home():
    return "✅ Бот активен! Команды: /на_пост, /выгнать, /помощь"

@app.route('/health')
def health():
    return "OK"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

# Запускаем веб-сервер
keep_alive()

# Настройка бота
intents = discord.Intents.default()
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

# Переменные для хранения состояния
is_in_channel = False
start_time = None
current_voice_channel = None

@bot.event
async def on_ready():
    print(f'🎯 Бот {bot.user.name} успешно запущен!')
    print(f'🎯 ID бота: {bot.user.id}')
    print('🔧 Синхронизация слеш-команд...')
    
    try:
        synced = await bot.tree.sync()
        print(f'✅ Успешно синхронизировано {len(synced)} команд:')
        for cmd in synced:
            print(f'   - /{cmd.name}')
    except Exception as e:
        print(f'❌ Ошибка синхронизации команд: {e}')
    
    await bot.change_presence(activity=discord.Game(name="Отдыхает"))
    print('🚀 Бот готов к работе!')

@bot.tree.command(name="на_пост", description="Заступить на пост в голосовом канале")
async def join_channel(interaction: discord.Interaction):
    print(f'🔔 Команда /на_пост вызвана пользователем {interaction.user.name}')
    
    global is_in_channel, start_time, current_voice_channel
    
    if interaction.user.voice is None:
        await interaction.response.send_message("❌ Вы должны находиться в голосовом канале!", ephemeral=True)
        return
    
    if is_in_channel:
        await interaction.response.send_message("❌ Бот уже находится на посту в другом канале!", ephemeral=True)
        return
    
    voice_channel = interaction.user.voice.channel
    
    try:
        print(f'🔗 Подключаюсь к каналу: {voice_channel.name}')
        voice_client = await voice_channel.connect()
        current_voice_channel = voice_client
        is_in_channel = True
        start_time = datetime.now()
        
        await bot.change_presence(activity=discord.Game(name="На посту"))
        bot.loop.create_task(update_presence_time())
        
        await interaction.response.send_message(f"✅ Бот заступил на пост в канале {voice_channel.name}!")
        print('✅ Успешно подключился к голосовому каналу')
        
    except Exception as e:
        error_msg = f"❌ Произошла ошибка при подключении: {str(e)}"
        await interaction.response.send_message(error_msg, ephemeral=True)
        print(f'❌ Ошибка подключения: {e}')

@bot.tree.command(name="выгнать", description="Завершить пост и показать статистику")
async def leave_channel(interaction: discord.Interaction):
    print(f'🔔 Команда /выгнать вызвана пользователем {interaction.user.name}')
    
    global is_in_channel, start_time, current_voice_channel
    
    if not is_in_channel:
        await interaction.response.send_message("❌ Бот не находится на посту!", ephemeral=True)
        return
    
    end_time = datetime.now()
    time_spent = end_time - start_time
    
    hours, remainder = divmod(time_spent.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    time_str = f"{int(hours)}ч {int(minutes)}м {int(seconds)}с"
    
    try:
        if current_voice_channel:
            await current_voice_channel.disconnect()
            print('🔌 Отключился от голосового канала')
        
        is_in_channel = False
        current_voice_channel = None
        
        await bot.change_presence(activity=discord.Game(name="Отдыхает"))
        
        embed = discord.Embed(
            title="📊 Сводка о времени на посту",
            color=0x00ff00,
            timestamp=end_time
        )
        embed.add_field(name="⏱️ Общее время", value=time_str, inline=False)
        embed.add_field(name="🕐 Начало смены", value=start_time.strftime("%H:%M:%S"), inline=True)
        embed.add_field(name="🕐 Конец смены", value=end_time.strftime("%H:%M:%S"), inline=True)
        embed.add_field(name="📅 Дата", value=start_time.strftime("%d.%m.%Y"), inline=False)
        
        await interaction.response.send_message(embed=embed)
        print('📊 Отправил статистику времени')
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Произошла ошибка при отключении: {str(e)}", ephemeral=True)
        print(f'❌ Ошибка отключения: {e}')

@bot.tree.command(name="помощь", description="Показать все доступные команды")
async def help_command(interaction: discord.Interaction):
    print(f'🔔 Команда /помощь вызвана пользователем {interaction.user.name}')
    
    embed = discord.Embed(
        title="📋 Доступные команды",
        color=0x0099ff
    )
    
    embed.add_field(name="/на_пост", value="Заступить на пост в вашем голосовом канале", inline=False)
    embed.add_field(name="/выгнать", value="Завершить пост и посмотреть статистику", inline=False)
    embed.add_field(name="/помощь", value="Показать это сообщение", inline=False)
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    print('📋 Отправил справку по командам')

async def update_presence_time():
    global is_in_channel, start_time
    
    while is_in_channel:
        try:
            current_time = datetime.now()
            time_spent = current_time - start_time
            
            hours, remainder = divmod(time_spent.total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            
            if hours > 0:
                time_str = f"На посту: {int(hours)}ч {int(minutes)}м"
            elif minutes > 0:
                time_str = f"На посту: {int(minutes)}м {int(seconds)}с"
            else:
                time_str = f"На посту: {int(seconds)}с"
            
            await bot.change_presence(activity=discord.Game(name=time_str))
            await asyncio.sleep(10)
            
        except Exception as e:
            print(f"⚠️ Ошибка при обновлении статуса: {e}")
            break

# Запуск бота
print('🔧 Запускаю бота...')
TOKEN = os.environ['DISCORD_TOKEN']
bot.run(TOKEN)
