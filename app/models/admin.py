from app import db
from datetime import datetime
import uuid

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'))
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))
    # status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='admin', lazy=True)
    clients= db.relationship('Client', backref='admin', lazy=True)
    
    
    
