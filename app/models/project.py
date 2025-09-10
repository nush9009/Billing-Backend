from app import db
from datetime import datetime
import uuid

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='active')
    project_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    project_value = db.Column(db.Numeric(12, 2))
    billing_frequency = db.Column(db.String(20), default='milestone')
    hourly_budget = db.Column(db.Numeric(8, 2))
    hours_used = db.Column(db.Numeric(8, 2), default=0)
    budget_spent = db.Column(db.Numeric(12, 2), default=0)
    admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True) 
    tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'), nullable=True)
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'), nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clients = db.relationship('Client', backref='project', lazy=True)



class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))  # optional
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

