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
            return redirect(url_for("/home"))
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
        return render_template("home.html")   # ✅ Directly show home.html
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
@app.route("/")
def index():
    return render_template("index.html")   # Lobby (create/join)

@app.route("/game")
def game():
    return render_template("game.html")   # Board UI

# ---------- Socket.IO Events ----------
@socketio.on("create_game")
def create_game():
    code = generate_code()
    games[code] = {"board": [""] * 9, "turn": "X"}
    join_room(code)
    emit("game_created", {
        "code": code,
        "board": games[code]["board"],
        "turn": "X"
    })
    # Tell creator explicitly they are waiting
    emit("waiting", {"message": "Waiting for another player..."})

@socketio.on("join_game")
def join_game(data):
    code = data["code"].strip().upper()
    if code in games:
        join_room(code)
        # Send to joining player
        emit("game_joined", {
            "code": code,
            "board": games[code]["board"],
            "turn": games[code]["turn"]
        })
        # Notify everyone in room
        emit("start_game", {
            "message": "Both players connected!",
            "board": games[code]["board"],
            "turn": games[code]["turn"]
        }, room=code)
    else:
        emit("error", {"message": "Invalid game code"})

@socketio.on("make_move")
def make_move(data):
    code = data["code"]
    index = data["index"]

    if code not in games:
        return

    game = games[code]
    if game["board"][index] == "":
        game["board"][index] = game["turn"]
        game["turn"] = "O" if game["turn"] == "X" else "X"
        emit("move_made", {"board": game["board"], "turn": game["turn"]}, room=code)

# ---------- Run ----------
# ---------------------- RUN APP ----------------------
# ---------------------- RUN APP ----------------------
if __name__ == "__main__":
    import eventlet
    import eventlet.wsgi
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True)
