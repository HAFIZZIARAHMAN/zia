from datetime import datetime, timedelta
import jinja2

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

app.secret_key = "secret123"
socketio = SocketIO(app)


# Add custom filters
app.jinja_env.filters['date'] = lambda s, format='%Y-%m-%d', years=0: (
    (datetime.now() + timedelta(days=years*365)).strftime(format) if not s 
    else datetime.strptime(s, '%Y-%m-%d').strftime(format)
)



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

# Ensure database has needed tables/columns
# (will call update_db_structure after its definition)


# ---------- DB Setup ----------
# ---------- Update DB Structure ----------
def update_db_structure():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    # Users table already exists
    c.execute("PRAGMA table_info(users)")
    cols = [col[1] for col in c.fetchall()]
    if "username" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN username TEXT")
    if "avatar_url" not in cols:
        c.execute("ALTER TABLE users ADD COLUMN avatar_url TEXT")
    
    # Followers table
    c.execute("""
        CREATE TABLE IF NOT EXISTS followers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            follower_email TEXT,
            followed_email TEXT,
            UNIQUE(follower_email, followed_email)
        )
    """)

    # Posts table
    c.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT,
            content TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()

# Ensure database has needed tables/columns (run once at startup)
try:
    update_db_structure()
except Exception:
    app.logger.exception('Failed to run update_db_structure')

@app.route("/follow/<username>")
def follow_user(username):
    if "user_email" not in session:
        return redirect(url_for("signin"))
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE username=?", (username,))
    target = c.fetchone()
    if not target:
        conn.close()
        return "User not found"
    
    try:
        c.execute("INSERT INTO followers (follower_email, followed_email) VALUES (?, ?)",
                  (session["user_email"], target[0]))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # Already following
    conn.close()
    return redirect(url_for("profile", username=username))


@app.route("/unfollow/<username>")
def unfollow_user(username):
    if "user_email" not in session:
        return redirect(url_for("signin"))

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT email FROM users WHERE username=?", (username,))
    target = c.fetchone()
    if target:
        c.execute("DELETE FROM followers WHERE follower_email=? AND followed_email=?",
                  (session["user_email"], target[0]))
        conn.commit()
    conn.close()
    return redirect(url_for("profile", username=username))

@app.route("/profile/<username>")
def profile(username):
    # viewing profiles is allowed for signed-in users and guests

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Get user email
    c.execute("SELECT id, name, email, username, avatar_url FROM users WHERE username=?", (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return "User not found"
    # Build a user dict for the template
    user = {'id': row[0], 'name': row[1], 'email': row[2], 'username': row[3], 'avatar_url': row[4]}
    user_email = user['email']
    # compute followers/following counts for template rendering
    try:
        c.execute('SELECT COUNT(1) FROM followers WHERE followed_email=?', (user_email,))
        user['followers_count'] = c.fetchone()[0] or 0
    except Exception:
        user['followers_count'] = 0
    try:
        c.execute('SELECT COUNT(1) FROM followers WHERE follower_email=?', (user_email,))
        user['following_count'] = c.fetchone()[0] or 0
    except Exception:
        user['following_count'] = 0

    # Get posts ONLY from users this person follows (or their own)
    current_email = session.get("user_email")
    c.execute("""
        SELECT posts.content, posts.timestamp, users.username
        FROM posts
        JOIN users ON users.email = posts.user_email
        WHERE posts.user_email = ? OR posts.user_email IN (
            SELECT followed_email FROM followers WHERE follower_email=?
        )
        ORDER BY posts.timestamp DESC
    """, (user_email, current_email))
    raw_posts = c.fetchall()
    # Convert DB rows to dicts for the template (so template can use post.content)
    posts = [{'content': rp[0], 'timestamp': rp[1], 'username': rp[2]} for rp in raw_posts]
    

    # Check if current user already follows this user
    is_following = False
    if current_email:
        try:
            c.execute("SELECT 1 FROM followers WHERE follower_email=? AND followed_email=?",
                      (current_email, user_email))
            is_following = bool(c.fetchone())
        except Exception:
            is_following = False
    
    conn.close()
    return render_template("profile.html", user=user, posts=posts, is_following=is_following, session_user_email=current_email)


@app.route('/profile/<username>/followers')
def profile_followers(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT email FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return 'User not found', 404
    email = row[0]
    c.execute('SELECT follower_email FROM followers WHERE followed_email=?', (email,))
    follower_emails = [r[0] for r in c.fetchall()]
    followers = []
    for fe in follower_emails:
        c.execute('SELECT id, name, username, avatar_url FROM users WHERE email=?', (fe,))
        r = c.fetchone()
        if r:
            followers.append({'id': r[0], 'name': r[1], 'username': r[2], 'avatar_url': r[3], 'email': fe})
    conn.close()
    return render_template('followers.html', user_username=username, followers=followers)


@app.route('/profile/<username>/following')
def profile_following(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT email FROM users WHERE username=?', (username,))
    row = c.fetchone()
    if not row:
        conn.close()
        return 'User not found', 404
    email = row[0]
    c.execute('SELECT followed_email FROM followers WHERE follower_email=?', (email,))
    following_emails = [r[0] for r in c.fetchall()]
    following = []
    for fe in following_emails:
        c.execute('SELECT id, name, username, avatar_url FROM users WHERE email=?', (fe,))
        r = c.fetchone()
        if r:
            following.append({'id': r[0], 'name': r[1], 'username': r[2], 'avatar_url': r[3], 'email': fe})
    conn.close()
    return render_template('following.html', user_username=username, following=following)


@app.route('/upload_avatar', methods=['POST'])
def upload_avatar():
    if 'user_email' not in session:
        return redirect(url_for('signin'))
    if 'avatar' not in request.files:
        return '<h3>No file uploaded</h3>', 400
    f = request.files['avatar']
    if f.filename == '':
        return '<h3>No file selected</h3>', 400
    # save to static/uploads
    upload_dir = os.path.join(BASE_DIR, 'static', 'uploads')
    os.makedirs(upload_dir, exist_ok=True)
    import time
    safe_name = str(int(time.time())) + '_' + os.path.basename(f.filename)
    dest = os.path.join(upload_dir, safe_name)
    f.save(dest)
    avatar_url = '/static/uploads/' + safe_name
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('UPDATE users SET avatar_url=? WHERE email=?', (avatar_url, session['user_email']))
    conn.commit()
    conn.close()
    return redirect(url_for('profile', username=request.form.get('username') or session.get('user')))


@app.route('/follow_toggle/<path:user_email>', methods=['POST'])
def follow_toggle(user_email):
    # Toggle follow from logged in user to the given user_email (used by profile.html form)
    if 'user_email' not in session:
        return redirect(url_for('signin'))
    me = session['user_email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT 1 FROM followers WHERE follower_email=? AND followed_email=?', (me, user_email))
        if c.fetchone():
            c.execute('DELETE FROM followers WHERE follower_email=? AND followed_email=?', (me, user_email))
        else:
            c.execute('INSERT OR IGNORE INTO followers (follower_email, followed_email) VALUES (?, ?)', (me, user_email))
        conn.commit()
    finally:
        conn.close()
    # redirect back to the profile of the target user (try to find username)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT username FROM users WHERE email=?', (user_email,))
        r = c.fetchone()
        if r and r[0]:
            return redirect(url_for('profile', username=r[0]))
    finally:
        conn.close()
    return redirect(url_for('home'))


@app.route('/api/followers/<username>')
def api_followers(username):
    # return list of followers for given username
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT email FROM users WHERE username=?', (username,))
        row = c.fetchone()
        if not row:
            return jsonify({'error':'not_found'}), 404
        target_email = row[0]
        c.execute('SELECT follower_email FROM followers WHERE followed_email=?', (target_email,))
        followers = [r[0] for r in c.fetchall()]
        return jsonify({'followers': followers})
    finally:
        conn.close()


@app.route('/api/following/<username>')
def api_following(username):
    # return list of emails this user is following
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT email FROM users WHERE username=?', (username,))
        row = c.fetchone()
        if not row:
            return jsonify({'error':'not_found'}), 404
        user_email = row[0]
        c.execute('SELECT followed_email FROM followers WHERE follower_email=?', (user_email,))
        following = [r[0] for r in c.fetchall()]
        return jsonify({'following': following})
    finally:
        conn.close()


@app.route('/api/chat_contacts')
def api_chat_contacts():
    # Return a list of users who are either following the current user or are followed by them
    if 'user_email' not in session:
        return jsonify({'error': 'unauthenticated'}), 401
    user_email = session['user_email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT follower_email FROM followers WHERE followed_email=?', (user_email,))
        follower_emails = [r[0] for r in c.fetchall()]
        c.execute('SELECT followed_email FROM followers WHERE follower_email=?', (user_email,))
        following_emails = [r[0] for r in c.fetchall()]

        # preserve order and remove duplicates
        emails = []
        for e in follower_emails + following_emails:
            if e and e not in emails and e != user_email:
                emails.append(e)

        contacts = []
        for e in emails:
            c.execute('SELECT id, name, username, avatar_url, email FROM users WHERE email=?', (e,))
            r = c.fetchone()
            if r:
                contacts.append({
                    'id': r[0],
                    'name': (r[1] or r[2] or r[4]),
                    'username': r[2],
                    'avatar_url': r[3],
                    'email': r[4]
                })

        return jsonify({'contacts': contacts})
    finally:
        conn.close()

@app.route("/search_users")
def search_users():
    # Allow searching users by username, name or email.
    # If user is not signed in, still allow searching (useful for public discovery) — but you can enforce session if desired.
    query = request.args.get("q", "").strip().lower()
    if not query:
        return jsonify([])

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        likeq = f"%{query}%"
        c.execute(
            "SELECT username, name, email FROM users WHERE (LOWER(username) LIKE ? OR LOWER(name) LIKE ? OR LOWER(email) LIKE ?) ORDER BY username IS NULL, username LIMIT 10",
            (likeq, likeq, likeq)
        )
        rows = c.fetchall()
        results = []
        for r in rows:
            results.append({
                'username': r[0],
                'name': r[1],
                'email': r[2]
            })
        app.logger.info(f"/search_users q={query} rows={len(rows)}")
    except Exception as e:
        app.logger.exception('search_users error')
        results = []
    finally:
        conn.close()

    return jsonify(results)

@app.route("/feed")
def feed():
    if "user_email" not in session:
        return redirect(url_for("signin"))

    user_email = session["user_email"]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Get posts only from people you follow
    # Note: followers table uses columns follower_email and followed_email
    c.execute("""
        SELECT p.content, u.username, p.timestamp
        FROM posts p
        JOIN users u ON u.email = p.user_email
        JOIN followers f ON f.followed_email = p.user_email
        WHERE f.follower_email = ?
        ORDER BY p.timestamp DESC
    """, (user_email,))

    posts = c.fetchall()
    conn.close()
    return render_template("feed.html", posts=posts)



import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "data.db")


# ---------- Routes ----------

# Sign In (Index page)
@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            # Select explicit columns to avoid index assumptions
            c.execute("SELECT name, email FROM users WHERE LOWER(email)=? AND password=?", (email, password))
            user = c.fetchone()
            conn.close()
        except Exception as e:
            app.logger.exception("Error checking user credentials")
            # Return response and set language cookie if signin supplied it
            from flask import g, make_response
            resp = make_response(render_template("index.html", error="Internal server error"))
            lang = getattr(g, '_set_language', None)
            if lang:
                resp.set_cookie('language', lang, max_age=31536000, path='/')
            return resp

        if user:
            session["user"] = user[0]
            session["user_email"] = user[1]
            app.logger.info(f"User logged in: {email}")
            # On successful signin, persist chosen language (if provided on signin)
            from flask import g, make_response
            resp = make_response(redirect(url_for("home")))
            lang = getattr(g, '_set_language', None)
            if lang:
                resp.set_cookie('language', lang, max_age=31536000, path='/')
            return resp
        else:
            app.logger.info(f"Failed login attempt for: {email}")
            from flask import g, make_response
            resp = make_response(render_template("index.html", error="Invalid email or password"))
            lang = getattr(g, '_set_language', None)
            if lang:
                resp.set_cookie('language', lang, max_age=31536000, path='/')
            return resp

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
    if "user" not in session:
        return redirect(url_for("signin"))

    # Get email from session
    user_email = session.get("user_email")

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT username FROM users WHERE email=?", (user_email,))
    result = c.fetchone()
    conn.close()

    username = result[0] if result else None

    # If username not set in DB, fall back to the session display name
    display_name = username if username else session.get('user', 'User')
    # compute avatar initials (up to 2 letters)
    avatar_text = ''.join([part[0] for part in display_name.split() if part])[:2].upper() if display_name else 'U'

    # log for debugging
    app.logger.info(f"Rendering home for session user={session.get('user')} user_email={session.get('user_email')} db_username={username} display_name={display_name} avatar_text={avatar_text}")

    # Fetch other users to show as stories/suggestions (exclude current user)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT id, name, username, email FROM users WHERE email!=? ORDER BY id DESC LIMIT 12', (user_email,))
        others = c.fetchall()
        # prepare simple structures for template
        users_list = []
        for r in others:
            users_list.append({
                'id': r[0],
                'name': r[1] or r[2] or r[3],
                'username': r[2] or r[3],
                'email': r[3]
            })
    except Exception:
        users_list = []
    finally:
        conn.close()

    return render_template("home.html", username=display_name, avatar_text=avatar_text, stories=users_list, suggestions=users_list)


@app.route('/debug-session')
def debug_session():
    # Return session keys and DB username for the logged-in email
    data = {k: session.get(k) for k in ['user', 'user_email', 'logged_in']}
    user_email = session.get('user_email')
    if user_email:
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT id, name, email, username FROM users WHERE email=?', (user_email,))
            row = c.fetchone()
            conn.close()
            data['db_row_for_email'] = row
        except Exception as e:
            data['db_error'] = str(e)
    return jsonify(data)


@app.route('/api/profile/<username>')
def api_profile(username):
    # return basic profile info as JSON for AJAX/profile modal
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        # Try case-insensitive username lookup
        c.execute('SELECT id, name, email, username FROM users WHERE LOWER(username)=LOWER(?)', (username,))
        row = c.fetchone()
        if not row:
            # fallback: try matching by email or name
            c.execute('SELECT id, name, email, username FROM users WHERE LOWER(email)=LOWER(?) OR LOWER(name)=LOWER(?)', (username, username))
            row = c.fetchone()
            if not row:
                return jsonify({'error': 'not_found'}), 404
        user = {'id': row[0], 'name': row[1], 'email': row[2], 'username': row[3]}
        # compute initials
        display_name = user.get('username') or user.get('name') or user.get('email')
        initials = ''.join([part[0] for part in (display_name or '').split() if part])[:2].upper()
        user['initials'] = initials
        # avatar_url: not stored in DB right now; keep None or generate placeholder later
        user['avatar_url'] = None
        # posts: get recent posts for this user (limit 10)
        try:
            c.execute('SELECT id, content, timestamp FROM posts WHERE user_email=? ORDER BY timestamp DESC LIMIT 10', (user['email'],))
            posts_rows = c.fetchall()
            user['posts'] = [{'id': r[0], 'content': r[1], 'timestamp': r[2]} for r in posts_rows]
        except Exception:
            user['posts'] = []
        # followers/following counts
        try:
            c.execute('SELECT COUNT(1) FROM followers WHERE followed_email=?', (user['email'],))
            user['followers_count'] = c.fetchone()[0] or 0
        except Exception:
            user['followers_count'] = 0
        try:
            c.execute('SELECT COUNT(1) FROM followers WHERE follower_email=?', (user['email'],))
            user['following_count'] = c.fetchone()[0] or 0
        except Exception:
            user['following_count'] = 0
        # is_following? (safe: if followers table missing, treat as not following)
        is_following = False
        if 'user_email' in session:
            follower = session['user_email']
            try:
                c.execute('SELECT 1 FROM followers WHERE follower_email=? AND followed_email=?', (follower, user['email']))
                is_following = bool(c.fetchone())
            except Exception:
                # followers table might not exist yet
                app.logger.debug('followers table missing or query failed; treating as not following')
                is_following = False
        user['is_following'] = is_following
        return jsonify(user)
    except Exception as e:
        app.logger.exception('api_profile error')
        return jsonify({'error': 'server_error'}), 500
    finally:
        conn.close()


@app.route('/i_profile')
def i_profile():
    # Redirect current signed-in user to their profile based on username in DB, or to username setup
    if 'user_email' not in session:
        return redirect(url_for('signin'))
    user_email = session['user_email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT username FROM users WHERE email=?', (user_email,))
        r = c.fetchone()
        if r and r[0]:
            return redirect(url_for('profile', username=r[0]))
        else:
            return redirect(url_for('set_username'))
    finally:
        conn.close()


@app.route('/api/follow/<username>', methods=['POST'])
def api_follow(username):
    if 'user_email' not in session:
        return jsonify({'error': 'unauthenticated'}), 401
    follower = session['user_email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT email FROM users WHERE username=?', (username,))
        row = c.fetchone()
        if not row:
            return jsonify({'error': 'not_found'}), 404
        followed_email = row[0]
        app.logger.info(f"api_follow called: follower={follower} -> followed={followed_email}")
        try:
            c.execute('INSERT INTO followers (follower_email, followed_email) VALUES (?, ?)', (follower, followed_email))
            conn.commit()
        except sqlite3.IntegrityError:
            # already following
            pass
        # return updated counts for the followed user
        try:
            c.execute('SELECT COUNT(1) FROM followers WHERE followed_email=?', (followed_email,))
            followers_count = c.fetchone()[0] or 0
        except Exception:
            followers_count = 0
        try:
            c.execute('SELECT COUNT(1) FROM followers WHERE follower_email=?', (followed_email,))
            following_count = c.fetchone()[0] or 0
        except Exception:
            following_count = 0
        return jsonify({'success': True, 'following': True, 'followers_count': followers_count, 'following_count': following_count})
    except Exception as e:
        app.logger.exception('api_follow error')
        return jsonify({'error': 'server_error'}), 500
    finally:
        conn.close()


@app.route('/api/unfollow/<username>', methods=['POST'])
def api_unfollow(username):
    if 'user_email' not in session:
        return jsonify({'error': 'unauthenticated'}), 401
    follower = session['user_email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('SELECT email FROM users WHERE username=?', (username,))
        row = c.fetchone()
        if not row:
            return jsonify({'error': 'not_found'}), 404
        followed_email = row[0]
        app.logger.info(f"api_unfollow called: follower={follower} -> followed={followed_email}")
        c.execute('DELETE FROM followers WHERE follower_email=? AND followed_email=?', (follower, followed_email))
        conn.commit()
        # return updated counts
        try:
            c.execute('SELECT COUNT(1) FROM followers WHERE followed_email=?', (followed_email,))
            followers_count = c.fetchone()[0] or 0
        except Exception:
            followers_count = 0
        try:
            c.execute('SELECT COUNT(1) FROM followers WHERE follower_email=?', (followed_email,))
            following_count = c.fetchone()[0] or 0
        except Exception:
            following_count = 0
        return jsonify({'success': True, 'following': False, 'followers_count': followers_count, 'following_count': following_count})
    except Exception as e:
        app.logger.exception('api_unfollow error')
        return jsonify({'error': 'server_error'}), 500
    finally:
        conn.close()
@app.before_request
def check_username():
    # Skip for these endpoints to avoid infinite redirects
    skip_endpoints = ['set_username', 'signin', 'signup', 'static', 'logout', 'signup_post']
    if request.endpoint in skip_endpoints:
        return
    
    if 'user_email' in session:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT username FROM users WHERE email=?", (session['user_email'],))
        result = c.fetchone()
        conn.close()

        # If no username exists, redirect to set_username
        if not result or not result[0]:
            return redirect(url_for('set_username'))



@app.route("/set_username", methods=["GET", "POST"])
def set_username():
    if "user_email" not in session:
        return redirect(url_for("signin"))

    if request.method == "POST":
        new_username = request.form["username"].strip().lower()

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # Ensure unique username
        c.execute("SELECT id FROM users WHERE username=?", (new_username,))
        exists = c.fetchone()
        if exists:
            conn.close()
            return "<h3>Username already taken!</h3><p><a href='/set_username'>Try again</a></p>"

        c.execute("UPDATE users SET username=? WHERE email=?", (new_username, session["user_email"]))
        conn.commit()
        conn.close()
        return redirect(url_for("home"))

    return render_template("set_username.html")

@app.route("/invite", methods=["GET", "POST"])
def invite():
    if "user_email" not in session:
        return redirect(url_for("signin"))

    if request.method == "POST":
        receiver = request.form["receiver"].strip().lower()
        sender = session["user_email"]

        # Determine if it's an email or username
        invite_type = "email" if "@" in receiver else "username"

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO invites (sender, receiver, type) VALUES (?, ?, ?)",
                  (sender, receiver, invite_type))
        conn.commit()
        conn.close()

        return "<h3>Invite sent successfully!</h3><p><a href='/home'>Back to Home</a></p>"

    return render_template("invite.html")

    # Keep chat history in memory (demo)
chats = {
    'general': []
}

@app.route('/')
def index():
    return render_template('chat.html')




@app.route('/explore')
def explore():
    # Simple explore page placeholder
    return render_template('explore.html')


@app.route('/notifications')
def notifications():
    # Simple notifications placeholder
    if 'user_email' not in session:
        return redirect(url_for('signin'))
    # For now, return an empty list
    return render_template('notifications.html', notifications=[])


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_email' not in session:
        return redirect(url_for('signin'))
    user_email = session['user_email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if request.method == 'POST':
        new_name = request.form.get('name','').strip()
        new_email = request.form.get('email','').strip().lower()
        # update
        try:
            c.execute('UPDATE users SET name=?, email=? WHERE email=?', (new_name, new_email, user_email))
            conn.commit()
            # update session if email changed
            session['user_email'] = new_email
            session['user'] = new_name or session.get('user')
        except Exception:
            app.logger.exception('Could not update settings')
        finally:
            conn.close()
        return redirect(url_for('settings'))
    else:
        c.execute('SELECT name, email, username FROM users WHERE email=?', (user_email,))
        r = c.fetchone()
        conn.close()
        name = r[0] if r else ''
        email = r[1] if r else user_email
        return render_template('settings.html', name=name, email=email)


@app.route('/create')
def create():
    if 'user_email' not in session:
        return redirect(url_for('signin'))
    return render_template('create.html')


# SocketIO events
@socketio.on('join')
def handle_join(data):
    room = data['room']
    join_room(room)
    emit('status', {'msg': f"{data['username']} has joined the room."}, room=room)

@socketio.on('send_message')
def handle_message(data):
    room = data['room']
    msg = {'username': data['username'], 'text': data['text']}
    if room not in chats:
        chats[room] = []
    chats[room].append(msg)
    emit('receive_message', msg, room=room)


    

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data.db')

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# Ensure users table exists
c.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT UNIQUE,
    password TEXT,
    username TEXT
)
''')

# Insert test user
try:
    c.execute("INSERT INTO users (name, email, password) VALUES (?, ?, ?)", ('Demo User', 'demo@example.com', 'password123'))
    conn.commit()
    print('Test user created: demo@example.com / password123')
except Exception as e:
    print('Could not create test user (maybe already exists):', e)

conn.close()







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




@app.route('/_routes')
def list_routes():
    # Diagnostic endpoint: returns a list of registered routes (method and rule)
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({'rule': str(rule), 'endpoint': rule.endpoint, 'methods': sorted(list(rule.methods))})
    return jsonify({'routes': routes})


    






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

# ✅ Store active games
games = {}

def generate_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ---------- Routes ----------
from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room
import random, string


app.config["SECRET_KEY"] = "mysecretkey"

# Store active games
games = {}

def generate_code(length=5):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

# ---------- Routes ----------
@app.route("/lobby")
def lobby():
    return render_template("index.html")   # Lobby (create/join)

  # Board UI

  

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
# ✅ Enhanced translation dictionary (only English, Turkish, Urdu)
# ✅ Enhanced translation dictionary (only English, Turkish, Urdu)
# ✅ Enhanced translation dictionary (only English, Turkish, Urdu)
# ✅ Enhanced translation dictionary (only English, Turkish, Urdu)
translations = {
    # Navigation and UI elements
    "Submit Form": {"tr": "Formu Gönder", "ur": "فارم جمع کروائیں"},
    "BeautifulForms": {"tr": "Güzel Formlar", "ur": "خوبصورت فارمز"},
    "Admin": {"tr": "Yönetici", "ur": "ایڈمن"},
    "Submit your data": {"tr": "Verilerinizi Gönderin", "ur": "اپنا ڈیٹا جمع کروائیں"},
    "Sign In": {"tr": "Giriş Yap", "ur": "سائن ان"},
    "Email": {"tr": "E-posta", "ur": "ای میل"},
    "Password": {"tr": "Şifre", "ur": "پاس ورڈ"},
    "Login": {"tr": "Giriş", "ur": "لاگ ان"},
    "Don't have an account?": {"tr": "Hesabınız yok mu?", "ur": "کیا آپ کے پاس اکاؤنٹ نہیں ہے؟"},
    "Sign Up": {"tr": "Kaydol", "ur": "سائن اپ"},
    "All rights reserved.": {"tr": "Tüm hakları saklıdır.", "ur": "جملہ حقوق محفوظ ہیں"},
    "Contact us": {"tr": "Bize Ulaşın", "ur": "ہم سے رابطہ کریں"},
    "Hello World": {"tr": "Merhaba Dünya", "ur": "ہیلو ورلڈ"},

    # Admin panel
    "ID": {"tr": "ID", "ur": "آئی ڈی"},
    "Name": {"tr": "İsim", "ur": "نام"},
    "Actions": {"tr": "İşlemler", "ur": "اعمال"},
    "Edit": {"tr": "Düzenle", "ur": "ترمیم"},
    "Delete": {"tr": "Sil", "ur": "حذف کریں"},
    "Login to manage": {"tr": "Yönetmek için giriş yapın", "ur": "انتظام کے لیے لاگ ان کریں"},
    "No users found": {"tr": "Kullanıcı bulunamadı", "ur": "کوئی صارف نہیں ملا"},
    "Back to Form": {"tr": "Forma Geri Dön", "ur": "فارم پر واپس جائیں"},
    "Manage users": {"tr": "Kullanıcıları Yönet", "ur": "صارفین کا انتظام"},
    "Admin Login": {"tr": "Yönetici Girişi", "ur": "ایڈمن لاگ ان"},
    "User ID": {"tr": "Kullanıcı ID", "ur": "صارف کی آئی ڈی"},
    "Admin User ID": {"tr": "Yönetici Kullanıcı ID", "ur": "ایڈمن صارف کی آئی ڈی"},
    "Your Password": {"tr": "Şifreniz", "ur": "آپ کا پاس ورڈ"},
    "Secure admin area - Unauthorized access prohibited": {
        "tr": "Güvenli yönetici alanı - Yetkisiz erişim yasaktır",
        "ur": "محفوظ ایڈمن ایریا - غیر مجاز رسائی ممنوع ہے"
    },

    # Game
    "Tic Tac Toe": {"tr": "XOX Oyunu", "ur": "ٹک ٹیک ٹو"},
    "Choose Game Mode": {"tr": "Oyun Modunu Seçin", "ur": "گیم موڈ منتخب کریں"},
    "Single Player": {"tr": "Tek Oyuncu", "ur": "سنگل پلیئر"},
    "1 Device (Local 2 Players)": {"tr": "1 Cihaz (Yerel 2 Oyuncu)", "ur": "1 ڈیوائس (لوکل 2 کھلاڑی)"},
    "2 Devices (Online Multiplayer)": {"tr": "2 Cihaz (Çevrimiçi Çoklu Oyunculu)", "ur": "2 ڈیوائسز (آن لائن ملٹی پلیئر)"},
    "Online Multiplayer": {"tr": "Çevrimiçi Çoklu Oyunculu", "ur": "آن لائن ملٹی پلیئر"},
    "Create New Game": {"tr": "Yeni Oyun Oluştur", "ur": "نیا گیم بنائیں"},
    "Enter Game Code": {"tr": "Oyun Kodunu Girin", "ur": "گیم کوڈ درج کریں"},
    "Join Game": {"tr": "Oyuna Katıl", "ur": "گیم میں شامل ہوں"},
    "Game Board": {"tr": "Oyun Tahtası", "ur": "گیم بورڈ"},
    "Reset Game": {"tr": "Oyunu Sıfırla", "ur": "گیم ری سیٹ کریں"},
    "Back to Menu": {"tr": "Menüye Dön", "ur": "مینو پر واپس جائیں"},
    "Congratulations": {"tr": "Tebrikler", "ur": "مبارک ہو"},
    "Player X's Turn": {"tr": "X Oyuncusunun Sırası", "ur": "کھلاڑی X کی باری"},
    "Player O's Turn": {"tr": "O Oyuncusunun Sırası", "ur": "کھلاڑی O کی باری"},

    # AI page
    "AI Assistant": {"tr": "Yapay Zeka Asistanı", "ur": "AI اسسٹنٹ"},
    "Powered by Zia Ur Rahman via Help of Chatgpt and DeepSeek": {
        "tr": "Zia Ur Rahman tarafından Chatgpt ve DeepSeek yardımıyla desteklenmektedir", 
        "ur": "Zia Ur Rahman کی جانب سے Chatgpt اور DeepSeek کی مدد سے طاقت یافتہ"
    },
    "Type your message here...": {"tr": "Mesajınızı buraya yazın...", "ur": "اپنا پیغام یہاں ٹائپ کریں..."},
    "Send": {"tr": "Gönder", "ur": "بھیجیں"},
    "Thinking": {"tr": "Düşünüyor", "ur": "سوچ رہا ہے"},
    "Checking API status...": {"tr": "API durumu kontrol ediliyor...", "ur": "API کی حیثیت چیک کی جا رہی ہے..."},
    "API Online": {"tr": "API Çevrimiçi", "ur": "API آن لائن"},
    "API Offline": {"tr": "API Çevrimdışı", "ur": "API آف لائن"},
    "Connection Error": {"tr": "Bağlantı Hatası", "ur": "کنیکشن ایرر"},

    # Home page
    "Home": {"tr": "Ana Sayfa", "ur": "ہوم"},
    "About Me": {"tr": "Hakkımda", "ur": "میرے بارے میں"},
    "Contact": {"tr": "İletişim", "ur": "رابطہ"},
    "Welcome To Xia-09's Corner": {"tr": "Xia-09 Köşesine Hoşgeldiniz", "ur": "Xia-09 کے کونے میں خوش آمدید"},
    "Choose Any Game": {"tr": "Herhangi bir oyun seçin", "ur": "کوئی بھی کھیل منتخب کریں"},
    "Perenoid": {"tr": "Perenoid", "ur": "پیرینوئڈ"},
    "AI": {"tr": "YZ", "ur": "AI"},
    "Game": {"tr": "Oyun", "ur": "کھیل"},

    # Profile and Social
    "Create Account": {"tr": "Hesap Oluştur", "ur": "اکاؤنٹ بنائیں"},
    "Full Name": {"tr": "Tam Ad", "ur": "مکمل نام"},
    "Already have an account?": {"tr": "Zaten hesabınız var mı?", "ur": "کیا آپ کے پاس پہلے سے اکاؤنٹ ہے؟"},
    "Sign In": {"tr": "Giriş Yap", "ur": "سائن ان"},
    "Your Feed": {"tr": "Akışınız", "ur": "آپ کی فیڈ"},
    "What's on your mind?": {"tr": "Aklınızda ne var?", "ur": "آپ کے ذہن میں کیا ہے؟"},
    "Post": {"tr": "Gönder", "ur": "پوسٹ کریں"},
    "No posts yet. Follow users to see their posts!": {
        "tr": "Henüz gönderi yok. Gönderileri görmek için kullanıcıları takip edin!", 
        "ur": "ابھی تک کوئی پوسٹ نہیں۔ ان کی پوسٹس دیکھنے کے لیے صارفین کو فالو کریں!"
    },
    "Followers": {"tr": "Takipçiler", "ur": "فالوورز"},
    "Following": {"tr": "Takip Edilenler", "ur": "فالو کر رہے ہیں"},
    "No followers yet.": {"tr": "Henüz takipçi yok.", "ur": "ابھی تک کوئی فالوور نہیں۔"},
    "Not following anyone yet.": {"tr": "Henüz kimseyi takip etmiyorsunuz.", "ur": "ابھی تک کسی کو فالو نہیں کر رہے۔"},

    # Chat
    "Chats": {"tr": "Sohbetler", "ur": "چیٹس"},
    "Load followers/following": {"tr": "Takipçileri/takip edilenleri yükle", "ur": "فالوورز/فالو کرنے والوں کو لوڈ کریں"},
    "Search contacts": {"tr": "Kişileri ara", "ur": "رابطے تلاش کریں"},
    "Select a chat": {"tr": "Bir sohbet seçin", "ur": "ایک چیٹ منتخب کریں"},
    "Type a message...": {"tr": "Bir mesaj yazın...", "ur": "ایک پیغام ٹائپ کریں..."},

    # Edit User
    "Edit User": {"tr": "Kullanıcıyı Düzenle", "ur": "صارف میں ترمیم کریں"},
    "Update": {"tr": "Güncelle", "ur": "اپ ڈیٹ کریں"},
    "Cancel": {"tr": "İptal", "ur": "منسوخ کریں"},
    "All Users": {"tr": "Tüm Kullanıcılar", "ur": "تمام صارفین"},

    # Invite
    "Send an Invite": {"tr": "Davetiye Gönder", "ur": "دعوت نامہ بھیجیں"},
    "Enter Gmail ID or Username": {"tr": "Gmail ID veya Kullanıcı Adı Girin", "ur": "Gmail ID یا صارف نام درج کریں"},
    "Send Invite": {"tr": "Davetiye Gönder", "ur": "دعوت نامہ بھیجیں"},
    "Back to Home": {"tr": "Ana Sayfaya Dön", "ur": "ہوم پر واپس جائیں"},

    # Set Username
    "Choose your username": {"tr": "Kullanıcı adınızı seçin", "ur": "اپنا صارف نام منتخب کریں"},
    "Enter username": {"tr": "Kullanıcı adını girin", "ur": "صارف نام درج کریں"},
    "Save": {"tr": "Kaydet", "ur": "محفوظ کریں"},

    # Game messages
    "Single Player Mode": {"tr": "Tek Oyuncu Modu", "ur": "سنگل پلیئر موڈ"},
    "Local Multiplayer Game": {"tr": "Yerel Çoklu Oyunculu Oyun", "ur": "لوکل ملٹی پلیئر گیم"},
    "Create or join an online game": {"tr": "Çevrimiçi oyun oluşturun veya katılın", "ur": "آن لائن گیم بنائیں یا شامل ہوں"},
    "Creating game...": {"tr": "Oyun oluşturuluyor...", "ur": "گیم بنائی جا رہی ہے..."},
    "Waiting for another player to join...": {"tr": "Başka bir oyuncunun katılması bekleniyor...", "ur": "دوسرے کھلاڑی کے شامل ہونے کا انتظار..."},
    "Game started!": {"tr": "Oyun başladı!", "ur": "گیم شروع ہو گئی!"},
    "It's a tie!": {"tr": "Berabere!", "ur": "یہ ایک ٹائی ہے!"},
    "Player X wins!": {"tr": "X Oyuncusu kazandı!", "ur": "کھلاڑی X جیت گیا!"},
    "Player O wins!": {"tr": "O Oyuncusu kazandı!", "ur": "کھلاڑی O جیت گیا!"},
    "Your Turn (X)": {"tr": "Sıranız (X)", "ur": "آپ کی باری (X)"},
    "AI's Turn (O)": {"tr": "YZ'nin Sırası (O)", "ur": "AI کی باری (O)"},

    # Error messages
    "Invalid email or password": {"tr": "Geçersiz e-posta veya şifre", "ur": "غلط ای میل یا پاس ورڈ"},
    "Email already exists!": {"tr": "E-posta zaten mevcut!", "ur": "ای میل پہلے سے موجود ہے!"},
    "Username already taken!": {"tr": "Kullanıcı adı zaten alınmış!", "ur": "صارف نام پہلے سے لیا جا چکا ہے!"},
    "User not found": {"tr": "Kullanıcı bulunamadı", "ur": "صارف نہیں ملا"},
    "Network error: Could not connect to the AI service.": {
        "tr": "Ağ hatası: YZ servisine bağlanılamadı.", 
        "ur": "نیٹ ورک ایرر: AI سروس سے رابطہ نہیں ہو سکا۔"
    }
}
# Add this to your existing app.py - Enhanced styling and features
@app.context_processor
def inject_global_vars():
    return {
        'site_name': 'SocialSphere',
        'current_year': 2024
    }

# Enhanced translation dictionary with more social media terms
translations.update({
    "SocialSphere": {"tr": "SocialSphere", "ur": "سوشل اسفیئر"},
    "Discover amazing content": {"tr": "Harika içerikleri keşfedin", "ur": "شاندار مواد دریافت کریں"},
    "Join our community": {"tr": "Topluluğumuza katılın", "ur": "ہماری کمیونٹی میں شامل ہوں"},
    "Share your moments": {"tr": "Anılarınızı paylaşın", "ur": "اپنے لمحات شیئر کریں"},
    "Connect with friends": {"tr": "Arkadaşlarınızla bağlantı kurun", "ur": "دوستوں کے ساتھ رابطہ قائم کریں"},
    "Explore": {"tr": "Keşfet", "ur": "دریافت کریں"},
    "Notifications": {"tr": "Bildirimler", "ur": "اطلاعات"},
    "Messages": {"tr": "Mesajlar", "ur": "پیغامات"},
    "Profile": {"tr": "Profil", "ur": "پروفائل"},
    "Settings": {"tr": "Ayarlar", "ur": "ترتیبات"},
    "Logout": {"tr": "Çıkış Yap", "ur": "لاگ آؤٹ"},
    "Create Post": {"tr": "Gönderi Oluştur", "ur": "پوسٹ بنائیں"},
    "Like": {"tr": "Beğen", "ur": "پسند کریں"},
    "Comment": {"tr": "Yorum Yap", "ur": "تبصرہ کریں"},
    "Share": {"tr": "Paylaş", "ur": "شیئر کریں"},
    "Save": {"tr": "Kaydet", "ur": "محفوظ کریں"},
    "Follow": {"tr": "Takip Et", "ur": "فالو کریں"},
    "Unfollow": {"tr": "Takibi Bırak", "ur": "انفالو کریں"},
    "Edit Profile": {"tr": "Profili Düzenle", "ur": "پروفائل میں ترمیم کریں"},
})

# ✅ Translate plain text
def translate_text(text, lang):
    allowed = {'en', 'tr', 'ur'}
    if lang not in allowed:
        lang = 'en'
    if text in translations and lang in translations[text]:
        return translations[text][lang]
    return text

# ✅ Translate full HTML content
def translate_html(html_content, lang):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html_content, 'html.parser')

    # Translate input placeholders and values
    for inp in soup.find_all('input'):
        for attr in ['placeholder', 'value']:
            if inp.get(attr):
                tr = translate_text(inp[attr].strip(), lang)
                if tr != inp[attr]:
                    inp[attr] = tr

    # Translate textarea placeholders
    for textarea in soup.find_all('textarea'):
        if textarea.get('placeholder'):
            tr = translate_text(textarea['placeholder'].strip(), lang)
            if tr != textarea['placeholder']:
                textarea['placeholder'] = tr

    # Translate button text
    for button in soup.find_all('button'):
        if button.string:
            tr = translate_text(button.string.strip(), lang)
            if tr != button.string:
                button.string = tr

    # Translate visible text (ignore scripts, styles, meta, etc.)
    SKIP = {'script', 'style', 'meta', 'head', 'link', '[document]'}
    for node in soup.find_all(string=True):
        parent = getattr(node.parent, 'name', None)
        if parent and parent.lower() in SKIP:
            continue
        text = node.string.strip() if node.string else ''
        if not text:
            continue
        tr = translate_text(text, lang)
        if tr != text:
            node.replace_with(tr)

    return str(soup)




# ✅ Automatically translate every HTML response
@app.after_request
def translate_response(response):
    content_type = (response.content_type or '').lower()
    if content_type.startswith('text/html'):
        lang = request.cookies.get('language', 'en')
        if lang not in ('en', 'tr', 'ur'):
            lang = 'en'
        content = response.get_data(as_text=True)
        translated = translate_html(content, lang)
        response.set_data(translated)
    return response


from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import SocketIO, emit, join_room
import uuid
import smtplib
from email.mime.text import MIMEText


# Store user data
users = {}  # {session_id: {"username": "..."}}
messages = []  # store chat messages in memory

@app.route('/chat-lobby')
def Chats():
    # If user already has a username, go to chat
    if 'user_id' in session and session['user_id'] in users:
        return redirect(url_for('chat'))
    return render_template('index.html')


@app.route('/chat')
def chat():
    if 'user_id' not in session or session['user_id'] not in users:
        return redirect(url_for('index'))
    return render_template('chat.html', username=users[session['user_id']]['username'])

# --- Email Invite Feature ---



# --- Real-Time Chat ---
@socketio.on('send_message')
def handle_message(data):
    username = users[session['user_id']]['username']
    msg = {'user': username, 'text': data['message']}
    messages.append(msg)
    emit('receive_message', msg, broadcast=True)








from flask import redirect, url_for, session



@app.route("/me")
def me_profile():   
    if 'user_email' not in session:
        return redirect(url_for('signin'))
    user_email = session['user_email']
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT name, email, username FROM users WHERE email=?', (user_email,))
    r = c.fetchone()
    conn.close()
    name = r[0] if r else ''
    email = r[1] if r else user_email
    username = r[2] if r and r[2] else 'No username set'
    return render_template('profile.html', name=name, email=email, username=username)




@app.route("/game")
def game():
    return render_template("game.html")





# ---------- Run ----------

# ---------- Run ----------
if __name__ == "__main__":
    import eventlet
    port = int(os.environ.get("PORT", 5000))
    # Disable Flask's reloader when running SocketIO to avoid binding the same port twice
    socketio.run(app, host="0.0.0.0", port=port, debug=True, use_reloader=False)

    from datetime import datetime, timedelta

# Custom Jinja2 filters
@app.template_filter('date')
def custom_date_filter(dummy, format_string='%Y-%m-%d', years_offset=0):
    """Handle the date filter used in templates"""
    target_date = datetime.now() + timedelta(days=years_offset * 365)
    return target_date.strftime(format_string)