from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Media(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200))
    description = db.Column(db.Text)
    filename = db.Column(db.String(300), unique=True)
    original_filename = db.Column(db.String(300))
    filetype = db.Column(db.String(50))
    thumbnail = db.Column(db.String(300))
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)
    uploaded_by = db.Column(db.String(100))
    tags = db.Column(db.String(500))
    family_group_id = db.Column(db.Integer, db.ForeignKey('family_group.id'))
    comments = db.relationship('Comment', backref='media', lazy=True, cascade='all, delete-orphan')

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200))
    family_group_id = db.Column(db.Integer, db.ForeignKey('family_group.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FamilyGroup(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(50), unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    media = db.relationship('Media', backref='family_group', lazy=True)
    users = db.relationship('User', backref='family_group', lazy=True)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    author = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    media_id = db.Column(db.Integer, db.ForeignKey('media.id'), nullable=False)

def init_db(app):
    db.init_app(app)
    with app.app_context():
        db.create_all()