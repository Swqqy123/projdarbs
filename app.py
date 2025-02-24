from flask import Flask, request, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirmPassword']
        
        # Check if passwords match
        if password != confirm_password:
            return "Passwords do not match!"

        # Save new user to the database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None  # Variable to hold error message

    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        # Check if the user exists in the database
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            return "Login successful!"  # For simplicity, we just return this text
        else:
            error = "Invalid credentials!"  # Set error message

    return render_template('login.html', error=error)  # Pass error message to the template


if __name__ == "__main__":
    app.run(debug=True)

