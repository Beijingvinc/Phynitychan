import os
import json
import time
import re
import random
from datetime import datetime
from flask import Flask, request, render_template_string, redirect, url_for, session, abort

app = Flask(__name__)
app.secret_key = 'phynitychan' #change secret key
app.config['UPLOAD_FOLDER'] = os.path.join('data', 'src')

DATA_DIR = 'data'
BOARDS_FILE = os.path.join(DATA_DIR, 'boards.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
SETTINGS_FILE = os.path.join(DATA_DIR, 'global_settings.json')

for path in [DATA_DIR, app.config['UPLOAD_FOLDER']]:
    if not os.path.exists(path):
        os.makedirs(path)

def load_json(filepath, default):
    if not os.path.exists(filepath):
        with open(filepath, 'w') as f:
            json.dump(default, f, indent=4)
        return default
    with open(filepath, 'r') as f:
        return json.load(f)

def save_json(filepath, data):
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

LANGUAGES = {
    "en": {
        "home": "Home", "user_panel": "User Panel / Registration", "admin": "Global Admin",
        "welcome": "Welcome to Phynitychan!", "desc": "Create your own imageboard or textboard instantly.",
        "active_boards": "Active Boards Across the Network", "board_type": "Board Type",
        "created_by": "Created by", "login_reg": "Login / Register", "username": "Username",
        "password": "Password", "btn_login": "Login", "btn_register": "Register",
        "create_new_board": "Create a New Board", "board_uri_placeholder": "uri (e.g., tech)",
        "board_title_placeholder": "Board Title", "btn_create": "Create Board", "my_boards": "My Managed Boards",
        "manage": "Manage", "banned_msg": "You are BANNED.", "name": "Name", "subject": "Subject",
        "message": "Message", "file": "File", "btn_submit_thread": "Submit Thread", "btn_reply": "Reply",
        "back_to_board": "Back to Board", "global_notice": "Global Notice", "site_name": "Site Name",
        "max_size": "Max File Size", "save_settings": "Save Settings", "delete_board": "Delete Board",
        "global_bans": "Global Ban List", "ban_btn": "Ban", "delete_btn": "Delete", "anonymous": "Anonymous",
        "new_thread": "New thread", "all_threads": "All threads", "back_to_index": "Back to index",
        "secret": "Secret (Hidden from list)", "password_protected": "Password Protected", "board_password": "Board Password"
    },
    "es": {
        "home": "Inicio", "user_panel": "Panel de Usuario", "admin": "Admin Global",
        "welcome": "¡Bienvenido a Phynitychan!", "desc": "Crea tu propio tablón de imágenes o texto al instante.",
        "active_boards": "Tablones Activos en la Red", "board_type": "Tipo de Tablón",
        "created_by": "Creado por", "login_reg": "Acceso / Registro", "username": "Usuario",
        "password": "Contraseña", "btn_login": "Entrar", "btn_register": "Registrarse",
        "create_new_board": "Crear un Nuevo Tablón", "board_uri_placeholder": "uri (ej: ciber)",
        "board_title_placeholder": "Título del Tablón", "btn_create": "Crear Tablón", "my_boards": "Mis Tablones",
        "manage": "Moderar", "banned_msg": "Estás BANEADO.", "name": "Nombre", "subject": "Tema",
        "message": "Mensaje", "file": "Archivo", "btn_submit_thread": "Enviar Hilo", "btn_reply": "Responder",
        "back_to_board": "Volver al Tablón", "global_notice": "Anuncio Global", "site_name": "Nombre del Sitio",
        "max_size": "Tamaño Máximo", "save_settings": "Guardar Ajustes", "delete_board": "Eliminar Tablón",
        "global_bans": "Lista de Baneos Globales", "ban_btn": "Banear", "delete_btn": "Borrar", "anonymous": "Anónimo",
        "new_thread": "Nuevo hilo", "all_threads": "Todos los hilos", "back_to_index": "Volver al índice",
        "secret": "Secreto (Ocultar de la lista)", "password_protected": "Proteger con Contraseña", "board_password": "Contraseña del Tablón"
    }
}

DEFAULT_SETTINGS = {
    "site_name": "Phynitychan",
    "global_notice": "Welcome to the custom imageboard & textboard platform!",
    "max_file_size_mb": 50,
    "global_bans": [],
    "language": "en"
}
global_config = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
app.config['MAX_CONTENT_LENGTH'] = global_config.get("max_file_size_mb", 50) * 1024 * 1024

def t(key):
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    lang = cfg.get("language", "en")
    return LANGUAGES.get(lang, LANGUAGES["en"]).get(key, key)

def parse_culture_formatting(text):
    if not text:
        return ""
    html_escaped = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    url_pattern = r'(https?://[^\s<>"]+)'
    html_escaped = re.sub(url_pattern, r'<a href="\1" target="_blank" rel="noopener noreferrer">\1</a>', html_escaped)
    lines = html_escaped.split("\n")
    processed_lines = []
    for line in lines:
        if line.startswith("&gt;&gt;"):
            line = f'<span class="greentext">{line}</span>'
        else:
            line = re.sub(r'(&gt;&gt;[^\n]+)', r'<span class="greentext">\1</span>', line)
        line = re.sub(r'(?<!&gt;)&gt;(\d+)', r'<a href="#p\1" class="quotelink">&gt;\1</a>', line)
        processed_lines.append(line)
    return "<br>".join(processed_lines)

app.jinja_env.filters['chan_format'] = parse_culture_formatting

def is_video_file(filename):
    if not filename: return False
    ext = os.path.splitext(filename)[1].lower()
    return ext in ['.mp4', '.webm']

app.jinja_env.filters['is_video'] = is_video_file

BASE_HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{{ settings.site_name }}</title>
    
    {% if not is_textboard %}
    <style>
        body.default-img-body { background-color: #FFFFEE; color: #800000; font-family: arial,helvetica,sans-serif; font-size: 10pt; margin: 0; padding: 10px; text-align: left; }
        .top-bar { font-size: 9pt; font-family: sans-serif; text-align: left; margin-bottom: 5px; color: #800000; }
        .top-bar a, .navbar-boards a { color: #34345C; text-decoration: none; font-weight: bold; }
        .top-bar a:hover, .navbar-boards a:hover { color: #ff0000; }
        .navbar-boards { text-align: center; font-size: 9pt; font-family: sans-serif; margin-bottom: 15px; border-bottom: 1px dashed #D9BFB7; padding-bottom: 8px; width: 100%; }
        .global-notice { background-color: #F0E0D6; border: 1px solid #E04000; max-width: 800px; margin: 10px auto; padding: 8px; text-align: center; font-size: 10pt; font-weight: bold; color: #800000; }
        .box { background-color: #F0E0D6; border: 1px solid #D9BFB7; max-width: 800px; margin: 15px auto; padding: 10px; text-align: center; font-family: sans-serif; color: #800000; }
        .box-title { background-color: #E04000; color: white; font-weight: bold; padding: 4px; margin: -10px -10px 10px -10px; font-size: 11pt; }
        
        table.post-form { margin: 0 auto !important; border-spacing: 1px; border-collapse: separate; background-color: transparent; text-align: left; width: auto; font-family: arial,helvetica,sans-serif; }
        table.post-form td { padding: 0px; border: none; text-align: left; color: #000; vertical-align: middle; }
        .form-label { background-color: #E08060; color: #800000; font-weight: bold; font-size: 10pt; width: 85px; padding: 3px 5px !important; border: 1px solid #FFFFEE !important; }
        .form-value { background-color: #FFFFEE; padding: 2px 4px !important; }
        .form-value input[type="text"], .form-value textarea { border: 1px solid #A9A9A9; font-family: monospace; font-size: 10pt; padding: 1px; box-sizing: border-box; }
        .form-value input[type="text"] { width: 324px; height: 22px; }
        .form-value textarea { width: 485px; height: 90px; resize: both; vertical-align: bottom; }
        .form-value input[type="submit"] { height: 22px; margin-left: 4px; font-family: sans-serif; font-size: 9pt; background-color: #ECE9D8; border: 1px solid #7F9DB9; color: black; cursor: pointer; padding: 0 6px; }
        .form-rules-box { max-width: 580px; margin: 6px auto 12px auto; text-align: left; font-size: 8.5pt; color: #555; font-family: sans-serif; line-height: 1.4; padding-left: 10px; }
        .form-rules-box ul { margin: 0; padding-left: 15px; list-style-type: disc; }
        .form-rules-box li { margin-bottom: 2px; }
        
        .thread { margin-top: 15px; text-align: left !important; clear: both; display: block; width: 100%; }
        .op-post { margin-bottom: 8px; display: block; text-align: left !important; width: 100%; }
        .file-meta { font-size: 8pt; color: #444; margin-bottom: 2px; }
        .file-meta a { color: #34345C; }
        .reply-container { clear: both; display: block; text-align: left !important; width: 100%; margin: 4px 0; }
        .reply-post { background-color: #F0E0D6; border: 1px solid #D9BFB7; display: table !important; padding: 6px 10px; margin: 0 0 0 20px !important; text-align: left !important; box-sizing: border-box; }
        .post-info { font-size: 9pt; color: #444; margin-bottom: 3px; text-align: left !important; }
        .subject { color: #0F0C5D; font-weight: bold; }
        .poster-name { color: #117743; font-weight: bold; }
        .post-message { font-size: 10pt; word-wrap: break-word; margin-top: 4px; color: #800000; text-align: left !important; font-family: arial,helvetica,sans-serif; }
        .post-message a { color: #34345C; text-decoration: underline; }
        .post-message a:hover { color: #ff0000; }
        .greentext { color: #789922 !important; font-family: monospace; font-size: 10.5pt; }
        .quotelink { color: #DD0000 !important; text-decoration: underline; font-weight: normal; }
        .quotelink:hover { color: #FF0000 !important; }
        .thumb { float: left; margin: 2px 20px 10px 2px; max-width: 150px; max-height: 150px; }
        .media-reply { max-width: 200px; max-height: 200px; display: block; margin: 4px 0; }
        .mod-actions { background-color: #F8D7DA; padding: 2px 5px; font-size: 8pt; border: 1px solid #F5C6CB; margin-left: 10px; display: inline-block; color: #000; }
    </style>
    {% else %}
    <style>
        .top-bar { background-color: transparent; padding: 5px; font-size: 9pt; font-family: sans-serif; }
        .navbar-boards { text-align: center; font-size: 9pt; font-family: sans-serif; margin-bottom: 15px; padding-bottom: 8px; }
        html { padding: 0px; margin: 0px; }
        body { padding: 8px; margin: 0px; }
        body.mainpage { background: #C5AD99; background-image: url(https://parts.jbbs.shitaraba.net/skin/0000/ba.gif); color: #000080; }
        body.threadpage { background: #EFEFEF; color: #000000; }
        body.backlogpage { background: #FFFFFF; color: #000000; }
        a { color: #0000FF; text-decoration: none; }
        a:visited { color: #660099; }
        a:hover { color: #FF0000; }
        form { margin: 0px; }
        .replytext { margin: 0.5em 0em 0em 3em; line-height: 1.2; }
        .outerbox { background: #CCFFCC; border: 1px outset white; padding: 7px; margin-bottom: 1em; margin-left: 2.5%; margin-right: 2.5%; clear: both; }
        .innerbox { border: 1px inset white; padding: 6px; }
        #titlebox h1 { font-size: 1.5em; font-weight: normal; padding: 0px; margin: 0px; }
        #titlebox { position: relative; }
        #titlebox .threadnavigation { position: absolute; right: 2.5%; padding-right: 20px; top: 12px; }
        body.threadpage #threads, body.mainpage #threads { margin-left: 2.5%; margin-right: 2.5%; background: #CCFFCC; padding: 7px; margin-bottom: 2em; border: 1px outset white; clear: both; }
        body.threadpage #threadlist { background: #CCFFCC; font-family: serif; margin: 0px 0px 7px 0px; padding: 6px; border-left: 1px inset white; border-right: 1px inset white; border-bottom: 1px inset white; }
        .mainpage #posts .thread { margin-left: 2.5%; margin-right: 2.5%; position: relative; background: #EFEFEF; border: 1px outset white; padding: 7px; margin-bottom: 2em; clear: both; }
        .mainpage #posts h2 { color: #FF0000; font-size: 1.5em; font-weight: bold; margin: 0px 0px -1px 0px; padding: 1em 0em 0em 0.3em; border-top: 1px inset white; border-left: 1px inset white; border-right: 1px inset white; }
        .threadpage #posts h2 { color: red; font-size: 1.2em; font-weight: normal; border-top: 2px ridge white; margin: 1em 0 0 0; padding: 0em 0em 0.5em 0em; }
        #posts .reply { clear: both; margin: 0px 0px 0.5em 0px; }
        #posts h3 { font-size: 1em; font-weight: normal; margin: 0px; padding: 0px; }
        .mainpage #posts h3 .postername { color: red; font-weight: bold; }
        .threadpage #posts h3 .postername { color: green; font-weight: bold; }
        #posts form { clear: both; background: #EFEFEF; font-family: serif; margin: 0; }
        .mainpage #posts form { padding: 6px 6px 1em 6px; border-left: 1px inset white; border-right: 1px inset white; border-bottom: 1px inset white; }
        #footer { text-align: center; font-size: 0.8em; }
        .greentext { color: #789922 !important; font-family: monospace; }
        .quotelink { color: #DD0000 !important; text-decoration: underline; }
    </style>
    {% endif %}
    {% if current_board_css %}<style>{{ current_board_css | safe }}</style>{% endif %}
</head>
<body class="{% if is_textboard %}{{ textboard_class }}{% else %}default-img-body{% endif %}">
    <div class="top-bar">
        [<a href="/">{{ trans('home') }}</a>] [<a href="/login">{{ trans('user_panel') }}</a>]
    </div>
    <div class="navbar-boards">
        {% for b_uri, b_meta in boards.items() %}
            {% if not b_meta.is_secret %}
                /<a href="/board/{{ b_uri }}">{{ b_uri }}</a>/ - 
            {% endif %}
        {% endfor %}
    </div>

    {% if custom_notice %}
    <div class="global-notice" style="background-color: #E2F0D6; border-color: #40A000;">{{ custom_notice }}</div>
    {% elif settings.global_notice and not is_textboard %}
    <div class="global-notice">{{ settings.global_notice }}</div>
    {% endif %}

    {% block content %}{% endblock %}
</body>
</html>
"""

def check_banned(uri=None):
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    ip = request.remote_addr
    if ip in cfg.get("global_bans", []):
        abort(403, description=t('banned_msg') + f" IP: {ip}")
    if uri:
        boards = load_json(BOARDS_FILE, {})
        if uri in boards and ip in boards[uri].get("bans", []):
            abort(403, description=t('banned_msg') + f" IP: {ip}")

def get_captcha():
    n1, n2 = random.randint(1, 9), random.randint(1, 9)
    session['captcha_ans'] = n1 + n2
    return f"{n1} + {n2}"

def check_password_auth(uri, board_data):
    if board_data.get('is_protected') and board_data.get('password'):
        auth_key = f"auth_{uri}"
        if session.get(auth_key) != board_data['password']:
            return False
    return True

@app.route('/')
def home():
    check_banned()
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    
    html = """
    {% extends "base" %}
    {% block content %}
    <div class="box" style="margin-top: 30px;">
        <div class="box-title">∞ {{ settings.site_name }}</div>
        <p>{{ trans('desc') }}</p>
    </div>
    <div class="box">
        <div class="box-title">{{ trans('active_boards') }}</div>
        <ul style="text-align: left; display: inline-block; line-height: 1.8; list-style-type: square; margin: 10px;">
        {% for uri, data in boards.items() %}
            {% if not data.is_secret %}
            <li>
                <a href="/board/{{ uri }}" style="font-size: 11pt; font-weight: bold;">/{{ uri }}/ - {{ data.title }}</a> 
                <span style="font-size:9pt; color:#555;">[{{ data.type | upper }}] ({{ trans('created_by') }}: <b>{{ data.owner }}</b>)</span>
                {% if data.is_protected %}<span style="color:red; font-size:8pt; font-weight:bold;">[🔒 Private]</span>{% endif %}
            </li>
            {% endif %}
        {% endfor %}
        </ul>
    </div>
    {% endblock %}
    """
    return render_template_string(html, boards=boards, settings=cfg, trans=t, is_textboard=False)

@app.route('/login', methods=['GET', 'POST'])
def login():
    check_banned()
    users = load_json(USERS_FILE, {})
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    error = None

    if request.method == 'POST':
        action = request.form.get('action')
        username = request.form.get('username').strip()
        password = request.form.get('password')

        if action == 'register':
            if username in users: error = "User already exists."
            elif not username or not password: error = "Fields cannot be blank."
            else:
                users[username] = password
                save_json(USERS_FILE, users)
                session['user'] = username
                return redirect(url_for('user_panel'))
        elif action == 'login':
            if users.get(username) == password:
                session['user'] = username
                return redirect(url_for('user_panel'))
            else: error = "Invalid credentials."

    html = """
    {% extends "base" %}
    {% block content %}
    <div class="box" style="max-width: 400px;">
        <div class="box-title">{{ trans('login_reg') }}</div>
        {% if error %}<p style="color:red; font-weight:bold;">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="username" placeholder="{{ trans('username') }}" style="width:80%; margin-bottom:8px;" required><br>
            <input type="password" name="password" placeholder="{{ trans('password') }}" style="width:80%; margin-bottom:12px;" required><br>
            <button type="submit" name="action" value="login">{{ trans('btn_login') }}</button>
            <button type="submit" name="action" value="register">{{ trans('btn_register') }}</button>
        </form>
    </div>
    {% endblock %}
    """
    return render_template_string(html, boards=boards, error=error, settings=cfg, trans=t, is_textboard=False)

@app.route('/user_panel', methods=['GET', 'POST'])
def user_panel():
    if 'user' not in session: return redirect(url_for('login'))
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    username = session['user']
    error = None

    if request.method == 'POST':
        board_uri = request.form.get('uri').strip().lower()
        board_title = request.form.get('title').strip()
        board_type = request.form.get('type')
        is_secret = True if request.form.get('is_secret') else False
        is_protected = True if request.form.get('is_protected') else False
        board_password = request.form.get('board_password','').strip()

        if not board_uri.isalnum():
            error = "URI must contain only alphanumeric characters."
        elif board_uri in boards:
            error = "That board URI is already taken."
        else:
            boards[board_uri] = {
                "title": board_title,
                "owner": username,
                "type": board_type,
                "css": "",
                "banner_url": "",
                "custom_notice": "",
                "is_secret": is_secret,
                "is_protected": is_protected,
                "password": board_password,
                "bans": [],
                "threads": []
            }
            save_json(BOARDS_FILE, boards)

    html = """
    {% extends "base" %}
    {% block content %}
    <div class="box">
        <div class="box-title">{{ username }}'s Control Station | [<a href="/logout" style="color:white;">Logout</a>]</div>
        <h3>{{ trans('create_new_board') }}</h3>
        {% if error %}<p style="color:red;">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="text" name="uri" placeholder="{{ trans('board_uri_placeholder') }}" required><br><br>
            <input type="text" name="title" placeholder="{{ trans('board_title_placeholder') }}" required><br><br>
            <select name="type">
                <option value="imgboard">Imageboard (Normal)</option>
                <option value="textboard">Textboard (Kareha Style)</option>
            </select><br><br>
            <label><input type="checkbox" name="is_secret"> {{ trans('secret') }}</label><br>
            <label><input type="checkbox" name="is_protected"> {{ trans('password_protected') }}</label><br>
            <input type="text" name="board_password" placeholder="{{ trans('board_password') }}"><br><br>
            <button type="submit">{{ trans('btn_create') }}</button>
        </form>
        <hr style="border-color:#D9BFB7; margin:15px 0;">
        <h3>{{ trans('my_boards') }}</h3>
        <table style="width:100%; text-align:left; background: #FFFEEF; border: 1px solid #D9BFB7; padding: 10px;">
        {% for uri, data in boards.items() %}
            {% if data.owner == username %}
                <tr>
                    <td>
                        <b>/{{ uri }}/ - {{ data.title }}</b> ({{ data.type }})
                        {% if data.is_secret %}<span style="color:gray;">[Secret]</span>{% endif %}
                        {% if data.is_protected %}<span style="color:red;">[🔒 Password]</span>{% endif %}
                    </td>
                    <td style="text-align:right;">
                        [<a href="/board/{{ uri }}">View</a>] 
                        [<a href="/board/{{ uri }}/manage" style="color:#AF0A0F;">{{ trans('manage') }}</a>]
                    </td>
                </tr>
            {% endif %}
        {% endfor %}
        </table>
    </div>
    {% endblock %}
    """
    return render_template_string(html, boards=boards, username=username, error=error, settings=cfg, trans=t, is_textboard=False)

@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

@app.route('/board/<uri>/manage', methods=['GET', 'POST'])
def manage_board(uri):
    if 'user' not in session: return redirect(url_for('login'))
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if uri not in boards: return "Not Found", 404
    board_data = boards[uri]
    if board_data['owner'] != session['user']: return "Forbidden", 403

    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'update_settings':
            board_data['banner_url'] = request.form.get('banner_url')
            board_data['custom_notice'] = request.form.get('custom_notice').strip()
            board_data['css'] = request.form.get('css')
            board_data['is_secret'] = True if request.form.get('is_secret') else False
            board_data['is_protected'] = True if request.form.get('is_protected') else False
            board_data['password'] = request.form.get('board_password','').strip()
        elif action == 'add_ban':
            target_ip = request.form.get('ip').strip()
            if target_ip and target_ip not in board_data['bans']: board_data['bans'].append(target_ip)
        elif action == 'remove_ban':
            target_ip = request.form.get('ip').strip()
            if target_ip in board_data['bans']: board_data['bans'].remove(target_ip)
        save_json(BOARDS_FILE, boards)

    html = """
    {% extends "base" %}
    {% block content %}
    <div class="box">
        <div class="box-title">Mod Station /{{ uri }}/</div>
        <p><a href="/user_panel">⬅ Back to Dashboard</a></p>
        <form method="POST">
            <input type="hidden" name="action" value="update_settings">
            <h4>Banner URL</h4>
            <input type="text" name="banner_url" value="{{ board.banner_url }}" style="width:90%;"><br>
            
            <h4>Custom Welcome Notice (Board Exclusive)</h4>
            <textarea name="custom_notice" rows="3" style="width:95%;">{{ board.custom_notice if board.custom_notice is defined else '' }}</textarea><br>
            
            <h4>Privacy Options</h4>
            <label><input type="checkbox" name="is_secret" {% if board.is_secret %}checked{% endif %}> Hide board from public index (Secret)</label><br>
            <label><input type="checkbox" name="is_protected" {% if board.is_protected %}checked{% endif %}> Require password authentication to view</label><br>
            <input type="text" name="board_password" placeholder="New Password" value="{{ board.password if board.password is defined else '' }}"><br>

            <h4>Custom CSS Overrides</h4>
            <textarea name="css" rows="6" style="width:95%; font-family:monospace;">{{ board.css }}</textarea><br><br>
            
            <button type="submit">Save Configurations</button>
        </form>
        <hr style="border-color:#D9BFB7; margin:20px 0;">
        <h3>Ban IP on /{{ uri }}/</h3>
        <form method="POST">
            <input type="hidden" name="action" value="add_ban"><input type="text" name="ip" required>
            <button type="submit">Ban IP</button>
        </form>
        <ul>
            {% for ip in board.bans %}
            <li>{{ ip }} - <form method="POST" style="display:inline;"><input type="hidden" name="action" value="remove_ban"><input type="hidden" name="ip" value="{{ ip }}"><button type="submit">Unban</button></form></li>
            {% endfor %}
        </ul>
    </div>
    {% endblock %}
    """
    return render_template_string(html, boards=boards, uri=uri, board=board_data, settings=cfg, trans=t, is_textboard=False)

@app.route('/board/<uri>/auth', methods=['GET', 'POST'])
def board_auth(uri):
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if uri not in boards: return "Not Found", 404
    board_data = boards[uri]
    error = None

    if request.method == 'POST':
        entered_pass = request.form.get('password')
        if entered_pass == board_data.get('password'):
            session[f"auth_{uri}"] = entered_pass
            return redirect(url_for('view_board', uri=uri))
        else:
            error = "Incorrect Password."

    html = """
    {% extends "base" %}
    {% block content %}
    <div class="box" style="max-width: 400px; margin-top: 50px;">
        <div class="box-title">🔒 Protected Board: /{{ uri }}/</div>
        <p>This board requires an access password to view its contents.</p>
        {% if error %}<p style="color:red; font-weight:bold;">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="password" placeholder="Board Password" style="width:80%; margin-bottom:10px;" required><br>
            <button type="submit">Access Board</button>
        </form>
    </div>
    {% endblock %}
    """
    return render_template_string(html, boards=boards, settings=cfg, trans=t, is_textboard=False, error=error)

@app.route('/board/<uri>', methods=['GET', 'POST'])
def view_board(uri):
    check_banned(uri)
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if uri not in boards: return "Not Found", 404
    board_data = boards[uri]
    
    if not check_password_auth(uri, board_data):
        return redirect(url_for('board_auth', uri=uri))

    is_textboard = (board_data.get('type') == 'textboard')

    if request.method == 'POST':
        user_ans = request.form.get('captcha')
        if not user_ans or int(user_ans) != session.get('captcha_ans'):
            return "Incorrect Captcha Solution.", 400

        name = request.form.get('name').strip() or t('anonymous')
        subject = request.form.get('subject').strip() or "Untitled"
        message = request.form.get('message').strip()
        
        filename = None
        if not is_textboard and 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                filename = f"{int(time.time())}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        timestamp_now = int(time.time())
        new_thread = {
            "id": timestamp_now,
            "ip": request.remote_addr,
            "date": datetime.now().strftime("%m/%d/%Y (%a) %H:%M:%S"),
            "name": name,
            "subject": subject,
            "message": message,
            "file": filename,
            "last_bump": timestamp_now,
            "replies": []
        }
        board_data['threads'].insert(0, new_thread)
        save_json(BOARDS_FILE, boards)
        return redirect(url_for('view_board', uri=uri))

    is_mod = session.get('is_global_admin', False) or ('user' in session and board_data['owner'] == session['user'])
    captcha_question = get_captcha()

    if 'threads' in board_data:
        for t_obj in board_data['threads']:
            if 'last_bump' not in t_obj:
                t_obj['last_bump'] = t_obj['id']
        board_data['threads'] = sorted(board_data['threads'], key=lambda k: k['last_bump'], reverse=True)

    custom_notice = board_data.get('custom_notice') if board_data.get('custom_notice') else None

    imgboard_html = """
    {% extends "base" %}
    {% block content %}
    <div style="text-align:center; margin-top:10px; margin-bottom: 15px; clear:both; width:100%;">
        {% if board.banner_url %}<img src="{{ board.banner_url }}" style="max-width:400px;"><br>{% endif %}
        <h1 style="color:#800000; font-family:serif; font-size:24pt; margin:5px; font-weight:normal;">/{{ uri }}/ - {{ board.title }}</h1>
    </div>
    
    <div style="width: 100%; display: block; margin-bottom: 20px;">
        <form method="POST" enctype="multipart/form-data">
            <table class="post-form">
                <tr>
                    <td class="form-label">{{ trans('name') }}</td>
                    <td class="form-value"><input type="text" name="name" value="Anonymous"></td>
                </tr>
                <tr>
                    <td class="form-label">{{ trans('subject') }}</td>
                    <td class="form-value">
                        <input type="text" name="subject">
                        <input type="submit" value="{{ trans('btn_submit_thread') }}">
                    </td>
                </tr>
                <tr>
                    <td class="form-label">{{ trans('message') }}</td>
                    <td class="form-value"><textarea name="message" required></textarea></td>
                </tr>
                <tr>
                    <td class="form-label">{{ trans('file') }}</td>
                    <td class="form-value"><input type="file" name="file" accept="image/*,video/*"></td>
                </tr>
                <tr>
                    <td class="form-label">Verification</td>
                    <td class="form-value" style="font-size: 9pt; font-family: sans-serif; color: #000;">
                        Solve: <b>{{ captcha }}</b> = <input type="text" name="captcha" size="5" style="width:50px; height:20px;" required>
                    </td>
                </tr>
            </table>
        </form>
        <div class="form-rules-box">
            <ul>
                <li>Supported file formats are standard images (JPG, PNG, GIF) and video containers (MP4, WEBM).</li>
                <li>Maximum configuration payload limit allocated globally per content package request.</li>
                <li>Hyperlinks are processed contextually and embedded inside raw layout tags dynamically.</li>
            </ul>
        </div>
    </div>
    <hr style="width:100%; border-color:#D9BFB7; margin:15px 0; clear:both;">
    
    {% for thread in board.threads %}
    <div class="thread" id="p{{ thread.id }}">
        <div class="op-post">
            {% if thread.file %}
            <div class="file-meta">File: <a target="_blank" href="/data/src/{{ thread.file }}">{{ thread.file }}</a></div>
                {% if thread.file | is_video %}
                <video class="thumb" src="/data/src/{{ thread.file }}" controls preload="metadata" style="max-width:200px; max-height:200px; float:left; margin-right:20px;"></video>
                {% else %}
                <a target="_blank" href="/data/src/{{ thread.file }}"><img class="thumb" src="/data/src/{{ thread.file }}"></a>
                {% endif %}
            {% endif %}
            <div class="post-info">
                <input type="checkbox"> <span class="subject">{{ thread.subject }}</span> <span class="poster-name">{{ thread.name }}</span> {{ thread.date }} No. {{ thread.id }}
                [<a href="/board/{{ uri }}/thread/{{ thread.id }}">{{ trans('btn_reply') }}</a>]
                {% if is_mod %}
                <div class="mod-actions">IP: {{ thread.ip }} | <form method="POST" action="/moderation/action" style="display:inline;"><input type="hidden" name="uri" value="{{ uri }}"><input type="hidden" name="thread_id" value="{{ thread.id }}"><button type="submit" name="type" value="delete">{{ trans('delete_btn') }}</button></form></div>
                {% endif %}
            </div>
            <div class="post-message">{{ thread.message | chan_format | safe }}</div>
        </div>
        
        {% for reply in thread.replies %}
        <div class="reply-container" id="p{{ reply.id }}">
            <div class="reply-post">
                <div class="post-info">
                    <input type="checkbox"> <span class="poster-name">{{ reply.name }}</span> {{ reply.date }} No. {{ reply.id }}
                    {% if is_mod %}
                    <div class="mod-actions">IP: {{ reply.ip }} | <form method="POST" action="/moderation/action" style="display:inline;"><input type="hidden" name="uri" value="{{ uri }}"><input type="hidden" name="thread_id" value="{{ thread.id }}"><input type="hidden" name="reply_id" value="{{ reply.id }}"><button type="submit" name="type" value="delete">{{ trans('delete_btn') }}</button></form></div>
                    {% endif %}
                </div>
                {% if reply.file %}
                <div class="file-meta">File: <a target="_blank" href="/data/src/{{ reply.file }}">{{ reply.file }}</a></div>
                    {% if reply.file | is_video %}
                    <video class="media-reply" src="/data/src/{{ reply.file }}" controls preload="metadata" style="max-width:180px; display:block; margin:4px 0;"></video>
                    {% else %}
                    <a target="_blank" href="/data/src/{{ reply.file }}"><img src="/data/src/{{ reply.file }}" style="max-width:120px; display:block; margin:4px 0;"></a>
                    {% endif %}
                {% endif %}
                <div class="post-message">{{ reply.message | chan_format | safe }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
    <hr style="width:100%; border-color:#D9BFB7; margin:15px 0; clear:both;">
    {% endfor %}
    {% endblock %}
    """

    textboard_html = """
    {% extends "base" %}
    {% block content %}
    <div class="outerbox" id="titlebox">
        <div class="innerbox">
            <h1>{{ board.title }}</h1>
            <div class="threadnavigation">Pure Text Ecosystem</div>
        </div>
    </div>
    <div id="threads">
        <div id="threadlist">
            {% for t_idx in board.threads %}
                <span class="threadlink"><a href="/board/{{ uri }}/thread/{{ t_idx.id }}">{{ loop.index }}: {{ t_idx.subject }} ({{ t_idx.replies | length + 1 }})</a></span>
            {% endfor %}
            <div id="threadlinks"><a href="#createbox">[{{ trans('new_thread') }}]</a></div>
        </div>
    </div>
    <div id="posts">
    {% for thread in board.threads %}
        <div class="thread" id="p{{ thread.id }}">
            <h2><a href="/board/{{ uri }}/thread/{{ thread.id }}">{{ thread.subject }}</a></h2>
            <div class="replies">
                <div class="reply">
                    <h3>
                        <span class="replynum">1</span>
                        <span class="postername">{{ thread.name }}</span>
                        {{ thread.date }} ID:{{ thread.id }}
                    </h3>
                    <div class="replytext"><div class="aa">{{ thread.message | chan_format | safe }}</div></div>
                </div>
                {% for reply in thread.replies %}
                <div class="reply" id="p{{ reply.id }}">
                    <h3><span class="replynum">{{ loop.index + 1 }}</span> <span class="postername">{{ reply.name }}</span> {{ reply.date }} No. {{ reply.id }}</h3>
                    <div class="replytext"><div class="aa">{{ reply.message | chan_format | safe }}</div></div>
                </div>
                {% endfor %}
            </div>
            <form method="POST" action="/board/{{ uri }}/thread/{{ thread.id }}">
                <input type="text" name="name" size="15" placeholder="{{ trans('name') }}">
                <input type="submit" value="{{ trans('btn_reply') }}">
                <span class="postcaptcha"> [ Solve: {{ captcha }} <input type="text" name="captcha" size="4" required> ]</span>
                <br>
                <textarea name="message" rows="3" style="width:90%; margin-top:5px;" required></textarea>
            </form>
        </div>
    {% endfor %}
    </div>
    <div class="outerbox" id="createbox" style="margin-top:25px;">
        <div class="innerbox">
            <h2>New Thread</h2>
            <form method="POST">
                <table border="0">
                    <tr><td>{{ trans('subject') }}:</td><td><input type="text" name="subject" size="40" required></td></tr>
                    <tr><td>{{ trans('name') }}:</td><td><input type="text" name="name" size="20"></td></tr>
                    <tr><td valign="top">{{ trans('message') }}:</td><td><textarea name="message" rows="5" cols="50" required></textarea></td></tr>
                    <tr><td class="threadcaptcha">Solve {{ captcha }}:</td><td><input type="text" name="captcha" size="10" required> <input type="submit" value="Post New Thread"></td></tr>
                </table>
            </form>
        </div>
    </div>
    {% endblock %}
    """

    target_html = textboard_html if is_textboard else imgboard_html
    return render_template_string(target_html, boards=boards, uri=uri, board=board_data, settings=cfg, trans=t, is_textboard=is_textboard, textboard_class="mainpage", is_mod=is_mod, captcha=captcha_question, custom_notice=custom_notice)

@app.route('/board/<uri>/thread/<int:thread_id>', methods=['GET', 'POST'])
def view_thread(uri, thread_id):
    check_banned(uri)
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    if uri not in boards: return "Not Found", 404
    board_data = boards[uri]

    if not check_password_auth(uri, board_data):
        return redirect(url_for('board_auth', uri=uri))

    is_textboard = (board_data.get('type') == 'textboard')
    thread = next((t for t in board_data['threads'] if t['id'] == thread_id), None)
    if not thread: return "Thread Not Found", 404

    if request.method == 'POST':
        user_ans = request.form.get('captcha')
        if not user_ans or int(user_ans) != session.get('captcha_ans'):
            return "Incorrect Captcha Solution.", 400

        name = request.form.get('name').strip() or t('anonymous')
        message = request.form.get('message').strip()

        filename = None
        if not is_textboard and 'file' in request.files:
            file = request.files['file']
            if file and file.filename != '':
                filename = f"{int(time.time())}_{file.filename}"
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        timestamp_now = int(time.time())
        new_reply = {
            "id": timestamp_now,
            "ip": request.remote_addr,
            "date": datetime.now().strftime("%m/%d/%Y (%a) %H:%M:%S"),
            "name": name,
            "message": message,
            "file": filename
        }
        thread['replies'].append(new_reply)
        thread['last_bump'] = timestamp_now
        
        save_json(BOARDS_FILE, boards)
        return redirect(url_for('view_thread', uri=uri, thread_id=thread_id))

    captcha_question = get_captcha()
    is_mod = session.get('is_global_admin', False) or ('user' in session and board_data['owner'] == session['user'])
    custom_notice = board_data.get('custom_notice') if board_data.get('custom_notice') else None

    imgboard_thread_html = """
    {% extends "base" %}
    {% block content %}
    <div style="margin: 10px 0; text-align: left;"><a href="/board/{{ uri }}">⬅ {{ trans('back_to_board') }}</a></div>
    <div class="thread" id="p{{ thread.id }}">
        <div class="op-post">
            {% if thread.file %}
            <div class="file-meta">File: <a target="_blank" href="/data/src/{{ thread.file }}">{{ thread.file }}</a></div>
                {% if thread.file | is_video %}
                <video class="thumb" src="/data/src/{{ thread.file }}" controls preload="metadata" style="max-width:200px; max-height:200px; float:left; margin-right:20px;"></video>
                {% else %}
                <a target="_blank" href="/data/src/{{ thread.file }}"><img class="thumb" src="/data/src/{{ thread.file }}"></a>
                {% endif %}
            {% endif %}
            <div class="post-info">
                <input type="checkbox"> <span class="subject">{{ thread.subject }}</span> <span class="poster-name">{{ thread.name }}</span> {{ thread.date }} No. {{ thread.id }}
            </div>
            <div class="post-message">{{ thread.message | chan_format | safe }}</div>
        </div>

        {% for reply in thread.replies %}
        <div class="reply-container" id="p{{ reply.id }}">
            <div class="reply-post">
                <div class="post-info">
                    <input type="checkbox"> <span class="poster-name">{{ reply.name }}</span> {{ reply.date }} No. {{ reply.id }}
                    {% if is_mod %}
                    <div class="mod-actions">IP: {{ reply.ip }} | <form method="POST" action="/moderation/action" style="display:inline;"><input type="hidden" name="uri" value="{{ uri }}"><input type="hidden" name="thread_id" value="{{ thread.id }}"><input type="hidden" name="reply_id" value="{{ reply.id }}"><button type="submit" name="type" value="delete">{{ trans('delete_btn') }}</button></form></div>
                    {% endif %}
                </div>
                {% if reply.file %}
                <div class="file-meta">File: <a target="_blank" href="/data/src/{{ reply.file }}">{{ reply.file }}</a></div>
                    {% if reply.file | is_video %}
                    <video class="media-reply" src="/data/src/{{ reply.file }}" controls preload="metadata" style="max-width:180px; display:block; margin:4px 0;"></video>
                    {% else %}
                    <a target="_blank" href="/data/src/{{ reply.file }}"><img src="/data/src/{{ reply.file }}" style="max-width:120px; display:block; margin:4px 0;"></a>
                    {% endif %}
                {% endif %}
                <div class="post-message">{{ reply.message | chan_format | safe }}</div>
            </div>
        </div>
        {% endfor %}
    </div>
    
    <div style="width: 100%; display: block; margin-top: 25px;">
        <form method="POST" enctype="multipart/form-data">
            <table class="post-form">
                <tr>
                    <td class="form-label">{{ trans('name') }}</td>
                    <td class="form-value"><input type="text" name="name" value="Anonymous"></td>
                </tr>
                <tr>
                    <td class="form-label">{{ trans('message') }}</td>
                    <td class="form-value">
                        <textarea name="message" required></textarea>
                    </td>
                </tr>
                <tr>
                    <td class="form-label">{{ trans('file') }}</td>
                    <td class="form-value"><input type="file" name="file" accept="image/*,video/*"></td>
                </tr>
                <tr>
                    <td class="form-label">Verification</td>
                    <td class="form-value" style="font-size: 9pt; font-family: sans-serif; color: #000;">
                        Solve: <b>{{ captcha }}</b> = <input type="text" name="captcha" size="5" style="width:50px; height:20px;" required>
                        <input type="submit" value="{{ trans('btn_reply') }}" style="height:22px; margin-left:10px;">
                    </td>
                </tr>
            </table>
        </form>
    </div>
    {% endblock %}
    """

    textboard_thread_html = """
    {% extends "base" %}
    {% block content %}
    <div id="threads">
        <h1>{{ thread.subject }}</h1>
        <div id="posts">
            <div class="reply" id="p{{ thread.id }}">
                <h3><span class="replynum">1</span> <span class="postername">{{ thread.name }}</span> {{ thread.date }} ID:{{ thread.id }}</h3>
                <div class="replytext"><div class="aa">{{ thread.message | chan_format | safe }}</div></div>
            </div>
            {% for reply in thread.replies %}
            <div class="reply" id="p{{ reply.id }}">
                <h3><span class="replynum">{{ loop.index + 1 }}</span> <span class="postername">{{ reply.name }}</span> {{ reply.date }} No. {{ reply.id }}</h3>
                <div class="replytext"><div class="aa">{{ reply.message | chan_format | safe }}</div></div>
            </div>
            {% endfor %}
            <form method="POST">
                <table border="0">
                    <tr><td>{{ trans('name') }}:</td><td><input type="text" name="name" size="25"></td></tr>
                    <tr><td>{{ trans('message') }}:</td><td><textarea name="message" rows="4" cols="60" required></textarea></td></tr>
                    <tr><td class="postcaptcha">Solve {{ captcha }}:</td><td><input type="text" name="captcha" size="10" required> <input type="submit" value="{{ trans('btn_reply') }}"></td></tr>
                </table>
            </form>
        </div>
        <div style="margin-top:15px; padding:5px;"><a href="/board/{{ uri }}">< {{ trans('back_to_index') }}</a></div>
    </div>
    {% endblock %}
    """
    
    target_html = textboard_thread_html if is_textboard else imgboard_thread_html
    return render_template_string(target_html, boards=boards, uri=uri, board=board_data, thread=thread, settings=cfg, trans=t, is_textboard=is_textboard, textboard_class="threadpage", captcha=captcha_question, is_mod=is_mod, custom_notice=custom_notice)

@app.route('/moderation/action', methods=['POST'])
def mod_action():
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    uri = request.form.get('uri')
    thread_id = int(request.form.get('thread_id'))
    reply_id = request.form.get('reply_id')
    action_type = request.form.get('type')
    
    if uri not in boards: return "Bad Request", 400
    board_data = boards[uri]
    if not (session.get('is_global_admin', False) or ('user' in session and board_data['owner'] == session['user'])):
        return "Unauthorized", 403

    thread = next((t for t in board_data['threads'] if t['id'] == thread_id), None)
    if thread:
        if reply_id:
            reply = next((r for r in thread['replies'] if str(r['id']) == str(reply_id)), None)
            if reply:
                if action_type == 'delete': thread['replies'].remove(reply)
                if action_type == 'ban' and reply.get('ip'):
                    if session.get('is_global_admin', False): cfg['global_bans'].append(reply['ip'])
                    else: board_data['bans'].append(reply['ip'])
        else:
            if action_type == 'delete': board_data['threads'].remove(thread)
            if action_type == 'ban' and thread.get('ip'):
                if session.get('is_global_admin', False): cfg['global_bans'].append(thread['ip'])
                else: board_data['bans'].append(thread['ip'])

    save_json(BOARDS_FILE, boards)
    save_json(SETTINGS_FILE, cfg)
    return redirect(request.referrer or url_for('view_board', uri=uri))

@app.route('/superadmin_gateway', methods=['GET', 'POST'])
def superadmin_gateway():
    boards = load_json(BOARDS_FILE, {})
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    error = None
    if request.method == 'POST':
        if request.form.get('master_password') == "Admin123": #Change password
            session['is_global_admin'] = True
            return redirect(url_for('global_admin_panel'))
        else: error = "Access Denied."

    html = """
    {% extends "base" %}
    {% block content %}
    <div class="box" style="background:#222; color:#FFF; max-width:400px; margin-top:50px;">
        <div class="box-title" style="background:#000;">MASTER CONFIG GATEWAY</div>
        {% if error %}<p style="color:red; font-weight:bold;">{{ error }}</p>{% endif %}
        <form method="POST">
            <input type="password" name="master_password" style="width:80%; text-align:center; margin-bottom:10px;" required><br>
            <button type="submit">Authenticate</button>
        </form>
    </div>
    {% endblock %}
    """
    return render_template_string(html, boards=boards, error=error, settings=cfg, trans=t, is_textboard=False)

@app.route('/superadmin_panel', methods=['GET', 'POST'])
def global_admin_panel():
    if not session.get('is_global_admin', False): abort(403)
    cfg = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    boards = load_json(BOARDS_FILE, {})
    
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'save_settings':
            cfg['site_name'] = request.form.get('site_name')
            cfg['global_notice'] = request.form.get('global_notice')
            cfg['language'] = request.form.get('language')
            save_json(SETTINGS_FILE, cfg)
        elif action == 'delete_board_global':
            target_uri = request.form.get('target_uri')
            if target_uri in boards: del boards[target_uri]
            save_json(BOARDS_FILE, boards)
        elif action == 'exit_admin':
            session.pop('is_global_admin', None)
            return redirect(url_for('home'))

    html = """
    {% extends "base" %}
    {% block content %}
    <div class="box" style="background:#E2E3E5; text-align:left; max-width:850px;">
        <div class="box-title" style="background:#383D41;">GLOBAL OPERATIONS CONTROL PANEL (ADMIN)</div>
        <form method="POST">
            <input type="hidden" name="action" value="save_settings">
            <h3>1. Localization Options & General Global Settings</h3>
            <select name="language" style="padding:3px;">
                <option value="en" {% if cfg.language == 'en' %}selected{% endif %}>English (English)</option>
                <option value="es" {% if cfg.language == 'es' %}selected{% endif %}>Español (Spanish)</option>
            </select>
            <br><br>
            <label><b>Site Name:</b></label><br><input type="text" name="site_name" value="{{ cfg.site_name }}" style="width:40%;"><br><br>
            <label><b>Global Banner Notice Text:</b></label><br><textarea name="global_notice" style="width:95%;">{{ cfg.global_notice }}</textarea><br><br>
            <button type="submit" style="background:green; color:#FFF; padding:5px 10px; border:none; font-weight:bold;">Update Global Configuration</button>
        </form>
        <hr style="margin:20px 0;">
        <h3>2. System Board Purgatory</h3>
        <form method="POST"><input type="hidden" name="action" value="delete_board_global">
            <select name="target_uri">
                {% for uri, data in boards.items() %}
                    <option value="{{ uri }}">/{{ uri }}/ - {{ data.title }}</option>
                {% endfor %}
            </select>
            <button type="submit" style="background:red; color:white; border:none; padding:3px 10px;">Purge Board Data</button>
        </form>
        <hr style="margin:20px 0;">
        <p><form method="POST"><input type="hidden" name="action" value="exit_admin"><button type="submit">Log Out From Terminal</button></form></p>
    </div>
    {% endblock %}
    """
    return render_template_string(html, boards=boards, cfg=cfg, settings=cfg, trans=t, is_textboard=False)

@app.route('/data/src/<filename>')
def serve_file(filename):
    from flask import send_from_directory
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.before_request
def setup_templates():
    import jinja2
    app.jinja_loader = jinja2.DictLoader({'base': BASE_HTML})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
