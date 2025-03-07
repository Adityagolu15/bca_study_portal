from flask import Flask, request, jsonify, render_template, redirect, url_for, flash, send_from_directory, session
from flask_sqlalchemy import SQLAlchemy
import os
import requests
import socket  # Import for getting local IP
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'your_secret_key'
db = SQLAlchemy(app)

# Hugging Face API Details
API_URL = "https://api-inference.huggingface.co/models/facebook/blenderbot-3B"
HEADERS = {"Authorization": "Bearer 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"}  # Replace with your API Key

# Function to get the local IP address
def get_local_ip():
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    return local_ip

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), default='user')
    study_hours = db.Column(db.Float, default=0.0)  # Total study time
    last_login = db.Column(db.DateTime, nullable=True)  # Track login time


class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    semester = db.Column(db.String(50), nullable=False)
    subject = db.Column(db.String(100), nullable=False)
    topic = db.Column(db.String(200), nullable=False)
    file_path = db.Column(db.String(200), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class ChatbotLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    question = db.Column(db.String(500), nullable=False)
    answer = db.Column(db.String(500), nullable=False)
    timestamp = db.Column(db.DateTime, default=db.func.current_timestamp())

# Create database and uploads folder
with app.app_context():
    db.create_all()
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

# Routes
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username, password=password).first()

        if user:
            session['user_id'] = user.id
            session['role'] = user.role
            user.last_login = datetime.now()  # Store login timestamp
            db.session.commit()
            
            return redirect(url_for('admin_dashboard' if user.role == 'admin' else 'user_dashboard'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user and user.last_login:
            elapsed_time = (datetime.now() - user.last_login).total_seconds() / 3600  # Convert seconds to hours
            user.study_hours += elapsed_time  # Add session duration
            user.last_login = None  # Reset login timestamp
            db.session.commit()
        
        session.pop('user_id', None)  # Logout the user
    return redirect(url_for('login'))
 

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if the username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose a different one.')
            return redirect(url_for('register'))

        # Create a new user
        new_user = User(username=username, password=password, role='user')
        db.session.add(new_user)
        db.session.commit()

        flash('Registration successful! Please login.')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/admin')
def admin_dashboard():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    users = User.query.all()
    return render_template('admin.html')

@app.route('/admin/users', methods=['GET', 'POST'])
def manage_users():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
    users = User.query.all()
    return render_template('manage_users.html', users=users)

# Route to delete user
@app.route("/delete_user/<int:user_id>", methods=["POST"])
def delete_user(user_id):
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
        flash("User deleted successfully", "success")
    else:
        flash("User not found", "error")
    return redirect(url_for("manage_users"))

@app.route('/admin/notes', methods=['GET', 'POST'])
def manage_notes():
    if 'user_id' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    if request.method == 'POST':
        print("Form Data Received:", request.form)  # Debugging line

        if 'semester' not in request.form:
            return "Error: 'semester' field is missing in the form", 400
        
        semester = request.form['semester']
        subject = request.form['subject']
        topic = request.form['topic']
        
        if 'file' not in request.files:
            return "Error: File not uploaded", 400
        
        file = request.files['file']
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        new_note = Note(semester=semester, subject=subject, topic=topic, file_path=file_path, uploaded_by=session['user_id'])
        db.session.add(new_note)
        db.session.commit()

        flash("Note uploaded successfully!")
        return redirect(url_for('manage_notes'))

    notes = Note.query.all()
    return render_template('manage_notes.html', notes=notes)

@app.route('/user')
def user_dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    if user.last_login:
        elapsed_time = (datetime.now() - user.last_login).total_seconds() / 3600  # Convert to hours
    else:
        elapsed_time = 0

    total_study_time = round(user.study_hours + elapsed_time, 2)  # Total study time
    user.last_login = datetime.now()
    user.study_hours = total_study_time  # Save updated study hours
    db.session.commit()

    semesters = db.session.query(Note.semester).distinct().all()

    return render_template('user.html', user=user, study_time=total_study_time, semesters=[s[0] for s in semesters])


@app.route('/user/semester/<semester>')
def view_semester(semester):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    subjects = db.session.query(Note.subject).filter_by(semester=semester).distinct().all()
    return render_template('semester.html', semester=semester, subjects=[s[0] for s in subjects])

@app.route('/user/semester/<semester>')
def view_subject(semester):
    if 'user_id' not in session:
        return redirect(url_for('login'))
    subjects = db.session.query(Note.subject).filter_by(semester=semester).distinct().all()
    return render_template('subject.html', semester=semester, subjects=[s[0] for s in subjects])

@app.route('/user/semester/<semester>/subject/<subject>')
def view_notes(semester, subject):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    user = User.query.get(user_id)
    if not user:
        return redirect(url_for('login'))

    # Fetch notes
    notes = Note.query.filter_by(semester=semester, subject=subject).all()

    return render_template('subject.html', semester=semester, subject=subject, notes=notes)

@app.route('/admin/stats')
def admin_stats():
    subjects = db.session.query(Note.subject).distinct().all()
    subject_labels = [s[0] for s in subjects]
    notes_count = [Note.query.filter_by(subject=s[0]).count() for s in subjects]
    return jsonify({'subjects': subject_labels, 'notes_count': notes_count})

def get_bot_response(question):
    """Sends the user's question to Hugging Face API and returns a response."""
    payload = {"inputs": question}

    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)

        print("Status Code:", response.status_code)  # Debugging
        print("Full Response:", response.text)  # Debugging

        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                return data[0].get("generated_text", "I'm not sure about that.")
            return "Sorry, I couldn't understand the response."

        elif response.status_code == 503:
            return "Error 503: Server busy. Try again later."

        else:
            return f"Error {response.status_code}: {response.text}"

    except Exception as e:
        return f"Error: {str(e)}"

@app.route("/chatbot", methods=["POST"])
def chatbot():
    try:
        data = request.get_json()
        if not data or "message" not in data or not data["message"].strip():
            return jsonify({"answer": "Error: Empty message"}), 400
        
        user_input = data["message"]
        bot_response = get_bot_response(user_input)  # Get response from Hugging Face
        return jsonify({"answer": bot_response})

    except Exception as e:
        return jsonify({"answer": f"Error: {str(e)}"}), 500


@app.route('/download/<filename>')
def download(filename):
    try:
        # Ensure the filename is safe and points to a file in the uploads folder
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return jsonify({'error': 'File not found'}), 404

# Helper function to check if user is logged in (used for protecting certain routes)
def is_logged_in():
    return 'user_id' in session

# Run Flask Server on Local Network
if __name__ == '__main__':
    local_ip = get_local_ip()
    print(f"🌍 Server running at: http://{local_ip}:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)
