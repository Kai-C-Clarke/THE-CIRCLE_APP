from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Media(db.Model):
    """Represents a family memory (photo + story)."""
    __tablename__ = 'circle_table'  # CRITICAL: Matches your Railway table
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)  # The "story"
    filename = db.Column(db.String(300), unique=True)
    original_filename = db.Column(db.String(300))
    filetype = db.Column(db.String(50))
    thumbnail = db.Column(db.String(300))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.String(100))
    tags = db.Column(db.String(500))
    # REMOVED: family_group_id and comments for now
    # family_group_id = db.Column(db.Integer, db.ForeignKey('family_group.id'))
    # comments = db.relationship('Comment', backref='media', lazy=True, cascade='all, delete-orphan')

# REMOVED FOR NOW: User, FamilyGroup, Comment classes
# We'll add these back later once basic uploads work

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("✅ Database initialized with table 'circle_table'")