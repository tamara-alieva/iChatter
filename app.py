import os
import json
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session
from flask_socketio import SocketIO, emit, join_room, leave_room
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key_here'  # В реальном приложении используйте надежный ключ
socketio = SocketIO(app)

# Папка для хранения истории чатов
if not os.path.exists('chat_history'):
    os.makedirs('chat_history')

# Файл для хранения пользователей
USERS_FILE = 'users.json'

# Загрузка пользователей из файла
def load_users():
    """Load users from JSON file with error handling"""
    try:
        # Check if file exists
        if not os.path.exists(USERS_FILE):
            # Create new file with empty dict if not exists
            with open(USERS_FILE, 'w') as f:
                json.dump({}, f)
            return {}
        
        # Read file content
        with open(USERS_FILE, 'r') as f:
            content = f.read().strip()
            
            # Return empty dict if file is empty
            if not content:
                return {}
                
            # Try to parse JSON
            return json.loads(content)
            
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in {USERS_FILE}: {e}")
        # Backup corrupted file
        try:
            os.rename(USERS_FILE, f"{USERS_FILE}.corrupted")
        except Exception as e:
            print(f"Could not backup corrupted file: {e}")
            
        # Create new empty file
        with open(USERS_FILE, 'w') as f:
            json.dump({}, f)
        return {}
        
    except Exception as e:
        print(f"Error loading users: {e}")
        return {}

# Сохранение пользователей в файл
def save_users(users):
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=4)

# Загрузка истории чата
def load_chat_history(chat_id):
    filename = f'chat_history/{chat_id}.json'
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

# Сохранение сообщения в историю
def save_message(chat_id, sender, message):
    filename = f'chat_history/{chat_id}.json'
    history = load_chat_history(chat_id)
    
    message_data = {
        'sender': sender,
        'message': message,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    history.append(message_data)
    
    with open(filename, 'w') as f:
        json.dump(history, f, indent=4)

# Главная страница - вход или регистрация
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'username' in session:
        return redirect(url_for('chat'))
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        action = request.form['action']
        
        users = load_users()
        
        if action == 'register':
            if username in users:
                return render_template('index.html', error='Username already exists')
            users[username] = generate_password_hash(password)
            save_users(users)
            session['username'] = username
            return redirect(url_for('chat'))
        elif action == 'login':
            if username not in users or not check_password_hash(users[username], password):
                return render_template('index.html', error='Invalid username or password')
            session['username'] = username
            return redirect(url_for('chat'))
    
    return render_template('index.html')

# Страница чата
@app.route('/chat')
def chat():
    if 'username' not in session:
        return redirect(url_for('index'))
    
    username = session['username']
    users = load_users()
    user_list = [u for u in users.keys() if u != username]
    
    return render_template('chat.html', username=username, users=user_list)

# Выход из системы
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('index'))

# WebSocket обработчики
@socketio.on('connect')
def handle_connect():
    if 'username' in session:
        join_room(session['username'])
        emit('update_users', {'users': list(load_users().keys())}, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    if 'username' in session:
        leave_room(session['username'])
        emit('update_users', {'users': list(load_users().keys())}, broadcast=True)

@socketio.on('private_message')
def handle_private_message(data):
    sender = session['username']
    recipient = data['recipient']
    message = data['message']
    
    # Создаем уникальный ID чата (сортировка имен для consistency)
    chat_id = '_'.join(sorted([sender, recipient]))
    
    # Сохраняем сообщение
    save_message(chat_id, sender, message)
    
    # Отправляем сообщение получателю
    emit('new_message', {
        'sender': sender,
        'message': message,
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'chat_id': chat_id
    }, room=recipient)
    
    # Также отправляем себе для отображения в интерфейсе
    emit('new_message', {
        'sender': sender,
        'message': message,
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'chat_id': chat_id
    }, room=sender)

@socketio.on('join_group')
def handle_join_group(data):
    group_name = data['group_name']
    join_room(group_name)
    emit('group_message', {
        'sender': 'System',
        'message': f"{session['username']} joined the group",
        'timestamp': datetime.now().strftime("%H:%M:%S")
    }, room=group_name)

@socketio.on('group_message')
def handle_group_message(data):
    group_name = data['group_name']
    message = data['message']
    sender = session['username']
    
    # Сохраняем групповое сообщение
    save_message(f"group_{group_name}", sender, message)
    
    emit('group_message', {
        'sender': sender,
        'message': message,
        'timestamp': datetime.now().strftime("%H:%M:%S"),
        'chat_id': f"group_{group_name}"
    }, room=group_name)

@socketio.on('load_history')
def handle_load_history(data):
    chat_id = data['chat_id']
    history = load_chat_history(chat_id)
    emit('chat_history', {'chat_id': chat_id, 'history': history})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)