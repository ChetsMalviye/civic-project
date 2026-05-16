# app.py
# Main file that runs our website
# Project: AI-Powered Smart Civic Issue Reporting System
# Made by: Chetan Lohar | BCA 6th Semester

import os
import psycopg2
import psycopg2.extras
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash

# Create the Flask app
app = Flask(__name__)
app.secret_key = "chetan123"

# -----------------------------------------------
# Database connection — Supabase PostgreSQL
# -----------------------------------------------
DB_URL = "postgresql://postgres.dbisiduqulcmvirjdxhr:Supabase%26%4004@aws-1-ap-south-1.pooler.supabase.com:5432/postgres"

def get_db():
    conn = psycopg2.connect(DB_URL)
    return conn

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
            conn   = get_db()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
                (name, email, hashed_password)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash('Email already exists! Try another.', 'danger')

    return render_template('auth/register.html')

# -----------------------------------------------
# Login page
# -----------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()
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

        conn   = get_db()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO complaints
               (user_id, title, description, category, location, priority, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (session['user_id'], title, description,
             category, location, priority, 'Pending')
        )
        conn.commit()
        cursor.close()
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

    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cursor.execute(
        "SELECT * FROM complaints WHERE user_id=%s ORDER BY created DESC",
        (session['user_id'],)
    )
    complaints = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('user/my_complaints.html', complaints=complaints)

# -----------------------------------------------
# Logout
# -----------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# -----------------------------------------------
# Admin Login
# -----------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn   = get_db()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        cursor.execute(
            "SELECT * FROM admins WHERE username=%s AND password=%s",
            (username, password)
        )
        admin = cursor.fetchone()
        cursor.close()
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

    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    cursor.execute("""
        SELECT complaints.*, users.name as user_name
        FROM complaints
        JOIN users ON complaints.user_id = users.id
        ORDER BY complaints.created DESC
    """)
    complaints = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
    inprogress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]

    cursor.close()
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
    conn   = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE complaints SET status=%s WHERE id=%s",
        (new_status, complaint_id)
    )
    conn.commit()
    cursor.close()
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
    return redirect(url_for('home'))

# -----------------------------------------------
# Run the app
# -----------------------------------------------

# -----------------------------------------------
# User Profile Page
# -----------------------------------------------
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))

    conn   = get_db()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        new_pass = request.form['new_password']

        if new_pass:
            # Update name, email and password
            hashed = generate_password_hash(new_pass)
            cursor.execute(
                "UPDATE users SET name=%s, email=%s, password=%s WHERE id=%s",
                (name, email, hashed, session['user_id'])
            )
        else:
            # Update only name and email
            cursor.execute(
                "UPDATE users SET name=%s, email=%s WHERE id=%s",
                (name, email, session['user_id'])
            )

        conn.commit()
        session['user_name'] = name
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))

    # Get user details
    cursor.execute("SELECT * FROM users WHERE id=%s", (session['user_id'],))
    user = cursor.fetchone()

    # Get complaint counts
    cursor.execute("SELECT COUNT(*) FROM complaints WHERE user_id=%s", (session['user_id'],))
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE user_id=%s AND status='Pending'", (session['user_id'],))
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE user_id=%s AND status='Resolved'", (session['user_id'],))
    resolved = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return render_template('user/profile.html',
                           user=user,
                           total=total,
                           pending=pending,
                           resolved=resolved)
    
    # -----------------------------------------------
# Delete Complaint
# -----------------------------------------------
@app.route('/delete-complaint/<int:complaint_id>')
def delete_complaint(complaint_id):
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))

    conn   = get_db()
    cursor = conn.cursor()

    # Make sure user can only delete their OWN complaint
    cursor.execute(
        "DELETE FROM complaints WHERE id=%s AND user_id=%s",
        (complaint_id, session['user_id'])
    )
    conn.commit()
    cursor.close()
    conn.close()

    flash('Complaint deleted successfully!', 'success')
    return redirect(url_for('my_complaints'))

if __name__ == '__main__':
    app.run(debug=True)