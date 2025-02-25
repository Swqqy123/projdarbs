from flask import Flask, request, render_template, redirect, url_for
import sqlite3

app = Flask(__name__)

@app.route("/")
def index():
    return render_template("index.html") # Palaižot app.py atveras index.html

@app.route("/signup", methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirmPassword']
        
        # Pārbauda vai paroles sakrīt
        if password != confirm_password:
            return "Passwords do not match!"

        # Saglabā jaunu user datu bāzē
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("INSERT INTO users (email, password) VALUES (?, ?)", (email, password))
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('signup.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    error = None  # Mainīgais kur turēt error message

    if request.method == 'POST':
        email = request.form['username']
        password = request.form['password']

        # Pārbauda vai konts ir reģistrēts datu bāzē
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = c.fetchone()
        conn.close()

        if user:
            return "Login successful!"  # Parādas šāda ziņa, ja lietotājs sekmīgi ielogojas	
        else:
            error = "Invalid credentials!"  # Izveidojas šāds error ja lietotājs nav atrasts

    return render_template('login.html', error=error)  # Nosūta kļūdas ziņojumu


if __name__ == "__main__":
    app.run(debug=True)
