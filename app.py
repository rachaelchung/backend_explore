from flask import Flask, render_template, request, jsonify, session
from flask_cors import CORS
import os
from datetime import datetime
import sqlite3

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
CORS(app)

# Database setup
DATABASE = 'chatroom.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # Return rows as dictionaries
    return db

def init_db():
    """Initialize database tables"""
    db = get_db()
    cursor = db.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            first_name TEXT NOT NULL,
            portfolio_url TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # Posts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            description TEXT,
            video_url TEXT,
            github_url TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    # Comments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            post_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    # Likes table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            post_id INTEGER NOT NULL,
            username TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (post_id, username),
            FOREIGN KEY (post_id) REFERENCES posts(id),
            FOREIGN KEY (username) REFERENCES users(username)
        )
    ''')
    
    db.commit()
    db.close()

# Initialize database on startup
init_db()

# Helper functions
def get_user_by_username(username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    user = cursor.fetchone()
    db.close()
    return dict(user) if user else None

def create_user(username, first_name):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            'INSERT INTO users (username, first_name, portfolio_url, created_at) VALUES (?, ?, ?, ?)',
            (username, first_name, '', datetime.now().isoformat())
        )
        db.commit()
        user = get_user_by_username(username)
        db.close()
        return user
    except sqlite3.IntegrityError:
        db.close()
        return None

def create_post(username, title, description, video_url, github_url):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO posts (username, title, description, video_url, github_url, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        (username, title, description, video_url, github_url, datetime.now().isoformat())
    )
    post_id = cursor.lastrowid
    db.commit()
    
    cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    db.close()
    return dict(post)

def add_comment(post_id, username, content):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO comments (post_id, username, content, created_at) VALUES (?, ?, ?, ?)',
        (post_id, username, content, datetime.now().isoformat())
    )
    comment_id = cursor.lastrowid
    db.commit()
    
    cursor.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
    comment = cursor.fetchone()
    db.close()
    return dict(comment) if comment else None

def toggle_like(post_id, username):
    db = get_db()
    cursor = db.cursor()
    
    # Check if like exists
    cursor.execute('SELECT * FROM likes WHERE post_id = ? AND username = ?', (post_id, username))
    existing_like = cursor.fetchone()
    
    if existing_like:
        # Unlike
        cursor.execute('DELETE FROM likes WHERE post_id = ? AND username = ?', (post_id, username))
        db.commit()
        db.close()
        return False
    else:
        # Like
        cursor.execute(
            'INSERT INTO likes (post_id, username, created_at) VALUES (?, ?, ?)',
            (post_id, username, datetime.now().isoformat())
        )
        db.commit()
        db.close()
        return True

def get_like_count(post_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) FROM likes WHERE post_id = ?', (post_id,))
    count = cursor.fetchone()[0]
    db.close()
    return count

def get_comment_count(post_id):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT COUNT(*) FROM comments WHERE post_id = ?', (post_id,))
    count = cursor.fetchone()[0]
    db.close()
    return count

def user_liked_post(post_id, username):
    if not username:
        return False
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM likes WHERE post_id = ? AND username = ?', (post_id, username))
    liked = cursor.fetchone() is not None
    db.close()
    return liked

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username', '').strip()
    first_name = data.get('first_name', '').strip()
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    user = get_user_by_username(username)
    
    if user:
        # Existing user - just log them in
        session['username'] = username
        return jsonify({'user': user, 'returning': True}), 200
    else:
        # New user - need first name to create account
        if not first_name:
            return jsonify({'error': 'First name is required for new accounts'}), 400
        
        user = create_user(username, first_name)
        if not user:
            return jsonify({'error': 'Could not create user'}), 500
        
        session['username'] = username
        return jsonify({'user': user, 'returning': False}), 200

@app.route('/api/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return jsonify({'message': 'Logged out'}), 200

@app.route('/api/check-username', methods=['POST'])
def check_username():
    """Check if a username exists in the database"""
    data = request.get_json()
    username = data.get('username', '').strip()
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    user = get_user_by_username(username)
    return jsonify({'exists': user is not None, 'user': dict(user) if user else None}), 200

@app.route('/api/current-user', methods=['GET'])
def current_user():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    user = get_user_by_username(username)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({'user': user}), 200

@app.route('/api/users/<username>', methods=['GET'])
def get_user_profile(username):
    """Get a user's profile and their posts"""
    user = get_user_by_username(username)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Get user's posts
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('''
        SELECT p.*, u.first_name 
        FROM posts p
        JOIN users u ON p.username = u.username
        WHERE p.username = ?
        ORDER BY p.created_at DESC
    ''', (username,))
    posts = cursor.fetchall()
    
    current_username = session.get('username')
    posts_with_data = []
    
    for post in posts:
        post_dict = dict(post)
        post_dict['like_count'] = get_like_count(post['id'])
        post_dict['comment_count'] = get_comment_count(post['id'])
        post_dict['liked_by_user'] = user_liked_post(post['id'], current_username)
        posts_with_data.append(post_dict)
    
    db.close()
    
    return jsonify({
        'user': user,
        'posts': posts_with_data,
        'post_count': len(posts_with_data)
    }), 200

@app.route('/api/profile', methods=['PUT'])
def update_profile():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    first_name = data.get('first_name', '').strip()
    portfolio_url = data.get('portfolio_url', '').strip()
    
    db = get_db()
    cursor = db.cursor()
    
    # Update fields
    if first_name:
        cursor.execute('UPDATE users SET first_name = ? WHERE username = ?', (first_name, username))
    
    cursor.execute('UPDATE users SET portfolio_url = ? WHERE username = ?', (portfolio_url, username))
    
    db.commit()
    db.close()
    
    user = get_user_by_username(username)
    return jsonify({'user': user}), 200

@app.route('/api/posts', methods=['GET'])
def get_posts():
    db = get_db()
    cursor = db.cursor()
    
    # Get all posts with user information
    cursor.execute('''
        SELECT p.*, u.first_name 
        FROM posts p
        JOIN users u ON p.username = u.username
        ORDER BY p.created_at DESC
    ''')
    posts = cursor.fetchall()
    
    current_username = session.get('username')
    posts_with_data = []
    
    for post in posts:
        post_dict = dict(post)
        post_dict['like_count'] = get_like_count(post['id'])
        post_dict['comment_count'] = get_comment_count(post['id'])
        post_dict['liked_by_user'] = user_liked_post(post['id'], current_username)
        posts_with_data.append(post_dict)
    
    db.close()
    return jsonify({'posts': posts_with_data}), 200

@app.route('/api/posts', methods=['POST'])
def create_post_route():
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    data = request.get_json()
    title = data.get('title', '').strip()
    description = data.get('description', '').strip()
    video_url = data.get('video_url', '').strip()
    github_url = data.get('github_url', '').strip()
    
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    
    post = create_post(username, title, description, video_url, github_url)
    return jsonify({'post': post}), 201

@app.route('/api/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    db = get_db()
    cursor = db.cursor()
    
    # Get post with user first name
    cursor.execute('''
        SELECT p.*, u.first_name 
        FROM posts p
        JOIN users u ON p.username = u.username
        WHERE p.id = ?
    ''', (post_id,))
    post = cursor.fetchone()
    
    if not post:
        db.close()
        return jsonify({'error': 'Post not found'}), 404
    
    post_dict = dict(post)
    post_dict['like_count'] = get_like_count(post_id)
    post_dict['liked_by_user'] = user_liked_post(post_id, session.get('username'))
    
    # Get comments with user first names
    cursor.execute('''
        SELECT c.*, u.first_name 
        FROM comments c
        JOIN users u ON c.username = u.username
        WHERE c.post_id = ?
        ORDER BY c.created_at ASC
    ''', (post_id,))
    comments = cursor.fetchall()
    post_dict['comments'] = [dict(comment) for comment in comments]
    
    db.close()
    return jsonify({'post': post_dict}), 200

@app.route('/api/posts/<int:post_id>/like', methods=['POST'])
def like_post(post_id):
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Check if post exists
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    db.close()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    liked = toggle_like(post_id, username)
    return jsonify({
        'liked': liked,
        'like_count': get_like_count(post_id)
    }), 200

@app.route('/api/posts/<int:post_id>/comments', methods=['POST'])
def add_comment_route(post_id):
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    # Check if post exists
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    db.close()
    
    if not post:
        return jsonify({'error': 'Post not found'}), 404
    
    data = request.get_json()
    content = data.get('content', '').strip()
    
    if not content:
        return jsonify({'error': 'Comment content is required'}), 400
    
    comment = add_comment(post_id, username, content)
    return jsonify({'comment': comment}), 201

@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id):
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if post exists and belongs to user
    cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
    post = cursor.fetchone()
    
    if not post:
        db.close()
        return jsonify({'error': 'Post not found'}), 404
    
    if post['username'] != username:
        db.close()
        return jsonify({'error': 'You can only delete your own posts'}), 403
    
    # Delete associated likes and comments first (foreign key constraint)
    cursor.execute('DELETE FROM likes WHERE post_id = ?', (post_id,))
    cursor.execute('DELETE FROM comments WHERE post_id = ?', (post_id,))
    cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
    
    db.commit()
    db.close()
    
    return jsonify({'message': 'Post deleted'}), 200

@app.route('/api/comments/<int:comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    username = session.get('username')
    if not username:
        return jsonify({'error': 'Not logged in'}), 401
    
    db = get_db()
    cursor = db.cursor()
    
    # Check if comment exists and belongs to user
    cursor.execute('SELECT * FROM comments WHERE id = ?', (comment_id,))
    comment = cursor.fetchone()
    
    if not comment:
        db.close()
        return jsonify({'error': 'Comment not found'}), 404
    
    if comment['username'] != username:
        db.close()
        return jsonify({'error': 'You can only delete your own comments'}), 403
    
    cursor.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
    
    db.commit()
    db.close()
    
    return jsonify({'message': 'Comment deleted'}), 200

@app.route('/api/admin/clear-all', methods=['POST'])
def clear_all_data():
    """Clear all data - useful for testing/development"""
    db = get_db()
    cursor = db.cursor()
    
    cursor.execute('DELETE FROM likes')
    cursor.execute('DELETE FROM comments')
    cursor.execute('DELETE FROM posts')
    cursor.execute('DELETE FROM users')
    
    db.commit()
    db.close()
    session.clear()
    return jsonify({'message': 'All data cleared'}), 200

if __name__ == '__main__':
    # Use port 5001 to avoid conflicts, or set PORT environment variable
    port = int(os.environ.get('PORT', 5001))
    app.run(debug=True, host='0.0.0.0', port=port)