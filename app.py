from flask import Flask, request, render_template, redirect, url_for, jsonify
import sqlite3
import requests
from urllib.parse import quote
import bcrypt  # Added for password hashing

app = Flask(__name__)

# Initialize database with proper schema
def init_db():
    with sqlite3.connect('users.db') as conn:
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                     (email TEXT PRIMARY KEY, password TEXT)''')

init_db()

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password'].encode('utf-8')  # Convert to bytes
        confirm_password = request.form['confirmPassword']

        if password != confirm_password.encode('utf-8'):
            return "Passwords do not match!"

        try:
            # Generate salt and hash password
            salt = bcrypt.gensalt()
            hashed_password = bcrypt.hashpw(password, salt)
            
            with sqlite3.connect('users.db') as conn:
                c = conn.cursor()
                c.execute("SELECT email FROM users WHERE email=?", (email,))
                if c.fetchone():
                    return "Email already registered!"
                c.execute("INSERT INTO users (email, password) VALUES (?, ?)", 
                         (email, hashed_password))
                conn.commit()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            return "Email already registered!"
        except Exception as e:
            app.logger.error(f"Signup error: {str(e)}")
            return "Registration failed!"

    return render_template('signup.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password'].encode('utf-8')

        try:
            with sqlite3.connect('users.db') as conn:
                c = conn.cursor()
                c.execute("SELECT password FROM users WHERE email=?", (email,))
                result = c.fetchone()
                
                if result and bcrypt.checkpw(password, result[0]):
                    return redirect(url_for('generator'))
                else:
                    error = "Invalid credentials!"
        except Exception as e:
            app.logger.error(f"Login error: {str(e)}")
            error = "Login failed!"

    return render_template('login.html', error=error)

@app.route("/generator")
def generator():
    return render_template("generator.html")

@app.route("/generate", methods=['POST'])
def generate():
    genres = request.form['genres']
    start_index = int(request.form.get('start_index', 0))
    books, total_books = fetch_books(genres, start_index)
    return render_template('books.html', genres=genres, books=books, start_index=start_index, total_books=total_books)

@app.route("/fetch_books", methods=['POST'])
def fetch_books_ajax():
    genres = request.form['genres']
    start_index = int(request.form.get('start_index', 0))
    books, total_books = fetch_books(genres, start_index)
    return jsonify({'books': books, 'total_books': total_books, 'start_index': start_index})

def fetch_books(genres, start_index):
    query = f'subject:{genres}'
    url = f"https://www.googleapis.com/books/v1/volumes?q={query}&startIndex={start_index}&maxResults=10"
    response = requests.get(url)
    data = response.json()
    books = []
    total_books = data.get('totalItems', 0)
    if 'items' in data:
        for item in data['items']:
            book_info = item['volumeInfo']
            books.append({
                "author": ', '.join(book_info.get('authors', 'Unknown')),
                "name": book_info.get('title', 'No Title'),
                "release_year": book_info.get('publishedDate', 'Unknown'),
                "genre": ', '.join(book_info.get('categories', []))
            })
    return books, total_books

if __name__ == "__main__":
    app.run(debug=True)
