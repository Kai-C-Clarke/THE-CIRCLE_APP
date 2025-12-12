import os
import sys
import json
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
from database import init_db, db, Media
import uuid
from datetime import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)

# === UNIVERSAL CONFIGURATION ===
# Use environment variables with safe defaults
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-for-local-testing-123')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///circle.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Folder setup - works everywhere
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize Database
init_db(app)

# === ADD THIS BLOCK ===
# Ensure tables are created on startup
with app.app_context():
    db.create_all()
    print("✅ Database tables verified/created")
# === END ADDED BLOCK ===

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
        return jsonify({'status': 'error', 'message': str(e)}), 500

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

        # Save to database
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

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/static/uploads/<filename>')
def uploaded_file(filename):
    """Serve uploaded files."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# === UNIVERSAL STARTUP ===
# This works on Railway (reads PORT env var) and locally (defaults to 5000)
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)