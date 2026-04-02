from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from bson.objectid import ObjectId
import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'your-very-secret-key'  # Change this to a secure random value

# Connect to your local MongoDB database
client = MongoClient('mongodb://localhost:27017/')
db = client.todo_database
collection = db.tasks
users_collection = db.users

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = users_collection.find_one({'username': username})
        if user and check_password_hash(user.get('password', ''), password):
            session['logged_in'] = True
            session['username'] = username
            flash('Welcome, ' + username + '!', 'success')
            return redirect(url_for('index'))
        flash('Invalid username or password', 'danger')
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if not username or not password or not confirm:
            flash('All fields are required.', 'warning')
        elif password != confirm:
            flash('Passwords do not match.', 'warning')
        elif users_collection.find_one({'username': username}):
            flash('Username already exists.', 'warning')
        else:
            users_collection.insert_one({
                'username': username,
                'password': generate_password_hash(password)
            })
            flash('Registration successful. Please log in.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))


# Route: Display the homepage and load tasks
@app.route('/')
@login_required
def index():
    # Fetch all tasks from MongoDB
    all_tasks = list(collection.find())
    today = datetime.date.today()
    current_tasks = []
    dues = []
    completed = []
    for task in all_tasks:
        if task.get('completed', False):
            completed.append(task)
        else:
            deadline_date = datetime.datetime.strptime(task['deadline'], '%Y-%m-%d').date()
            if deadline_date >= today:
                current_tasks.append(task)
            else:
                dues.append(task)
    # Sort by deadline
    current_tasks.sort(key=lambda x: datetime.datetime.strptime(x['deadline'], '%Y-%m-%d').date())
    dues.sort(key=lambda x: datetime.datetime.strptime(x['deadline'], '%Y-%m-%d').date())
    completed.sort(key=lambda x: x.get('submission_date', datetime.datetime.min))
    return render_template('index.html', tasks=current_tasks, dues=dues, completed=completed)

# Route: Add a new task
@app.route('/add', methods=['POST'])
@login_required
def add_task():
    task_text = request.form.get('content')
    deadline = request.form.get('deadline')
    if task_text and deadline:
        # Insert the task into MongoDB
        collection.insert_one({'content': task_text, 'deadline': deadline, 'submission_date': datetime.datetime.now(), 'completed': False})
    return redirect(url_for('index'))

# Route: Delete a task
@app.route('/delete/<task_id>')
@login_required
def delete_task(task_id):
    # Delete the task from MongoDB using its unique ID
    collection.delete_one({'_id': ObjectId(task_id)})
    return redirect(url_for('index'))

# Route: Mark a task as complete
@app.route('/complete/<task_id>')
@login_required
def complete_task(task_id):
    # Update the task to completed
    collection.update_one({'_id': ObjectId(task_id)}, {'$set': {'completed': True}})
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)