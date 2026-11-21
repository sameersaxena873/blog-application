import os
import sqlite3
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "blog.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me")


# ---------- Database helpers ----------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DATABASE)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            author_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)
    db.commit()
    db.close()


# ---------- Auth helpers ----------

def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute(
        "SELECT id, username FROM users WHERE id = ?", (uid,)
    ).fetchone()


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if current_user() is None:
            flash("Please log in first.", "error")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------- Template helpers ----------

@app.template_filter("paragraphs")
def paragraphs(text):
    return [p.strip() for p in text.split("\n\n") if p.strip()]


# ---------- Post helpers ----------

def get_post_or_404(post_id):
    post = get_db().execute("""
        SELECT posts.*, users.username
        FROM posts JOIN users ON users.id = posts.author_id
        WHERE posts.id = ?
    """, (post_id,)).fetchone()
    if post is None:
        abort(404)
    return post


def read_post_form():
    title = request.form.get("title", "").strip()
    content = request.form.get("content", "").strip()
    if not title or not content:
        return None, None, "Title and content are required."
    return title, content, None


# ---------- Public routes ----------

@app.route("/")
def index():
    posts = get_db().execute("""
        SELECT posts.id, posts.title, posts.content, posts.created_at,
               users.username
        FROM posts JOIN users ON users.id = posts.author_id
        ORDER BY posts.created_at DESC
    """).fetchall()
    return render_template("index.html", posts=posts)


@app.route("/post/<int:post_id>")
def show_post(post_id):
    post = get_post_or_404(post_id)
    return render_template("post.html", post=post)


# ---------- Auth routes ----------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3 or len(password) < 6:
            flash("Username needs 3+ characters and password needs 6+.", "error")
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                db.commit()
                flash("Account created. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username is already taken.", "error")

    return render_template("auth.html", heading="Create an account",
                           action=url_for("register"), button="Sign up")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            flash(f"Welcome back, {user['username']}!", "success")
            next_url = request.args.get("next", "")
            # Only allow relative redirects inside this site
            if next_url.startswith("/") and not next_url.startswith("//"):
                return redirect(next_url)
            return redirect(url_for("index"))
        flash("Wrong username or password.", "error")

    return render_template("auth.html", heading="Log in",
                           action=url_for("login"), button="Log in")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# ---------- Post management routes ----------

@app.route("/new", methods=["GET", "POST"])
@login_required
def new_post():
    if request.method == "POST":
        title, content, error = read_post_form()
        if error:
            flash(error, "error")
            return render_template("form.html", post=request.form,
                                   heading="New post", button="Publish")
        db = get_db()
        cur = db.execute(
            "INSERT INTO posts (title, content, author_id) VALUES (?, ?, ?)",
            (title, content, current_user()["id"]),
        )
        db.commit()
        flash("Post published.", "success")
        return redirect(url_for("show_post", post_id=cur.lastrowid))

    return render_template("form.html", post=None,
                           heading="New post", button="Publish")


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = get_post_or_404(post_id)
    if post["author_id"] != current_user()["id"]:
        abort(403)

    if request.method == "POST":
        title, content, error = read_post_form()
        if error:
            flash(error, "error")
            return render_template("form.html", post=request.form,
                                   heading="Edit post", button="Save changes")
        db = get_db()
        db.execute(
            "UPDATE posts SET title = ?, content = ?, updated_at = CURRENT_TIMESTAMP "
            "WHERE id = ?",
            (title, content, post_id),
        )
        db.commit()
        flash("Changes saved.", "success")
        return redirect(url_for("show_post", post_id=post_id))

    return render_template("form.html", post=post,
                           heading="Edit post", button="Save changes")


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = get_post_or_404(post_id)
    if post["author_id"] != current_user()["id"]:
        abort(403)
    db = get_db()
    db.execute("DELETE FROM posts WHERE id = ?", (post_id,))
    db.commit()
    flash("Post deleted.", "success")
    return redirect(url_for("index"))


@app.errorhandler(403)
def forbidden(e):
    return render_template("error.html", code=403,
                           message="You can only change your own posts."), 403


@app.errorhandler(404)
def not_found(e):
    return render_template("error.html", code=404,
                           message="We could not find that page."), 404


# Create tables when the app starts (safe to run multiple times)
init_db()


if __name__ == "__main__":
    app.run(debug=True)
