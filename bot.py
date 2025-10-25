import discord
from discord.ext import commands, tasks
import json
from datetime import datetime, timedelta

TOKEN = "ВАШ_ТОКЕН_БОТА"

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="/", intents=intents)

CONFIG_FILE = "config.json"
SESSIONS_FILE = "sessions.json"
active_sessions = {}

# ======== Функции для работы с файлами ========
def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

def load_sessions():
    with open(SESSIONS_FILE, "r") as f:
        return json.load(f)

def save_sessions(sessions):
    with open(SESSIONS_FILE, "w") as f:
        json.dump(sessions, f, indent=4)

# ======== Проверка прав доступа ========
def is_admin(ctx):
    config = load_config()
    return ctx.author.guild_permissions.administrator or ctx.author.id in config["allowed_admins"]

# ======== Команды бота ========
@bot.slash_command(name="настройки", description="Настройка бота (только для админов)")
async def settings(ctx):
    if not is_admin(ctx):
        await ctx.respond("У вас нет доступа к настройкам.", ephemeral=True)
        return

    config = load_config()
    guild_id = str(ctx.guild.id)
    guild_config = config["servers"].get(guild_id, {"channel_id": None, "timer": 10})
    await ctx.respond(
        f"Текущий канал: {guild_config['channel_id']}\nТаймер (минут): {guild_config['timer']}"
    )

@bot.slash_command(name="на_пост", description="Бот заходит в канал")
async def na_post(ctx):
    config = load_config()
    guild_id = str(ctx.guild.id)
    guild_config = config["servers"].get(guild_id)

    if not guild_config or not guild_config.get("channel_id"):
        await ctx.respond("Канал для бота не настроен. Используйте /настройки.", ephemeral=True)
        return

    channel = ctx.guild.get_channel(guild_config["channel_id"])
    if not channel:
        await ctx.respond("Канал не найден.", ephemeral=True)
        return

    if guild_id in active_sessions:
        await ctx.respond("Бот уже находится в канале.", ephemeral=True)
        return

    vc = await channel.connect()
    start_time = datetime.now()
    timer_minutes = guild_config.get("timer", 10)
    end_time = start_time + timedelta(minutes=timer_minutes)

    active_sessions[guild_id] = {
        "vc": vc,
        "start": start_time,
        "end": end_time,
        "user": ctx.author.name,
        "reason": "таймер"
    }

    await ctx.respond(f"Бот зашел в канал {channel.name}. Таймер: {timer_minutes} минут.")

@bot.slash_command(name="выгнать", description="Бот покидает канал")
async def kick(ctx):
    guild_id = str(ctx.guild.id)
    session = active_sessions.get(guild_id)
    if not session:
        await ctx.respond("Бот сейчас не в канале.", ephemeral=True)
        return

    vc = session["vc"]
    await vc.disconnect()

    end_time = datetime.now()
    duration = end_time - session["start"]

    # Сохраняем сессию в лог
    sessions = load_sessions()
    sessions.append({
        "guild_id": guild_id,
        "channel_id": session["vc"].channel.id,
        "user_started": session["user"],
        "start_time": session["start"].isoformat(),
        "end_time": end_time.isoformat(),
        "duration": str(duration),
        "exit_reason": f"команда {ctx.author.name}"
    })
    save_sessions(sessions)

    await ctx.send(f"Бот покинул канал. Время сессии: {duration}. Причина: команда {ctx.author.name}")
    del active_sessions[guild_id]

# ======== Таймер выхода ========
@tasks.loop(seconds=10)
async def check_sessions():
    for guild_id, session in list(active_sessions.items()):
        if datetime.now() >= session["end"]:
            vc = session["vc"]
            await vc.disconnect()
            duration = datetime.now() - session["start"]

            # Сохраняем сессию
            sessions = load_sessions()
            sessions.append({
                "guild_id": guild_id,
                "channel_id": vc.channel.id,
                "user_started": session["user"],
                "start_time": session["start"].isoformat(),
                "end_time": datetime.now().isoformat(),
                "duration": str(duration),
                "exit_reason": "таймер истек"
            })
            save_sessions(sessions)

            guild = bot.get_guild(int(guild_id))
            if guild.text_channels:
                await guild.text_channels[0].send(
                    f"Бот покинул канал (таймер истек). Время сессии: {duration}"
                )
            del active_sessions[guild_id]

check_sessions.start()

bot.run(TOKEN)
