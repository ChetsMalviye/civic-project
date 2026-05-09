# app.py
# Main file that runs our website
# Project: AI-Powered Smart Civic Issue Reporting System
# Made by: Chetan Lohar | BCA 6th Semester

from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash

# Create the Flask app
app = Flask(__name__)

# Secret key for sessions
app.secret_key = "chetan123"

# --- MySQL Database Connection ---
app.config['MYSQL_HOST']     = 'localhost'
app.config['MYSQL_USER']     = 'root'
app.config['MYSQL_PASSWORD'] = ''          # XAMPP default has no password
app.config['MYSQL_DB']       = 'civic_db'

# Connect MySQL to app
mysql = MySQL(app)

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
        # Get data from the form
        name     = request.form['name']
        email    = request.form['email']
        password = request.form['password']

 # Hash the password before saving — more secure!
        hashed_password = generate_password_hash(password)

        # Save to database
        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (%s, %s, %s)",
            (name, email, hashed_password)
        )
        mysql.connection.commit()
        cursor.close()

        # Show success message and go to login
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    # Show the register page
    return render_template('auth/register.html')

# -----------------------------------------------
# Login page
# -----------------------------------------------
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']

# Check if email exists in database
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT * FROM users WHERE email=%s",
            (email,)
        )
        user = cursor.fetchone()
        cursor.close()

        # Now check if password matches the hashed password
        if user and check_password_hash(user[3], password):
            # Save user info in session (like a cookie)
            session['user_id']   = user[0]
            session['user_name'] = user[1]
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Wrong email or password!', 'danger')

    return render_template('auth/login.html')

# -----------------------------------------------
# Dashboard (after login)
# -----------------------------------------------
@app.route('/dashboard')
def dashboard():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))
    return render_template('user/dashboard.html')

# -----------------------------------------------
# Logout
# -----------------------------------------------
@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# -----------------------------------------------
# Complaint Form page
# -----------------------------------------------
@app.route('/complaint', methods=['GET', 'POST'])
def complaint():
    # Check if user is logged in
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        # Get data from form
        title       = request.form['title']
        description = request.form['description']
        category    = request.form['category']
        location    = request.form['location']

        # Simple AI priority logic
        # If description has urgent words = High priority
        urgent_words = ['urgent', 'dangerous', 'accident', 'broken',
                        'flood', 'fire', 'blocked', 'serious', 'critical']
        priority = 'Low'
        for word in urgent_words:
            if word.lower() in description.lower():
                priority = 'High'
                break
        else:
            priority = 'Medium'

        # Save complaint to database
        cursor = mysql.connection.cursor()
        cursor.execute(
            """INSERT INTO complaints
               (user_id, title, description, category, location, priority, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
            (session['user_id'], title, description,
             category, location, priority, 'Pending')
        )
        mysql.connection.commit()
        cursor.close()

        flash('Complaint submitted successfully! Priority: ' + priority, 'success')
        return redirect(url_for('my_complaints'))

    return render_template('user/complaint.html')


# My Complaints page — shows user's complaints

@app.route('/my-complaints')
def my_complaints():
    if 'user_id' not in session:
        flash('Please login first!', 'danger')
        return redirect(url_for('login'))

    # Get all complaints of this user from database
    cursor = mysql.connection.cursor()
    cursor.execute(
        "SELECT * FROM complaints WHERE user_id = %s ORDER BY created DESC",
        (session['user_id'],)
    )
    complaints = cursor.fetchall()
    cursor.close()

    return render_template('user/my_complaints.html', complaints=complaints)

# -----------------------------------------------
# Admin Login page
# -----------------------------------------------
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check admin in database
        cursor = mysql.connection.cursor()
        cursor.execute(
            "SELECT * FROM admins WHERE username=%s AND password=%s",
            (username, password)
        )
        admin = cursor.fetchone()
        cursor.close()

        if admin:
            session['admin_id']   = admin[0]
            session['admin_name'] = admin[1]
            flash('Welcome Admin!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Wrong username or password!', 'danger')

    return render_template('admin/admin_login.html')

# -----------------------------------------------
# Admin Dashboard — see all complaints
# -----------------------------------------------
@app.route('/admin/dashboard')
def admin_dashboard():
    # Check if admin is logged in
    if 'admin_id' not in session:
        flash('Please login as admin!', 'danger')
        return redirect(url_for('admin_login'))

    cursor = mysql.connection.cursor()

    # Get all complaints with user name
    cursor.execute("""
        SELECT complaints.*, users.name
        FROM complaints
        JOIN users ON complaints.user_id = users.id
        ORDER BY complaints.created DESC
    """)
    all_complaints = cursor.fetchall()

    # Count totals for summary cards
    cursor.execute("SELECT COUNT(*) FROM complaints")
    total = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Pending'")
    pending = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='In Progress'")
    inprogress = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM complaints WHERE status='Resolved'")
    resolved = cursor.fetchone()[0]

    cursor.close()

    return render_template('admin/admin_dashboard.html',
                           complaints=all_complaints,
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

    cursor = mysql.connection.cursor()
    cursor.execute(
        "UPDATE complaints SET status=%s WHERE id=%s",
        (new_status, complaint_id)
    )
    mysql.connection.commit()
    cursor.close()

    flash('Status updated successfully!', 'success')
    return redirect(url_for('admin_dashboard'))

# -----------------------------------------------
# Admin Logout
# -----------------------------------------------
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_id', None)
    session.pop('admin_name', None)
    flash('Admin logged out!', 'success')
    return redirect(url_for('admin_login'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)