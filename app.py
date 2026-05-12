# app.py
# Main file that runs our website
# Project: AI-Powered Smart Civic Issue Reporting System
# Made by: Chetan Lohar | BCA 6th Semester

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# Create the Flask app
app = Flask(__name__)
app.secret_key = "chetan123"

# -----------------------------------------------
# DATABASE SETUP — SQLite (works everywhere!)
# -----------------------------------------------
DB_PATH = "civic.db"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            name     TEXT NOT NULL,
            email    TEXT NOT NULL UNIQUE,
            password TEXT NOT NULL,
            role     TEXT DEFAULT 'user',
            created  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create complaints table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS complaints (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            title       TEXT NOT NULL,
            description TEXT NOT NULL,
            category    TEXT NOT NULL,
            location    TEXT NOT NULL,
            priority    TEXT DEFAULT 'Medium',
            status      TEXT DEFAULT 'Pending',
            created     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Create admins table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            password TEXT NOT NULL
        )
    """)

    # Add default admin if not exists
    cursor.execute("SELECT * FROM admins WHERE username='admin'")
    if not cursor.fetchone():
        cursor.execute(
            "INSERT INTO admins (username, password) VALUES (?, ?)",
            ('admin', 'admin123')
        )

    conn.commit()
    conn.close()

# -----------------------------------------------
# Home page
# -----------------------------------------------
@app.route('/')
def home():
    return render_template('index.html')

# -----------------------------------------------
# Register page
# -----------------------------------------------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        password = request.form['password']

        # Hash the password
        hashed_password = generate_password_hash(password)

        try:
            conn = get_db()
            conn.execute(
                "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
                (name, email, hashed_password)
            )
            conn.commit()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Email already exists! Try another email.', 'danger')
            conn.close()

    return render_template('auth/register.html')

# -----------------------------------------------
# Login page
# -----------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=?", (email,)
        ).fetchone()
        conn.close()

        if user and check_password_hash(user['password'], password):
            session['user_id']   = user['id']
            session['user_name'] = user['name']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Wrong email or password!', 'danger')

    return render_template('auth/login.html')

# -----------------------------------------------
# Dashboard
# -----------------------------------------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))
    return render_template('user/dashboard.html')

# -----------------------------------------------
# Complaint Form
# -----------------------------------------------
@app.route('/complaint', methods=['GET', 'POST'])
def complaint():
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        title       = request.form['title']
        description = request.form['description']
        category    = request.form['category']
        location    = request.form['location']

        # AI priority logic
        urgent_words = ['urgent', 'dangerous', 'accident', 'broken',
                        'flood', 'fire', 'blocked', 'serious', 'critical']
        priority = 'Medium'
        for word in urgent_words:
            if word.lower() in description.lower():
                priority = 'High'
                break

        conn = get_db()
        conn.execute(
            """INSERT INTO complaints
               (user_id, title, description, category, location, priority, status)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (session['user_id'], title, description,
             category, location, priority, 'Pending')
        )
        conn.commit()
        conn.close()

        flash('Complaint submitted! Priority: ' + priority, 'success')
        return redirect(url_for('my_complaints'))

    return render_template('user/complaint.html')

# -----------------------------------------------
# My Complaints
# -----------------------------------------------
@app.route('/my-complaints')
def my_complaints():
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))

    conn = get_db()
    complaints = conn.execute(
        "SELECT * FROM complaints WHERE user_id=? ORDER BY created DESC",
        (session['user_id'],)
    ).fetchall()
    conn.close()

    return render_template('user/my_complaints.html', complaints=complaints)

# -----------------------------------------------
# Logout
# -----------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# -----------------------------------------------
# Admin Login
# -----------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db()
        admin = conn.execute(
            "SELECT * FROM admins WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        conn.close()

        if admin:
            session['admin_id']   = admin['id']
            session['admin_name'] = admin['username']
            flash('Welcome Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Wrong username or password!', 'danger')

    return render_template('admin/admin_login.html')

# -----------------------------------------------
# Admin Dashboard
# -----------------------------------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    if 'admin_id' not in session:
        flash('Please login as admin!', 'danger')
        return redirect(url_for('admin_login'))

    conn = get_db()

    complaints = conn.execute("""
        SELECT complaints.*, users.name as user_name
        FROM complaints
        JOIN users ON complaints.user_id = users.id
        ORDER BY complaints.created DESC
    """).fetchall()

    total      = conn.execute("SELECT COUNT(*) FROM complaints").fetchone()[0]
    pending    = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'").fetchone()[0]
    inprogress = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'").fetchone()[0]
    resolved   = conn.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'").fetchone()[0]
    conn.close()

    return render_template('admin/admin_dashboard.html',
                           complaints=complaints,
                           total=total,
                           pending=pending,
                           inprogress=inprogress,
                           resolved=resolved)

# -----------------------------------------------
# Update complaint status
# -----------------------------------------------
@app.route('/admin/update/<int:complaint_id>', methods=['POST'])
def update_status(complaint_id):
    if 'admin_id' not in session:
        return redirect(url_for('admin_login'))

    new_status = request.form['status']
    conn = get_db()
    conn.execute(
        "UPDATE complaints SET status=? WHERE id=?",
        (new_status, complaint_id)
    )
    conn.commit()
    conn.close()

    flash('Status updated!', 'success')
    return redirect(url_for('admin_dashboard'))

# -----------------------------------------------
# Admin Logout
# -----------------------------------------------
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    return redirect(url_for('admin_login'))

# -----------------------------------------------
# Run the app
# -----------------------------------------------
if __name__ == '__main__':
    init_db()
    print("Database ready!")
    app.run(debug=True)

# This runs on the server (Render/Railway)
init_db()