from app import db
from datetime import datetime
import uuid

class Tier1Seller(db.Model):
   
    __tablename__ = 'tier1_sellers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    subdomain = db.Column(db.String(100), unique=True, nullable=True)
    admin_email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # commission_type = db.Column(db.String(50))
    # commission_value = db.Column(db.Numeric(10, 2))
    logo_url = db.Column(db.Text)
    stylesheet_url = db.Column(db.Text)
    site_content = db.Column(db.JSON)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tier2_sellers = db.relationship('Tier2Seller', backref='parent_tier1_seller', lazy=True)
    admins = db.relationship('Admin', backref='tier1_seller', lazy=True)


class Tier2Seller(db.Model):
    __tablename__ = 'tier2_sellers'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    subdomain = db.Column(db.String(100), unique=True, nullable=True)
    admin_email = db.Column(db.String(255), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    # commission_type = db.Column(db.String(50))
    # commission_value = db.Column(db.Numeric(10, 2))
    deleted_at = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships

    admins = db.relationship('Admin', backref='tier2_seller', lazy=True)
  

