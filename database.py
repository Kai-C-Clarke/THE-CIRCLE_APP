from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Media(db.Model):
    """Represents a family memory (photo + story)."""
    __tablename__ = 'circle_table'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    filename = db.Column(db.String(300), unique=True)
    original_filename = db.Column(db.String(300))
    filetype = db.Column(db.String(50))
    thumbnail = db.Column(db.String(300))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.String(100))
    tags = db.Column(db.String(500))
    
    # ADD THESE COLUMNS to match your code:
    name = db.Column(db.String(200))  # For 'name' parameter
    relationship = db.Column(db.String(100))  # For 'relationship'
    memory = db.Column(db.Text)  # For 'memory' (could also use description)
    year = db.Column(db.Integer)  # For 'year'
    photo_url = db.Column(db.String(300))  # For 'photo_url'

# REMOVED FOR NOW: User, FamilyGroup, Comment classes
# We'll add these back later once basic uploads work

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("✅ Database initialized with table 'circle_table'")