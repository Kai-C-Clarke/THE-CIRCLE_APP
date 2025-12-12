import os
import sys
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from database import init_db, db, Media
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename
from urllib.parse import urlparse
from sqlalchemy import text  # ADD THIS IMPORT

app = Flask(__name__)
CORS(app)

# === DEBUG: Check environment at startup ===
print("=" * 60)
print("🚀 THE CIRCLE - Family Memory App Starting...")
print(f"Python: {sys.version}")
print(f"DATABASE_URL set: {'YES' if 'DATABASE_URL' in os.environ else 'NO'}")

# === FIXED DATABASE CONFIGURATION FOR RAILWAY POSTGRESQL ===
database_url = os.environ.get('DATABASE_URL', 'sqlite:///circle.db')

# Debug log database URL (safely)
if 'DATABASE_URL' in os.environ:
    db_url = os.environ['DATABASE_URL']
    print(f"Database: {'PostgreSQL' if 'postgres' in db_url else 'SQLite'}")
    # Show first and last 30 chars only for security
    if len(db_url) > 60:
        print(f"URL: {db_url[:30]}...{db_url[-30:]}")
    else:
        print(f"URL: {db_url}")

# Fix for Railway PostgreSQL SSL connection
if database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

# Add SSL mode for Railway PostgreSQL if not present
if database_url.startswith('postgresql://') and 'sslmode' not in database_url:
    if '?' in database_url:
        database_url += '&sslmode=require'
    else:
        database_url += '?sslmode=require'
    print("🔧 Added sslmode=require to database URL")

print("=" * 60)

# === UNIVERSAL CONFIGURATION ===
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-local-testing-123')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_recycle': 300,
    'pool_pre_ping': True,
    'connect_args': {
        'sslmode': 'require' if 'postgresql://' in database_url else None
    }
}

# Folder setup - works everywhere
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Database with improved error handling
try:
    init_db(app)
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization error: {type(e).__name__}: {e}")
    print("⚠️ App will continue with database in fallback mode")

# === IMPROVED TABLE CREATION WITH ERROR HANDLING ===
print("\n🔧 Attempting to create database tables...")
try:
    with app.app_context():
        # Check if tables already exist
        from sqlalchemy import inspect
        inspector = inspect(db.engine)
        existing_tables = inspector.get_table_names()
        
        if existing_tables:
            print(f"✅ Found {len(existing_tables)} existing table(s): {existing_tables}")
        else:
            print("📭 No tables found, creating them now...")
            # Test connection first
            try:
                db.session.execute(text('SELECT 1'))  # FIXED: Added text()
                print("✅ Database connection test passed")
            except Exception as e:
                print(f"❌ Database connection failed: {e}")
                print("⚠️ Will attempt to create tables anyway...")
            
            # Create tables
            db.create_all()
            
            # Verify creation
            inspector = inspect(db.engine)
            new_tables = inspector.get_table_names()
            print(f"✅ Created {len(new_tables)} table(s): {new_tables}")
            
except Exception as e:
    print(f"❌ ERROR during table creation: {type(e).__name__}: {e}")
    print("⚠️ Tables will be created on first API call instead.")

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# === ROUTES ===
@app.route('/')
def index():
    """Serve the main interface."""
    return render_template('index.html')

@app.route('/api/memories', methods=['GET'])
def get_memories():
    """API endpoint to get all memories for the timeline."""
    try:
        # AUTO-CREATE TABLES IF MISSING (safety net)
        with app.app_context():
            try:
                # Try a simple query to check if tables exist
                Media.query.limit(1).all()
            except Exception as e:
                print(f"⚠️ Tables missing, creating now: {e}")
                # Test connection first
                try:
                    db.session.execute(text('SELECT 1'))  # FIXED: Added text()
                except Exception as conn_error:
                    print(f"❌ Connection error: {conn_error}")
                    # Return empty array if database is down
                    return jsonify({'status': 'success', 'memories': []})
                
                db.create_all()
                print("✅ Tables auto-created via API call")
        
        media_items = Media.query.order_by(Media.upload_date.desc()).all()
        memories = []
        for item in media_items:
            memories.append({
                'id': item.id,
                'title': item.title,
                'date': item.upload_date.strftime('%b %d, %Y'),
                'story': item.description,
                'tags': item.tags,
                'filename': item.filename,
                'filetype': item.filetype
            })
        return jsonify({'status': 'success', 'memories': memories})
    except Exception as e:
        print(f"❌ Error in get_memories: {e}")
        # Return empty array on error - app should not crash
        return jsonify({'status': 'success', 'memories': []})

@app.route('/api/memories', methods=['POST'])
def add_memory():
    """API endpoint to upload a new memory (photo + story)."""
    try:
        if 'photo' not in request.files:
            return jsonify({'status': 'error', 'message': 'No photo file'}), 400
        
        file = request.files['photo']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'status': 'error', 'message': 'File type not allowed'}), 400

        # Create a safe, unique filename
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)

        # Get form data
        title = request.form.get('title', 'Untitled Memory')
        story = request.form.get('story', '')
        tags = request.form.get('tags', '')

        # Save to database with error handling
        try:
            new_memory = Media(
                title=title,
                description=story,
                filename=unique_filename,
                original_filename=secure_filename(file.filename),
                filetype=file_extension,
                uploaded_by='Catherine',
                tags=tags
            )

            db.session.add(new_memory)
            db.session.commit()

            return jsonify({
                'status': 'success',
                'message': 'Memory saved!',
                'memory': {
                    'id': new_memory.id,
                    'title': new_memory.title,
                    'date': new_memory.upload_date.strftime('%b %d, %Y'),
                    'story': new_memory.description,
                    'filename': new_memory.filename
                }
            })
        except Exception as db_error:
            print(f"❌ Database error saving memory: {db_error}")
            # Still return success for file upload, even if database fails
            return jsonify({
                'status': 'partial_success',
                'message': 'File uploaded but database save failed',
                'filename': unique_filename
            }), 207

    except Exception as e:
        print(f"❌ Error in add_memory: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === DEBUG/ADMIN ROUTES ===
@app.route('/debug/create-tables')
def debug_create_tables():
    """Special route to create database tables on demand."""
    try:
        with app.app_context():
            # Check current tables
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            if 'media' in existing_tables:
                return jsonify({
                    'status': 'info',
                    'message': 'Tables already exist',
                    'tables': existing_tables,
                    'table_count': len(existing_tables)
                })
            
            # Create tables
            db.create_all()
            
            # Verify
            inspector = inspect(db.engine)
            new_tables = inspector.get_table_names()
            
            return jsonify({
                'status': 'success',
                'message': f'Created {len(new_tables)} table(s)',
                'tables': new_tables,
                'table_count': len(new_tables)
            })
            
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'error_type': type(e).__name__
        }), 500

@app.route('/debug/health')
def debug_health():
    """Check app and database health."""
    try:
        with app.app_context():
            # Check database connection - FIXED: Use text()
            db.session.execute(text('SELECT 1'))
            db_ok = True
            
            # Check table existence
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            return jsonify({
                'status': 'healthy',
                'database': 'connected',
                'tables': tables,
                'table_count': len(tables),
                'upload_folder_exists': os.path.exists(UPLOAD_FOLDER),
                'database_url_type': 'PostgreSQL' if 'postgresql://' in database_url else 'SQLite'
            })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e),
            'error_type': type(e).__name__,
            'app_status': 'running'
        }), 500

@app.route('/debug/test-db')
def debug_test_db():
    """Test database connection specifically."""
    try:
        with app.app_context():
            # Test raw connection - FIXED: Use text()
            result = db.session.execute(text('SELECT version()')).fetchone()
            version = result[0] if result else 'Unknown'
            
            # Test table query - FIXED: Use text()
            table_count = db.session.execute(
                text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
            ).scalar()
            
            return jsonify({
                'status': 'success',
                'database_version': version,
                'table_count': table_count,
                'connection': 'established'
            })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e),
            'connection': 'failed',
            'database_url_preview': database_url[:50] + '...' if len(database_url) > 50 else database_url
        }), 500

# === SIMPLE HEALTH CHECK (NO DATABASE) ===
@app.route('/health')
def simple_health():
    """Simple health check that doesn't depend on database."""
    return jsonify({
        'status': 'running',
        'app': 'The Circle - Family Memory App',
        'timestamp': datetime.now().isoformat()
    })

# === UNIVERSAL STARTUP ===
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"\n🌍 Starting Flask server on port {port}...")
    print(f"📊 Database URL configured for: {'PostgreSQL' if 'postgresql://' in database_url else 'SQLite'}")
    print(f"🔒 SSL Mode: {'Enabled' if 'sslmode=require' in database_url else 'Not set'}")
    app.run(host='0.0.0.0', port=port)