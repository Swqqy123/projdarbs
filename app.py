from flask import Flask, request, render_template, redirect, url_for, jsonify
import sqlite3
import requests
import re

app = Flask(__name__)

def validate_password(password):
    if len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r'[A-Z]', password):
        return "Password must contain at least one uppercase letter."
    if not re.search(r'[a-z]', password):
        return "Password must contain at least one lowercase letter."
    return None

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
        
        validation_error = validate_password(password)
        if validation_error:
            return render_template('signup.html', error=validation_error)

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html', error=error)

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None

    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            return redirect(url_for('generator'))
        else:
            error = "Invalid credentials!"

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
                "author": ', '.join(book_info.get('authors', ['Unknown'])),
                "name": book_info.get('title', 'No Title'),
                "release_year": book_info.get('publishedDate', 'Unknown'),
                "genre": ', '.join(book_info.get('categories', []))
            })
    return books, total_books

if __name__ == "__main__":
    app.run(debug=True)
