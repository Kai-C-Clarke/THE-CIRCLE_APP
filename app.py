import os
import json
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, flash
from flask_cors import CORS
from database import init_db, db, Media, User, FamilyGroup, Comment
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
import uuid
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Replit-specific configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///circle.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Replit media upload folder
UPLOAD_FOLDER = 'static/uploads'
THUMBNAIL_FOLDER = 'static/thumbnails'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi', 'mkv', 'pdf', 'doc', 'docx'}

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(THUMBNAIL_FOLDER, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['THUMBNAIL_FOLDER'] = THUMBNAIL_FOLDER

# Initialize database
init_db(app)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/test')
def test_api():
    return jsonify({'status': 'success', 'message': 'API is working!'})

@app.route('/api/media', methods=['GET'])
def get_media():
    """Get all media items"""
    try:
        media_items = Media.query.order_by(Media.upload_date.desc()).all()
        result = []
        for item in media_items:
            result.append({
                'id': item.id,
                'title': item.title,
                'description': item.description,
                'filename': item.filename,
                'filetype': item.filetype,
                'thumbnail': item.thumbnail,
                'upload_date': item.upload_date.isoformat(),
                'uploaded_by': item.uploaded_by,
                'tags': item.tags,
                'family_group_id': item.family_group_id
            })
        return jsonify({'status': 'success', 'media': result})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/media/upload', methods=['POST'])
def upload_media():
    """Upload media file"""
    try:
        if 'file' not in request.files:
            return jsonify({'status': 'error', 'message': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'status': 'error', 'message': 'No selected file'}), 400
        
        if file and allowed_file(file.filename):
            # Generate unique filename
            original_filename = secure_filename(file.filename)
            file_extension = original_filename.rsplit('.', 1)[1].lower()
            unique_filename = f"{uuid.uuid4().hex}.{file_extension}"
            
            # Save file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
            file.save(file_path)
            
            # Get form data
            title = request.form.get('title', original_filename)
            description = request.form.get('description', '')
            uploaded_by = request.form.get('uploaded_by', 'Anonymous')
            tags = request.form.get('tags', '')
            family_group_id = request.form.get('family_group_id', 1)
            
            # Create thumbnail for images
            thumbnail_filename = None
            if file_extension in ['png', 'jpg', 'jpeg', 'gif']:
                try:
                    from PIL import Image
                    img = Image.open(file_path)
                    img.thumbnail((300, 300))
                    thumbnail_filename = f"thumb_{unique_filename}"
                    thumbnail_path = os.path.join(app.config['THUMBNAIL_FOLDER'], thumbnail_filename)
                    img.save(thumbnail_path)
                except Exception as e:
                    print(f"Thumbnail creation failed: {e}")
                    thumbnail_filename = None
            
            # Save to database
            new_media = Media(
                title=title,
                description=description,
                filename=unique_filename,
                original_filename=original_filename,
                filetype=file_extension,
                thumbnail=thumbnail_filename,
                uploaded_by=uploaded_by,
                tags=tags,
                family_group_id=family_group_id
            )
            
            db.session.add(new_media)
            db.session.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'File uploaded successfully',
                'media_id': new_media.id,
                'filename': unique_filename
            })
        
        return jsonify({'status': 'error', 'message': 'File type not allowed'}), 400
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/media/<int:media_id>', methods=['DELETE'])
def delete_media(media_id):
    """Delete media item"""
    try:
        media = Media.query.get(media_id)
        if media:
            # Delete file
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], media.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Delete thumbnail if exists
            if media.thumbnail:
                thumb_path = os.path.join(app.config['THUMBNAIL_FOLDER'], media.thumbnail)
                if os.path.exists(thumb_path):
                    os.remove(thumb_path)
            
            db.session.delete(media)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Media deleted'})
        
        return jsonify({'status': 'error', 'message': 'Media not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# Initialize sample data
@app.before_first_request
def create_tables():
    db.create_all()
    # Add sample family group if none exists
    if FamilyGroup.query.count() == 0:
        family = FamilyGroup(name="Smith Family", code="CIRCLE123")
        db.session.add(family)
        db.session.commit()
        print("Created sample family group")

# Replit-specific: Add error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'status': 'error', 'message': 'Not found'}), 404

@app.errorhandler(500)
def server_error(error):
    return jsonify({'status': 'error', 'message': 'Server error'}), 500

# For Replit deployment
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)