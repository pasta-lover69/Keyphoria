"""
Secure Password Manager - Clean Backend API
Provides REST API for password management with encryption
"""

from flask import Flask, request, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
import os
import base64
from functools import wraps

# Initialize Flask app
app = Flask(__name__)

# Configuration
app.config.update(
    SESSION_COOKIE_SECURE=os.getenv('FLASK_ENV') == 'production',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
)

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL')
if DATABASE_URL:
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///password_manager.db'

# Enable CORS for browser extension
CORS(app, supports_credentials=True, origins=['chrome-extension://*', 'moz-extension://*', 'http://localhost:*'])

db = SQLAlchemy(app)


# Encryption setup
def get_encryption_key():
    """Get or generate encryption key"""
    encryption_key = os.getenv('ENCRYPTION_KEY')
    if encryption_key:
        try:
            return base64.b64decode(encryption_key.encode())
        except:
            return encryption_key.encode()
    return Fernet.generate_key()


fernet = Fernet(get_encryption_key())


# Database Models
class User(db.Model):
    """User model for authentication"""
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    passwords = db.relationship('Password', backref='user', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Hash and set user password"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify password against hash"""
        return check_password_hash(self.password_hash, password)


class Password(db.Model):
    """Password storage model with encryption"""
    __tablename__ = 'password'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    service = db.Column(db.String(150), nullable=False, index=True)
    username = db.Column(db.String(150), nullable=False)
    password_encrypted = db.Column(db.String(256), nullable=False)

    def encrypt_password(self, password):
        """Encrypt and store password"""
        self.password_encrypted = fernet.encrypt(password.encode()).decode()

    def decrypt_password(self):
        """Decrypt and return password"""
        return fernet.decrypt(self.password_encrypted.encode()).decode()

    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            'id': self.id,
            'service': self.service,
            'username': self.username,
            'password': self.decrypt_password()
        }


# Initialize database
with app.app_context():
    db.create_all()


# Authentication decorator
def login_required(f):
    """Decorator to require authentication for endpoints"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Get current authenticated user"""
    username = session.get('username')
    if not username:
        return None
    return User.query.filter_by(username=username).first()


# API Endpoints

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'ok', 'message': 'Password Manager API is running'})


@app.route('/register', methods=['POST'])
def register():
    """Register a new user"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')

    # Validation
    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400
    
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400

    # Check if user exists
    if User.query.filter_by(username=username).first():
        return jsonify({'error': 'Username already exists'}), 409

    try:
        # Create new user
        new_user = User(username=username)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()

        # Auto-login after registration
        session['username'] = username
        
        return jsonify({
            'success': 'User registered successfully',
            'username': username
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Registration error: {str(e)}')
        return jsonify({'error': 'Registration failed'}), 500


@app.route('/login', methods=['POST'])
def login():
    """Authenticate user and create session"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({'error': 'Username and password are required'}), 400

    try:
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid username or password'}), 401

        # Create session
        session['username'] = username
        
        return jsonify({
            'success': 'Login successful',
            'username': username
        })

    except Exception as e:
        app.logger.error(f'Login error: {str(e)}')
        return jsonify({'error': 'Login failed'}), 500


@app.route('/logout', methods=['POST', 'GET'])
def logout():
    """Clear user session"""
    session.clear()
    return jsonify({'success': 'Logged out successfully'})


@app.route('/check-session', methods=['GET'])
def check_session():
    """Check if user is authenticated"""
    if 'username' in session:
        return jsonify({
            'logged_in': True,
            'username': session['username']
        })
    return jsonify({'logged_in': False})


@app.route('/add', methods=['POST'])
@login_required
def add_password():
    """Add a new password entry"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    service = data.get('service', '').strip()
    username = data.get('username', '').strip()
    password = data.get('password', '')

    # Validation
    if not all([service, username, password]):
        return jsonify({'error': 'Service, username, and password are required'}), 400

    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        # Create new password entry
        new_password = Password(
            user_id=user.id,
            service=service,
            username=username
        )
        new_password.encrypt_password(password)
        
        db.session.add(new_password)
        db.session.commit()

        return jsonify({
            'success': 'Password added successfully',
            'id': new_password.id
        }), 201

    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Add password error: {str(e)}')
        return jsonify({'error': 'Failed to add password'}), 500


@app.route('/get-all-passwords', methods=['GET'])
@login_required
def get_all_passwords():
    """Get all passwords for current user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        passwords = Password.query.filter_by(user_id=user.id).all()
        return jsonify([pwd.to_dict() for pwd in passwords])
    
    except Exception as e:
        app.logger.error(f'Get passwords error: {str(e)}')
        return jsonify({'error': 'Failed to retrieve passwords'}), 500


@app.route('/get/<service>', methods=['POST'])
@login_required
def get_password(service):
    """Get specific password by service and username"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    username = data.get('username', '').strip()

    if not username:
        return jsonify({'error': 'Username is required'}), 400

    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        password_entry = Password.query.filter_by(
            user_id=user.id,
            service=service,
            username=username
        ).first()
        
        if not password_entry:
            return jsonify({'error': f'No password found for {username} on {service}'}), 404

        return jsonify(password_entry.to_dict())
    
    except Exception as e:
        app.logger.error(f'Get password error: {str(e)}')
        return jsonify({'error': 'Failed to retrieve password'}), 500


@app.route('/edit-password', methods=['POST'])
@login_required
def edit_password():
    """Update an existing password"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    password_id = data.get('id')
    new_password = data.get('password', '')

    if not password_id or not new_password:
        return jsonify({'error': 'ID and password are required'}), 400

    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        password_entry = Password.query.filter_by(
            id=password_id,
            user_id=user.id
        ).first()
        
        if not password_entry:
            return jsonify({'error': 'Password not found'}), 404

        password_entry.encrypt_password(new_password)
        db.session.commit()
        
        return jsonify({'success': 'Password updated successfully'})
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Edit password error: {str(e)}')
        return jsonify({'error': 'Failed to update password'}), 500


@app.route('/delete-password', methods=['POST'])
@login_required
def delete_password():
    """Delete a password entry"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'Invalid request data'}), 400
    
    password_id = data.get('id')

    if not password_id:
        return jsonify({'error': 'Password ID is required'}), 400

    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        password_entry = Password.query.filter_by(
            id=password_id,
            user_id=user.id
        ).first()
        
        if not password_entry:
            return jsonify({'error': 'Password not found'}), 404

        db.session.delete(password_entry)
        db.session.commit()
        
        return jsonify({'success': 'Password deleted successfully'})
    
    except Exception as e:
        db.session.rollback()
        app.logger.error(f'Delete password error: {str(e)}')
        return jsonify({'error': 'Failed to delete password'}), 500


@app.route('/get-services', methods=['GET'])
@login_required
def get_services():
    """Get list of unique services for current user"""
    user = get_current_user()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    try:
        services = db.session.query(Password.service).filter_by(
            user_id=user.id
        ).distinct().all()
        
        return jsonify([service[0] for service in services])
    
    except Exception as e:
        app.logger.error(f'Get services error: {str(e)}')
        return jsonify({'error': 'Failed to retrieve services'}), 500


# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Endpoint not found'}), 404


@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return jsonify({'error': 'Internal server error'}), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)
