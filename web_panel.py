from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

CONFIG_FILE = "config.json"
WEB_PASSWORD = "ваш_пароль"

def load_config():
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)

@app.get("/", response_class=HTMLResponse)
async def panel(request: Request, password: str = ""):
    if password != WEB_PASSWORD:
        return HTMLResponse("<h2>Неверный пароль</h2>")
    config = load_config()
    return templates.TemplateResponse("panel.html", {"request": request, "config": config})

@app.post("/update", response_class=HTMLResponse)
async def update_settings(request: Request, guild_id: str = Form(...), channel_id: int = Form(...), timer: int = Form(...), password: str = Form(...)):
    if password != WEB_PASSWORD:
        return HTMLResponse("<h2>Неверный пароль</h2>")
    config = load_config()
    config["servers"][guild_id] = {"channel_id": channel_id, "timer": timer}
    save_config(config)
    return HTMLResponse("<h2>Настройки сохранены</h2><a href='/?password={0}'>Назад</a>".format(password))
