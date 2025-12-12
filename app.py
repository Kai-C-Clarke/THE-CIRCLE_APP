# app.py - AUTO-CREATES circle_table
import os
import sys
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from database import init_db, db, CircleEntry
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from sqlalchemy import text, inspect

app = Flask(__name__)
CORS(app)

print("=" * 60)
print("🚀 THE CIRCLE - Family Memory App")
print("📊 Creating circle_table in this project's database...")

# === DATABASE CONFIGURATION ===
database_url = os.environ.get('DATABASE_URL', '')

if not database_url:
    print("⚠️ DATABASE_URL not set - check Railway Variables")
    # Fallback for testing
    database_url = 'sqlite:///circle.db'

# Fix PostgreSQL URL format
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Add SSL mode for Railway
if database_url.startswith('postgresql://') and 'sslmode' not in database_url:
    if '?' in database_url:
        database_url += '&sslmode=require'
    else:
        database_url += '?sslmode=require'

print(f"📡 Database: {'PostgreSQL' if 'postgresql://' in database_url else 'SQLite'}")

# Configure Flask
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
}

# Add SSL for PostgreSQL
if 'postgresql://' in database_url:
    app.config['SQLALCHEMY_ENGINE_OPTIONS']['connect_args'] = {'sslmode': 'require'}

# Upload configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB

# Initialize database
init_db(app)
print("✅ Database module initialized")

# === FORCE CREATE circle_table ===
print("\n🔨 Ensuring circle_table exists...")
with app.app_context():
    try:
        # Check if circle_table exists
        inspector = inspect(db.engine)
        tables = inspector.get_table_names()
        
        if 'circle_table' in tables:
            print("✅ circle_table already exists")
            
            # Count entries
            count = db.session.query(CircleEntry).count()
            print(f"📊 Table has {count} entries")
            
            # If empty, add sample data
            if count == 0:
                print("📝 Adding welcome entry...")
                welcome_entry = CircleEntry(
                    name="Catherine",
                    relationship="Family",
                    memory="Welcome to The Circle! This is where we'll store all our family memories.",
                    year=2024,
                    photo_url=None
                )
                db.session.add(welcome_entry)
                db.session.commit()
                print("✅ Added welcome entry")
        else:
            print("📝 Creating circle_table...")
            db.create_all()  # This creates ALL tables defined in models
            
            # Verify creation
            inspector = inspect(db.engine)
            new_tables = inspector.get_table_names()
            print(f"✅ Created tables: {new_tables}")
            
            # Add welcome entry
            welcome_entry = CircleEntry(
                name="The Family",
                relationship="Family",
                memory="This is our family memory circle. Add your photos and stories here!",
                year=2024,
                photo_url=None
            )
            db.session.add(welcome_entry)
            db.session.commit()
            print("✅ Added welcome entry to new table")
            
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        print("⚠️ Will try to create on first API call")

print("=" * 60)

# === HELPER FUNCTIONS ===
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === ROUTES ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/entries', methods=['GET'])
def get_entries():
    """Get all circle entries."""
    try:
        entries = CircleEntry.query.order_by(CircleEntry.created_at.desc()).all()
        
        if not entries:
            # Return sample data if table is empty
            return jsonify({'status': 'success', 'entries': [{
                'id': 0,
                'name': 'Welcome!',
                'relationship': 'Family',
                'memory': 'Add your first memory using the form below!',
                'year': datetime.now().year,
                'photo_url': None,
                'created_at': datetime.now().isoformat()
            }]})
        
        result = []
        for entry in entries:
            result.append({
                'id': entry.id,
                'name': entry.name,
                'relationship': entry.relationship,
                'memory': entry.memory,
                'year': entry.year,
                'photo_url': entry.photo_url,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            })
        
        return jsonify({'status': 'success', 'entries': result})
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/entries', methods=['POST'])
def add_entry():
    """Add a new circle entry."""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'status': 'error', 'message': 'No data'}), 400
        
        new_entry = CircleEntry(
            name=data.get('name', 'Anonymous'),
            relationship=data.get('relationship', 'Family'),
            memory=data.get('memory', ''),
            year=data.get('year'),
            photo_url=data.get('photo_url')
        )
        
        db.session.add(new_entry)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Memory added to The Circle!',
            'entry': {
                'id': new_entry.id,
                'name': new_entry.name,
                'relationship': new_entry.relationship,
                'memory': new_entry.memory,
                'year': new_entry.year,
                'photo_url': new_entry.photo_url
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Upload a photo."""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'status': 'error', 'message': 'File type not allowed'}), 400
    
    # Generate unique filename
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    return jsonify({
        'status': 'success',
        'photo_url': f"/static/uploads/{unique_filename}",
        'filename': unique_filename
    })

@app.route('/static/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === DEBUG ROUTES ===
@app.route('/health')
def health():
    try:
        with app.app_context():
            count = CircleEntry.query.count()
            return jsonify({
                'status': 'healthy',
                'app': 'The Circle',
                'database': 'PostgreSQL' if 'postgresql://' in database_url else 'SQLite',
                'table': 'circle_table',
                'entries': count,
                'timestamp': datetime.now().isoformat()
            })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/debug/create-table')
def debug_create():
    """Force create the table."""
    try:
        with app.app_context():
            db.create_all()
            return jsonify({'status': 'success', 'message': 'Table created'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# === STARTUP ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🌍 Server starting on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=False)