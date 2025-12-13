# app.py - AUTO-CREATES circle_table
import os
import sys
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from database import init_db, db, Media
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
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'pdf', 'doc', 'docx', 'txt'}
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
            count = db.session.query(Media).count()
            print(f"📊 Table has {count} entries")
            
            # If empty, add sample data
            if count == 0:
                print("📝 Adding welcome entry...")
                welcome_entry = Media(
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
            welcome_entry = Media(
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

def get_file_type(filename):
    """Get file type from filename."""
    if not filename:
        return 'file'
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    if ext in ['png', 'jpg', 'jpeg', 'gif']:
        return 'image'
    elif ext in ['mp4', 'mov', 'avi', 'mkv']:
        return 'video'
    elif ext in ['pdf', 'doc', 'docx', 'txt']:
        return 'document'
    return 'file'

# === API ROUTES ===
@app.route('/api/test')
def test_api():
    """Test endpoint for frontend connectivity check."""
    return jsonify({
        'status': 'success',
        'message': 'API is working!',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/media')
def get_media():
    """Get all media entries for frontend."""
    try:
        entries = Media.query.order_by(Media.created_at.desc()).all()
        
        if not entries:
            return jsonify({'status': 'success', 'media': []})
        
        media_list = []
        for entry in entries:
            # Map database fields to frontend expectations
            file_type = get_file_type(entry.photo_url)
            
            media_list.append({
                'id': entry.id,
                # Frontend expects these:
                'title': entry.name,
                'uploaded_by': entry.relationship,
                'upload_date': entry.created_at.isoformat() if entry.created_at else datetime.now().isoformat(),
                'description': entry.memory,
                'tags': str(entry.year) if entry.year else '',
                'filetype': file_type,
                'filename': entry.photo_url.split('/')[-1] if entry.photo_url else '',
                'thumbnail': entry.photo_url,
                # Keep original fields too:
                'name': entry.name,
                'relationship': entry.relationship,
                'memory': entry.memory,
                'year': entry.year,
                'photo_url': entry.photo_url,
                'created_at': entry.created_at.isoformat() if entry.created_at else None
            })
        
        return jsonify({
            'status': 'success',
            'count': len(media_list),
            'media': media_list  # Frontend expects 'media' not 'memories'
        })
        
    except Exception as e:
        print(f"Error in /api/media: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/media/<int:media_id>')
def get_single_media(media_id):
    """Get single media entry by ID."""
    try:
        entry = Media.query.get_or_404(media_id)
        file_type = get_file_type(entry.photo_url)
        
        return jsonify({
            'status': 'success',
            'media': {
                'id': entry.id,
                'title': entry.name,
                'uploaded_by': entry.relationship,
                'upload_date': entry.created_at.isoformat() if entry.created_at else datetime.now().isoformat(),
                'description': entry.memory,
                'tags': str(entry.year) if entry.year else '',
                'filetype': file_type,
                'filename': entry.photo_url.split('/')[-1] if entry.photo_url else '',
                'thumbnail': entry.photo_url,
                'name': entry.name,
                'relationship': entry.relationship,
                'memory': entry.memory,
                'year': entry.year,
                'photo_url': entry.photo_url
            }
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 404

@app.route('/api/media/<int:media_id>', methods=['DELETE'])
def delete_media(media_id):
    """Delete a media entry."""
    try:
        entry = Media.query.get_or_404(media_id)
        db.session.delete(entry)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': 'Media deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/media/upload', methods=['POST'])
def media_upload():
    """Alias for /api/upload to match frontend."""
    print(f"Upload request files: {request.files}")
    print(f"Upload form data: {request.form}")
    
    if 'file' not in request.files:
        print("ERROR: No file in request")
        return jsonify({'status': 'error', 'message': 'No file'}), 400
    
    file = request.files['file']
    print(f"File received: {file.filename}")
    
    if file.filename == '':
        print("ERROR: Empty filename")
        return jsonify({'status': 'error', 'message': 'No file selected'}), 400
    
    if not allowed_file(file.filename):
        print(f"ERROR: File type not allowed: {file.filename}")
        return jsonify({'status': 'error', 'message': 'File type not allowed'}), 400
    
    
    # Get form data
    title = request.form.get('title', '')
    description = request.form.get('description', '')
    uploaded_by = request.form.get('uploaded_by', 'Anonymous')
    tags = request.form.get('tags', '')
    
    # Generate unique filename
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
    file.save(filepath)
    
    # Create database entry
    new_entry = Media(
        name=title,
        relationship=uploaded_by,
        memory=description,
        year=datetime.now().year,
        photo_url=f"/static/uploads/{unique_filename}"
    )
    db.session.add(new_entry)
    db.session.commit()
    
    return jsonify({
        'status': 'success',
        'photo_url': f"/static/uploads/{unique_filename}",
        'filename': unique_filename,
        'media': {
            'id': new_entry.id,
            'title': new_entry.name,
            'uploaded_by': new_entry.relationship,
            'upload_date': new_entry.created_at.isoformat() if new_entry.created_at else datetime.now().isoformat(),
            'description': new_entry.memory,
            'tags': tags
        }
    })

# === COMPATIBILITY ROUTES (Keep for other parts of app) ===
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/entries', methods=['GET'])
def get_entries():
    """Get all circle entries."""
    try:
        entries = Media.query.order_by(Media.created_at.desc()).all()
        
        if not entries:
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
        
        new_entry = Media(
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
    """Upload a photo (compatibility route)."""
    return media_upload()  # Use the new implementation

@app.route('/static/uploads/<filename>')
def serve_upload(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === DEBUG ROUTES ===
@app.route('/health')
def health():
    try:
        with app.app_context():
            count = Media.query.count()
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