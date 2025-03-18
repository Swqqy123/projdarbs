from flask import Flask, request, render_template, redirect, url_for, session, jsonify
import sqlite3
import requests
from urllib.parse import quote
import os

app = Flask(__name__)
app.secret_key = os.urandom(24)

def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS favorites
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER NOT NULL,
                  book_id TEXT NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE(user_id, book_id))''')
    
    conn.commit()
    conn.close()

init_db()

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    error = None
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirmPassword']

        if password != confirm_password:
            error = "Passwords do not match!"
            return render_template('signup.html', error=error)

        if len(password) < 8:
            error = "Password must be at least 8 characters long."
            return render_template('signup.html', error=error)
        if not any(c.isupper() for c in password):
            error = "Password must contain at least one uppercase letter."
            return render_template('signup.html', error=error)
        if not any(c.islower() for c in password):
            error = "Password must contain at least one lowercase letter."
            return render_template('signup.html', error=error)

        try:
            conn = sqlite3.connect('users.db')
            c = conn.cursor()
            c.execute("INSERT INTO users (email, password) VALUES (?, ?)", 
                     (email, password))
            conn.commit()
            user_id = c.lastrowid
            session['user_id'] = user_id
            return redirect(url_for('generator'))
        except sqlite3.IntegrityError:
            error = "Email already exists!"
        finally:
            conn.close()

    return render_template('signup.html', error=error)

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND password=?", 
                 (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            session['user_id'] = user[0]
            return redirect(url_for('generator'))
        else:
            error = "Invalid credentials!"

    return render_template('login.html', error=error)

@app.route("/logout")
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

@app.route("/generator")
def generator():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template("generator.html")

@app.route("/generate", methods=['POST'])
def generate():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    genres = request.form['genres']
    start_index = int(request.form.get('start_index', 0))
    books, total_books = fetch_books(genres, start_index)
    books = check_favorites(session['user_id'], books)
    
    return render_template('books.html',
                         genres=genres,
                         books=books,
                         start_index=start_index,
                         total_books=total_books)

@app.route("/favorites")
def view_favorites():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    favorites = get_favorited_books(user_id)
    
    return render_template('books.html',
                         genres="Favorites",
                         books=favorites,
                         start_index=0,
                         total_books=len(favorites))

def fetch_books(genres, start_index):
    try:
        response = requests.get(
            f"https://www.googleapis.com/books/v1/volumes?"
            f"q=subject:{quote(genres)}&"
            f"startIndex={start_index}&"
            f"maxResults=10"
        )
        data = response.json()
    except Exception as e:
        print(f"API Error: {str(e)}")
        return [], 0

    books = []
    seen_ids = set()

    if 'items' in data:
        for item in data['items']:
            volume = item.get('volumeInfo', {})
            book_id = item.get('id', '')
            
            if book_id in seen_ids:
                continue
            seen_ids.add(book_id)

            pub_date = volume.get('publishedDate', '')
            pub_year = pub_date[:4] if pub_date and len(pub_date) >=4 else 'Unknown'
            thumbnail = volume.get('imageLinks', {}).get('thumbnail', 
                url_for('static', filename='default-book.jpg'))
            
            books.append({
                "id": book_id,
                "author": ', '.join(volume.get('authors', ['Unknown'])),
                "name": volume.get('title', 'No Title'),
                "thumbnail": thumbnail,
                "release_year": pub_year
            })

    return books, data.get('totalItems', 0)

def check_favorites(user_id, books):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        book_ids = [book['id'] for book in books]
        placeholders = ','.join(['?'] * len(book_ids))
        query = f"SELECT book_id FROM favorites WHERE user_id = ? AND book_id IN ({placeholders})"
        c.execute(query, [user_id] + book_ids)
        favorited_ids = {row[0] for row in c.fetchall()}
        
        for book in books:
            book['is_favorited'] = book['id'] in favorited_ids
    finally:
        conn.close()
    return books

def get_favorited_books(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    try:
        c.execute("SELECT book_id FROM favorites WHERE user_id = ?", (user_id,))
        book_ids = [row[0] for row in c.fetchall()]
        
        favorites = []
        for book_id in book_ids:
            response = requests.get(f"https://www.googleapis.com/books/v1/volumes/{book_id}")
            if response.status_code == 200:
                item = response.json()
                volume = item.get('volumeInfo', {})
                pub_date = volume.get('publishedDate', '')
                pub_year = pub_date[:4] if pub_date and len(pub_date) >=4 else 'Unknown'
                
                favorites.append({
                    "id": book_id,
                    "author": ', '.join(volume.get('authors', ['Unknown'])),
                    "name": volume.get('title', 'No Title'),
                    "thumbnail": volume.get('imageLinks', {}).get('thumbnail', 
                                url_for('static', filename='default-book.jpg')),
                    "release_year": pub_year,
                    "is_favorited": True
                })
        return favorites
    finally:
        conn.close()

@app.route("/favorite", methods=['POST'])
def favorite_book():
    if 'user_id' not in session:
        return jsonify({"error": "Unauthorized"}), 401
        
    user_id = session['user_id']
    data = request.json
    book_id = data.get('book_id')
    action = data.get('action')

    conn = sqlite3.connect('users.db')
    try:
        if action == 'add':
            conn.execute("INSERT OR IGNORE INTO favorites (user_id, book_id) VALUES (?, ?)",
                        (user_id, book_id))
        elif action == 'remove':
            conn.execute("DELETE FROM favorites WHERE user_id = ? AND book_id = ?",
                        (user_id, book_id))
        conn.commit()
        return jsonify({"success": True, "is_favorited": action == 'add'})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(debug=True)