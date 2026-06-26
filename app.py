import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = 'userbase_secret_key_2024'

DATABASE = os.path.join('/tmp', 'database.db')

def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute('''CREATE TABLE IF NOT EXISTS users 
                    (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                     name TEXT NOT NULL, 
                     email TEXT NOT NULL,
                     phone TEXT,
                     age INTEGER,
                     city TEXT,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.execute('''CREATE TABLE IF NOT EXISTS accounts
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT NOT NULL UNIQUE,
                     email TEXT NOT NULL UNIQUE,
                     password TEXT NOT NULL,
                     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
    conn.commit()
    conn.close()

def get_db_connection():
    init_db()
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/register', methods=['GET', 'POST'])
def register():
    error = {}
    form_data = {}
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm', '').strip()
        form_data = {'username': username, 'email': email}
        if not username: error['username'] = 'Username is required'
        if not email: error['email'] = 'Email is required'
        if not password: error['password'] = 'Password is required'
        if not confirm: error['confirm'] = 'Please confirm your password'
        if password and confirm and password != confirm:
            error['confirm'] = 'Passwords do not match'
        if password and len(password) < 6:
            error['password'] = 'Password must be at least 6 characters'
        if not error:
            conn = get_db_connection()
            existing = conn.execute('SELECT id FROM accounts WHERE username=? OR email=?', (username, email)).fetchone()
            if existing:
                error['username'] = 'Username or email already exists'
                conn.close()
            else:
                hashed = generate_password_hash(password)
                conn.execute('INSERT INTO accounts (username, email, password) VALUES (?, ?, ?)', (username, email, hashed))
                conn.commit()
                conn.close()
                return redirect(url_for('login'))
    return render_template('register.html', error=error, form_data=form_data)

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = {}
    form_data = {}
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        form_data = {'username': username}
        if not username: error['username'] = 'Username is required'
        if not password: error['password'] = 'Password is required'
        if not error:
            conn = get_db_connection()
            account = conn.execute('SELECT * FROM accounts WHERE username=?', (username,)).fetchone()
            conn.close()
            if account and check_password_hash(account['password'], password):
                session['user_id'] = account['id']
                session['username'] = account['username']
                return redirect(url_for('dashboard'))
            else:
                error['username'] = 'Invalid username or password'
    return render_template('login.html', error=error, form_data=form_data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    conn = get_db_connection()
    total = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    cities = conn.execute('SELECT COUNT(DISTINCT city) FROM users').fetchone()[0]
    recent = conn.execute('SELECT * FROM users ORDER BY id DESC LIMIT 5').fetchall()
    conn.close()
    return render_template('dashboard.html', total=total, cities=cities, recent=recent)

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    conn = get_db_connection()
    search = request.args.get('search', '')
    error = {}
    form_data = {}
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        age = request.form.get('age', '').strip()
        city = request.form.get('city', '').strip()
        form_data = {'name': name, 'email': email, 'phone': phone, 'age': age, 'city': city}
        if not name: error['name'] = 'Full name is required'
        if not email: error['email'] = 'Email is required'
        if not phone: error['phone'] = 'Phone number is required'
        if not age: error['age'] = 'Age is required'
        if not city: error['city'] = 'City is required'
        if not error:
            conn.execute('INSERT INTO users (name, email, phone, age, city) VALUES (?, ?, ?, ?, ?)', (name, email, phone, age, city))
            conn.commit()
            conn.close()
            return redirect('/')
    if search:
        users = conn.execute('SELECT * FROM users WHERE name LIKE ? OR email LIKE ? OR city LIKE ? ORDER BY id DESC', (f'%{search}%', f'%{search}%', f'%{search}%')).fetchall()
    else:
        users = conn.execute('SELECT * FROM users ORDER BY id DESC').fetchall()
    total = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
    cities = conn.execute('SELECT COUNT(DISTINCT city) FROM users').fetchone()[0]
    conn.close()
    return render_template('index.html', users=users, total=total, cities=cities, search=search, error=error, form_data=form_data)

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (id,)).fetchone()
    error = {}
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        age = request.form.get('age', '').strip()
        city = request.form.get('city', '').strip()
        if not name: error['name'] = 'Full name is required'
        if not email: error['email'] = 'Email is required'
        if not phone: error['phone'] = 'Phone number is required'
        if not age: error['age'] = 'Age is required'
        if not city: error['city'] = 'City is required'
        if not error:
            conn.execute('UPDATE users SET name=?, email=?, phone=?, age=?, city=? WHERE id=?', (name, email, phone, age, city, id))
            conn.commit()
            conn.close()
            return redirect('/')
    conn.close()
    return render_template('edit.html', user=user, error=error)

@app.route('/delete/<int:id>')
@login_required
def delete(id):
    conn = get_db_connection()
    conn.execute('DELETE FROM users WHERE id = ?', (id,))
    conn.commit()
    conn.close()
    return redirect('/')
