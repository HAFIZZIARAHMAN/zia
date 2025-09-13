import os
from flask import Flask, request, redirect, url_for, session, render_template
from flask import Flask, request, render_template, redirect, url_for, session
import sqlite3
import os
import os
from flask import Flask, request, jsonify, render_template_string
import os
from openai import OpenAI

import subprocess
import sys
from flask_socketio import SocketIO, emit, join_room
import random, string
from flask import Flask
from flask import Flask
from flask_socketio import SocketIO, emit, join_room
from flask import request, make_response
from bs4 import BeautifulSoup
import html

app = Flask(__name__)
app.config['SECRET_KEY'] = "mysecretkey"

socketio = SocketIO(app)





# Function to install a package if it's missing
def install_if_missing(package_name):
    try:
        __import__(package_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

# Ensure 'openai' is installed
install_if_missing("openai")


# Now you can safely import it
from openai import OpenAI
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")

conn = sqlite3.connect(DB_PATH)

app.secret_key = "mysecretkey"

client = OpenAI(
    base_url="https://router.huggingface.co/v1",
     api_key=os.environ.get("HF_TOKEN")
)
MODEL_NAME = "deepseek-ai/DeepSeek-V3-0324:fireworks-ai"


DB_PATH = os.path.join(os.path.dirname(__file__), "data.db")
conn = sqlite3.connect(DB_PATH)


# ---------- DB Setup ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            password TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")


# ---------- Routes ----------

# Sign In (Index page)
@app.route("/", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session["user"] = user[1]  # store name in session
            return redirect(url_for("home"))
        else:
            return "<h3>Invalid login!</h3><p><a href='/'>Try again</a></p>"

    return render_template("index.html")

# Sign Up
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()

        conn = sqlite3.connect("data.db")
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                      (name, email, password))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return "<h3>Email already exists!</h3><p><a href='/signup'>Try again</a></p>"
        conn.close()
        return redirect(url_for("signin"))

    return render_template("auth.html")



# Dummy page after login
@app.route("/home")
def home():
    if "user" in session:
        return render_template("home.html", user=session["user"])
    else:
        return redirect(url_for("signin"))


# ---------- Admin Panel ----------
ADMIN_USER = "hiimzia"
ADMIN_PASS = "!@#123"

@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        userid = request.form["userid"]
        password = request.form["password"]
        if userid == ADMIN_USER and password == ADMIN_PASS:
            session["logged_in"] = True
            return redirect(url_for("users"))
        else:
            error = "Invalid username or password"
    return render_template("login.html", error=error)

@app.route("/users")
def users():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT id, name, email, password FROM users")  # Correct column name
    all_users = c.fetchall()
    conn.close()
    return render_template("users.html", users=all_users)


# ---------- /submit Route ----------
@app.route("/submit", methods=["POST"])
def submit():
    # Get form data
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "").strip()

    # Connect to database
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
    user = c.fetchone()
    conn.close()

    # Check if user exists
    if user:
        session["user"] = user[1]  # store user's name in session
        return redirect(url_for("home"))

    else:
        return "<h3>Invalid login!</h3><p><a href='/'>Try again</a></p>"




@app.route("/delete/<int:user_id>")
def delete_user(user_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("users"))

@app.route("/edit/<int:user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = sqlite3.connect("data.db")
    c = conn.cursor()

    if request.method == "POST":
        new_name = request.form["name"].strip()
        new_email = request.form["email"].strip().lower()
        new_password = request.form["password"].strip()

        c.execute("SELECT * FROM users WHERE LOWER(email)=? AND id!=?", (new_email, user_id))
        exists = c.fetchone()
        if exists:
            conn.close()
            return "<h3>Error: Email already used!</h3><p><a href='/users'>Back</a></p>"

        # Update all fields including password
        c.execute("UPDATE users SET name=?, email=?, password=? WHERE id=?",
                  (new_name, new_email, new_password, user_id))
        conn.commit()
        conn.close()
        return redirect(url_for("users"))

    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()

    if not user:
        return "<h3>User not found!</h3><p><a href='/users'>Back</a></p>"

    return render_template("edit.html", user=user)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("signin"))

@app.route("/perenoid")
def perenoid():
    return render_template("perenoid.html")


    






# 🔑 Hugging Face OpenAI-compatible API client



# ---------------------- ROUTES ----------------------

@app.route("/AI-home")
def AI():
    return render_template("AI.html")

@app.route("/api-status")
def api_status():
    """Check if the Hugging Face API is online"""
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5
        )
        return jsonify({"status": "online"})
    except Exception as e:
        return jsonify({"status": "error", "error": str(e)})

@app.route("/generate", methods=["POST"])
def generate():
    """Generate text using DeepSeek via Hugging Face router"""
    try:
        data = request.get_json(force=True) or {}
        user_message = data.get("message", "").strip()

        if not user_message:
            return jsonify({"error": "No message provided"}), 400

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ],
            max_tokens=500,
            temperature=0.7
        )

        response_text = completion.choices[0].message.content

        return jsonify({"response": response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
    # --- Multiplayer Tic Tac Toe ---
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import random, string


app.config["SECRET_KEY"] = "mysecretkey"

# ✅ Initialize SocketIO
socketio = SocketIO(app)

# ✅ Store active games
games = {}

def generate_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ---------- Routes ----------
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import random, string


app.config["SECRET_KEY"] = "mysecretkey"

socketio = SocketIO(app)

# Store active games
games = {}

def generate_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")   # Lobby (create/join)

@app.route("/game")
def game():
    return render_template("game.html")   # Board UI

  

# ---------- Winner Check ----------
def check_winner(board):
    # All winning combinations (indices)
    wins = [
        [0,1,2], [3,4,5], [6,7,8],  # rows
        [0,3,6], [1,4,7], [2,5,8],  # columns
        [0,4,8], [2,4,6]            # diagonals
    ]
    for combo in wins:
        a, b, c = combo
        if board[a] != "" and board[a] == board[b] == board[c]:
            return board[a]  # "X" or "O"
    if "" not in board:
        return "Tie"
    return None  # Game still ongoing




# ---------- Socket.IO Events ----------
@socketio.on("create_game")
def create_game():
    code = generate_code()
    games[code] = {"board": [""] * 9, "turn": "X", "players": {}}
    join_room(code)
    games[code]["players"][request.sid] = "X"  # creator is X
    emit("game_created", {"code": code, "board": games[code]["board"], "turn": "X"})
    

@socketio.on("join_game")
def join_game(data):
    code = data["code"].strip().upper()
    if code in games and len(games[code]["players"]) < 2:
        join_room(code)
        # Second player is O
        games[code]["players"][request.sid] = "O"
        emit("game_joined", {
            "code": code,
            "board": games[code]["board"],
            "turn": games[code]["turn"]
        })
        emit("start_game", {
            "message": "Both players connected!",
            "board": games[code]["board"],
            "turn": games[code]["turn"]
        }, room=code)
    else:
        emit("error", {"message": "Invalid game code or room full"})

@socketio.on("make_move")
def make_move(data):
    code = data["code"]
    index = data["index"]

    if code not in games:
        emit("error", {"message": "Invalid game code"})
        return

    game = games[code]
    player_symbol = game["players"].get(request.sid)

    if player_symbol != game["turn"]:
        # It's not this player's turn
        # Find whose turn it actually is
        for sid, symbol in game["players"].items():
            if symbol == game["turn"]:
                current_sid = sid
                break

        # Send a message to the player who clicked out-of-turn
        emit("not_your_turn", {"message": f"It's player {game['turn']}'s turn!"})
        return

    # Make move if the cell is empty
    if game["board"][index] == "":
        game["board"][index] = player_symbol
        winner = check_winner(game["board"])

        if winner:
            emit("game_over", {"board": game["board"], "winner": winner}, room=code)
        else:
            # Switch turn
            game["turn"] = "O" if game["turn"] == "X" else "X"
            emit("move_made", {"board": game["board"], "turn": game["turn"]}, room=code)

            # Add these imports at the top of your app.py


# Enhanced translation dictionary with Turkish support
translations = {
    # Navigation and UI elements
    "Submit Form": {
        "es": "Enviar formulario", "fr": "Soumettre le formulaire", "it": "Invia modulo", 
        "de": "Formular einreichen", "nl": "Formulier indienen", "tr": "Formu Gönder"
    },
    "BeautifulForms": {
        "es": "FormulariosHermosos", "fr": "BeauxFormulaires", "it": "FormeBelle", 
        "de": "SchöneFormulare", "nl": "MooieFormulieren", "tr": "GüzelFormlar"
    },
    "Admin": {
        "es": "Administrador", "fr": "Admin", "it": "Amministratore", 
        "de": "Administrator", "nl": "Beheerder", "tr": "Yönetici"
    },
    "Submit your data": {
        "es": "Envía tus datos", "fr": "Soumettez vos données", "it": "Invia i tuoi dati", 
        "de": "Senden Sie Ihre Daten", "nl": "Verzend uw gegevens", "tr": "Verilerinizi Gönderin"
    },
    "Sign In": {
        "es": "Iniciar sesión", "fr": "Se connecter", "it": "Accedi", 
        "de": "Anmelden", "nl": "Inloggen", "tr": "Giriş Yap"
    },
    "Email": {
        "es": "Correo electrónico", "fr": "E-mail", "it": "E-mail", 
        "de": "E-Mail", "nl": "E-mail", "tr": "E-posta"
    },
    "Password": {
        "es": "Contraseña", "fr": "Mot de passe", "it": "Password", 
        "de": "Passwort", "nl": "Wachtwoord", "tr": "Şifre"
    },
    "Login": {
        "es": "Iniciar sesión", "fr": "Connexion", "it": "Accesso", 
        "de": "Anmeldung", "nl": "Inloggen", "tr": "Giriş"
    },
    "Don't have an account?": {
        "es": "¿No tienes una cuenta?", "fr": "Vous n'avez pas de compte ?", "it": "Non hai un account?", 
        "de": "Sie haben kein Konto?", "nl": "Heb je geen account?", "tr": "Hesabınız yok mu?"
    },
    "Sign Up": {
        "es": "Regístrate", "fr": "S'inscrire", "it": "Iscriviti", 
        "de": "Anmelden", "nl": "Aanmelden", "tr": "Kaydol"
    },
    "All rights reserved.": {
        "es": "Todos los derechos reservados.", "fr": "Tous droits réservés.", "it": "Tutti i diritti riservati.", 
        "de": "Alle Rechte vorbehalten.", "nl": "Alle rechten voorbehouden.", "tr": "Tüm hakları saklıdır."
    },
    "Contact us": {
        "es": "Contáctanos", "fr": "Contactez-nous", "it": "Contattaci", 
        "de": "Kontaktieren Sie uns", "nl": "Neem contact op", "tr": "Bize Ulaşın"
    },
    "Hello World": {
        "es": "Hola Mundo", "fr": "Bonjour le monde", "it": "Ciao Mondo", 
        "de": "Hallo Welt", "nl": "Hallo Wereld", "tr": "Merhaba Dünya"
    },
    # Admin panel translations
    "ID": {
        "es": "ID", "fr": "ID", "it": "ID", "de": "ID", "nl": "ID", "tr": "ID"
    },
    "Name": {
        "es": "Nombre", "fr": "Nom", "it": "Nome", "de": "Name", "nl": "Naam", "tr": "İsim"
    },
    "Actions": {
        "es": "Acciones", "fr": "Actions", "it": "Azioni", "de": "Aktionen", "nl": "Acties", "tr": "İşlemler"
    },
    "Edit": {
        "es": "Editar", "fr": "Modifier", "it": "Modifica", "de": "Bearbeiten", "nl": "Bewerken", "tr": "Düzenle"
    },
    "Delete": {
        "es": "Eliminar", "fr": "Supprimer", "it": "Elimina", "de": "Löschen", "nl": "Verwijderen", "tr": "Sil"
    },
    "Login to manage": {
        "es": "Inicia sesión para gestionar", "fr": "Connectez-vous pour gérer", "it": "Accedi per gestire", 
        "de": "Anmelden um zu verwalten", "nl": "Inloggen om te beheren", "tr": "Yönetmek için giriş yapın"
    },
    "No users found": {
        "es": "No se encontraron usuarios", "fr": "Aucun utilisateur trouvé", "it": "Nessun utente trovato", 
        "de": "Keine Benutzer gefunden", "nl": "Geen gebruikers gevonden", "tr": "Kullanıcı bulunamadı"
    },
    "Back to Form": {
        "es": "Volver al formulario", "fr": "Retour au formulaire", "it": "Torna al modulo", 
        "de": "Zurück zum Formular", "nl": "Terug naar formulier", "tr": "Forma Geri Dön"
    },
    "Manage users": {
        "es": "Gestionar usuarios", "fr": "Gérer les utilisateurs", "it": "Gestisci utenti", 
        "de": "Benutzer verwalten", "nl": "Gebruikers beheren", "tr": "Kullanıcıları Yönet"
    },
    # Admin login translations
    "Admin Login": {
        "es": "Inicio de sesión de administrador", "fr": "Connexion administrateur", "it": "Accesso amministratore", 
        "de": "Admin-Anmeldung", "nl": "Admin login", "tr": "Yönetici Girişi"
    },
    "User ID": {
        "es": "ID de usuario", "fr": "ID utilisateur", "it": "ID utente", 
        "de": "Benutzer-ID", "nl": "Gebruikers-ID", "tr": "Kullanıcı ID"
    },
    "Admin User ID": {
        "es": "ID de usuario administrador", "fr": "ID utilisateur administrateur", "it": "ID utente amministratore", 
        "de": "Administrator-Benutzer-ID", "nl": "Beheerders gebruikers-ID", "tr": "Yönetici Kullanıcı ID"
    },
    "Your Password": {
        "es": "Tu contraseña", "fr": "Votre mot de passe", "it": "La tua password", 
        "de": "Ihr Passwort", "nl": "Uw wachtwoord", "tr": "Şifreniz"
    },
    "Secure admin area - Unauthorized access prohibited": {
        "es": "Área administrativa segura - Acceso no autorizado prohibido", 
        "fr": "Zone d'administration sécurisée - Accès non autorisé interdit", 
        "it": "Area amministrativa sicura - Accesso non autorizzato vietato", 
        "de": "Sicherer Admin-Bereich - Unbefugter Zugriff verboten", 
        "nl": "Beveiligd admin gebied - Ongeautoriseerde toegang verboden", 
        "tr": "Güvenli yönetici alanı - Yetkisiz erişim yasaktır"
    },
    # Game translations
    "Tic Tac Toe": {
        "es": "Tres en raya", "fr": "Morpion", "it": "Tris", 
        "de": "Tic Tac Toe", "nl": "Boter-kaas-en-eieren", "tr": "XOX Oyunu"
    },
    "Choose Game Mode": {
        "es": "Elige modo de juego", "fr": "Choisissez le mode de jeu", "it": "Scegli modalità di gioco", 
        "de": "Spielmodus wählen", "nl": "Kies spelmodus", "tr": "Oyun Modunu Seçin"
    },
    "Single Player": {
        "es": "Un jugador", "fr": "Un joueur", "it": "Giocatore singolo", 
        "de": "Einzelspieler", "nl": "Singleplayer", "tr": "Tek Oyuncu"
    },
    "1 Device (Local 2 Players)": {
        "es": "1 Dispositivo (2 jugadores locales)", "fr": "1 Appareil (2 joueurs locaux)", 
        "it": "1 Dispositivo (2 giocatori locali)", "de": "1 Gerät (Lokale 2 Spieler)", 
        "nl": "1 Apparaat (Lokaal 2 spelers)", "tr": "1 Cihaz (Yerel 2 Oyuncu)"
    },
    "2 Devices (Online Multiplayer)": {
        "es": "2 Dispositivos (Multijugador en línea)", "fr": "2 Appareils (Multijoueur en ligne)", 
        "it": "2 Dispositivi (Multigiocatore online)", "de": "2 Geräte (Online-Mehrspieler)", 
        "nl": "2 Apparaten (Online multiplayer)", "tr": "2 Cihaz (Çoklu Oyunculu)"
    },
    "Online Multiplayer": {
        "es": "Multijugador en línea", "fr": "Multijoueur en ligne", "it": "Multigiocatore online", 
        "de": "Online-Mehrspieler", "nl": "Online multiplayer", "tr": "Çoklu Oyunculu"
    },
    "Create New Game": {
        "es": "Crear nuevo juego", "fr": "Créer une nouvelle partie", "it": "Crea nuova partita", 
        "de": "Neues Spiel erstellen", "nl": "Nieuw spel maken", "tr": "Yeni Oyun Oluştur"
    },
    "Enter Game Code": {
        "es": "Ingresar código de juego", "fr": "Entrer le code de jeu", "it": "Inserisci codice gioco", 
        "de": "Spielcode eingeben", "nl": "Voer spelcode in", "tr": "Oyun Kodunu Girin"
    },
    "Join Game": {
        "es": "Unirse al juego", "fr": "Rejoindre la partie", "it": "Unisciti al gioco", 
        "de": "Spiel beitreten", "nl": "Deelname aan spel", "tr": "Oyuna Katıl"
    },
    "Game Board": {
        "es": "Tablero de juego", "fr": "Plateau de jeu", "it": "Tabellone di gioco", 
        "de": "Spielfeld", "nl": "Spelbord", "tr": "Oyun Tahtası"
    },
    "Reset Game": {
        "es": "Reiniciar juego", "fr": "Redémarrer le jeu", "it": "Riavvia gioco", 
        "de": "Spiel zurücksetzen", "nl": "Spel resetten", "tr": "Oyunu Sıfırla"
    },
    "Back to Menu": {
        "es": "Volver al menú", "fr": "Retour au menu", "it": "Torna al menu", 
        "de": "Zurück zum Menü", "nl": "Terug naar menu", "tr": "Menüye Dön"
    },
    "Congratulations": {
        "es": "Felicidades", "fr": "Félicitations", "it": "Congratulazioni", 
        "de": "Herzlichen Glückwunsch", "nl": "Gefeliciteerd", "tr": "Tebrikler"
    },
    # AI page translations
    "AI Assistant": {
        "es": "Asistente de IA", "fr": "Assistant IA", "it": "Assistente AI", 
        "de": "KI-Assistent", "nl": "AI-assistent", "tr": "Yapay Zeka Asistanı"
    },
    "Powered by": {
        "es": "Desarrollado por", "fr": "Propulsé par", "it": "Sviluppato da", 
        "de": "Unterstützt von", "nl": "Aangedreven door", "tr": "Tarafından desteklenmektedir"
    },
    "Type your message here": {
        "es": "Escribe tu mensaje aquí", "fr": "Tapez votre message ici", "it": "Scrivi il tuo messaggio qui", 
        "de": "Geben Sie hier Ihre Nachricht ein", "nl": "Typ hier uw bericht", "tr": "Mesajınızı buraya yazın"
    },
    "Send": {
        "es": "Enviar", "fr": "Envoyer", "it": "Invia", 
        "de": "Senden", "nl": "Versturen", "tr": "Gönder"
    },
    "Thinking": {
        "es": "Pensando", "fr": "Réflexion", "it": "Pensando", 
        "de": "Denken", "nl": "Denken", "tr": "Düşünüyor"
    },
    # Add more translations as needed
}

def translate_text(text, lang):
    """Translate text to the specified language if available"""
    if text in translations and lang in translations[text]:
        return translations[text][lang]
    return text  # Return original text if no translation available

def translate_html(html_content, lang):
    """Parse HTML and translate all text content"""
    if lang == 'en':  # No translation needed for English
        return html_content
        
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Elements to translate
    elements_to_translate = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'span', 
                                         'div', 'li', 'td', 'th', 'label', 'button', 'title'])
    
    for element in elements_to_translate:
        if element.string and element.string.strip():
            original_text = element.string.strip()
            translated_text = translate_text(original_text, lang)
            if translated_text != original_text:
                element.string.replace_with(translated_text)
        # Also check for placeholder text in input fields
        if element.name == 'input' and element.get('placeholder'):
            original_placeholder = element['placeholder']
            translated_placeholder = translate_text(original_placeholder, lang)
            if translated_placeholder != original_placeholder:
                element['placeholder'] = translated_placeholder
    
    # Add language switcher to the page
    language_switcher = soup.new_tag('div')
    language_switcher['style'] = 'position: fixed; bottom: 20px; right: 20px; z-index: 1000; background: white; padding: 10px; border-radius: 5px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);'
    
    languages = {
        'en': 'English',
        'es': 'Español',
        'fr': 'Français',
        'it': 'Italiano',
        'de': 'Deutsch',
        'nl': 'Nederlands',
        'tr': 'Türkçe'  # Added Turkish
    }
    
    for code, name in languages.items():
        button = soup.new_tag('button')
        button['onclick'] = f'setLanguage("{code}")'
        button['style'] = 'margin: 2px; padding: 5px 10px;'
        button.string = name
        language_switcher.append(button)
    
    # Add JavaScript for language switching
    script = soup.new_tag('script')
    script.string = '''
    function setLanguage(lang) {
        document.cookie = "language=" + lang + "; path=/; max-age=31536000";
        location.reload();
    }
    '''
    
    # Add the language switcher and script to the body
    if soup.body:
        soup.body.append(language_switcher)
        soup.body.append(script)
    
    # Special handling for AI page to remove suggestions and make chat bigger
    if soup.find('div', class_='examples'):
        examples_div = soup.find('div', class_='examples')
        if examples_div:
            examples_div.decompose()  # Remove the examples/suggestions
            
        # Make chat container bigger
        chat_container = soup.find('div', class_='chat-container')
        if chat_container:
            current_style = chat_container.get('style', '')
            chat_container['style'] = current_style + ' height: 600px;'
            
        # Make input area bigger
        input_area = soup.find('div', class_='input-area')
        if input_area:
            current_style = input_area.get('style', '')
            input_area['style'] = current_style + ' min-height: 80px;'
            
        # Make textarea bigger
        textarea = soup.find('textarea')
        if textarea:
            current_style = textarea.get('style', '')
            textarea['style'] = current_style + ' min-height: 60px; font-size: 16px;'
    
    return str(soup)

# Add this middleware to translate all responses
@app.after_request
def translate_response(response):
    # Only translate HTML responses
    if response.content_type == 'text/html; charset=utf-8':
        lang = request.cookies.get('language', 'en')
        content = response.get_data(as_text=True)
        translated_content = translate_html(content, lang)
        response.set_data(translated_content)
    return response



# ---------- Run ----------
if __name__ == "__main__":
    import eventlet
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)

