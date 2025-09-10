from app import db
from datetime import datetime
import uuid

# RENAMED: The 'Client' model is now 'Admin' as requested.
class Admin(db.Model):
    # The table in the database will now be named 'admins'.
    __tablename__ = 'admins'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # RENAMED & UPDATED: This now links to the new 'tier1_sellers' table.
    tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'))
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'))
    
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))
    status = db.Column(db.String(20), default='active')
    intake_form_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # UPDATED: The back-references are updated to reflect the new class name 'Admin'.
    projects = db.relationship('Project', backref='admin', lazy=True)
    clients= db.relationship('Client', backref='admin', lazy=True)
    
