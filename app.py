from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import sqlite3
import requests
from urllib.parse import quote
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_db_connection():
    return sqlite3.connect('users.db', check_same_thread=False)

def init_db():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, email TEXT UNIQUE NOT NULL, password TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS favorites (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, book_id TEXT NOT NULL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(user_id, book_id))''')
        conn.commit()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email, password, confirm_password = request.form['email'], request.form['password'], request.form['confirmPassword']
        if password != confirm_password or len(password) < 8 or not any(c.isupper() for c in password) or not any(c.islower() for c in password):
            return render_template('signup.html', error="Invalid password!")
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
                c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
                session['user_id'] = c.lastrowid
                return redirect(url_for('generator'))
        except sqlite3.IntegrityError:
            return render_template('signup.html', error="Email already exists!")
    return render_template('signup.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email, password = request.form['username'], request.form['password']
        with get_db_connection() as conn:
            user = conn.execute("SELECT id FROM users WHERE email=? AND password=?", (email, password)).fetchone()
        if user:
            session['user_id'] = user[0]
            return redirect(url_for('generator'))
        return render_template('login.html', error="Invalid credentials!")
    return render_template('login.html')

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route("/generator")
def generator():
    return redirect(url_for('login')) if 'user_id' not in session else render_template("generator.html")

@app.route("/generate", methods=['POST'])
def generate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    genres, start_index = request.form['genres'], int(request.form.get('start_index', 0))
    books, total_books = fetch_books(genres, start_index)
    return render_template('books.html', genres=genres, books=check_favorites(session['user_id'], books), start_index=start_index, total_books=total_books)

@app.route("/favorites")
def view_favorites():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('books.html', genres="Favorites", books=get_favorited_books(session['user_id']), start_index=0, total_books=0)

def fetch_books(genres, start_index):
    try:
        data = requests.get(f"https://www.googleapis.com/books/v1/volumes?q=subject:{quote(genres)}&startIndex={start_index}&maxResults=10").json()
    except Exception as e:
        print(f"API Error: {e}")
        return [], 0
    books = [{
        "id": item['id'],
        "author": ', '.join(item.get('volumeInfo', {}).get('authors', ['Unknown'])),
        "name": item.get('volumeInfo', {}).get('title', 'No Title'),
        "thumbnail": item.get('volumeInfo', {}).get('imageLinks', {}).get('thumbnail', url_for('static', filename='default-book.jpg')),
        "release_year": item.get('volumeInfo', {}).get('publishedDate', 'Unknown')[:4]
    } for item in data.get('items', [])]
    return books, data.get('totalItems', 0)

def check_favorites(user_id, books):
    with get_db_connection() as conn:
        favorited_ids = {row[0] for row in conn.execute("SELECT book_id FROM favorites WHERE user_id = ?", (user_id,)).fetchall()}
    for book in books:
        book['is_favorited'] = book['id'] in favorited_ids
    return books

def get_favorited_books(user_id):
    with get_db_connection() as conn:
        book_ids = [row[0] for row in conn.execute("SELECT book_id FROM favorites WHERE user_id = ?", (user_id,)).fetchall()]
    return fetch_books_by_ids(book_ids)

def fetch_books_by_ids(book_ids):
    books = []
    for book_id in book_ids:
        response = requests.get(f"https://www.googleapis.com/books/v1/volumes/{book_id}")
        if response.status_code == 200:
            item = response.json()
            volume = item.get('volumeInfo', {})
            books.append({
                "id": book_id,
                "author": ', '.join(volume.get('authors', ['Unknown'])),
                "name": volume.get('title', 'No Title'),
                "thumbnail": volume.get('imageLinks', {}).get('thumbnail', url_for('static', filename='default-book.jpg')),
                "release_year": volume.get('publishedDate', 'Unknown')[:4],
                "is_favorited": True
            })
    return books

@app.route("/favorite", methods=['POST'])
def favorite_book():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
    user_id, data = session['user_id'], request.json
    try:
        with get_db_connection() as conn:
            if data.get('action') == 'add':
                conn.execute("INSERT OR IGNORE INTO favorites (user_id, book_id) VALUES (?, ?)", (user_id, data['book_id']))
            elif data.get('action') == 'remove':
                conn.execute("DELETE FROM favorites WHERE user_id = ? AND book_id = ?", (user_id, data['book_id']))
            conn.commit()
        return jsonify({"success": True, "is_favorited": data.get('action') == 'add'})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
