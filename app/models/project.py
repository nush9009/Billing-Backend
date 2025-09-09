from app import db
from datetime import datetime
import uuid

class Project(db.Model):
    __tablename__ = 'projects'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # UPDATED: ForeignKey now points to the 'admins' table.
    client_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=False)
    name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(20), default='active')
    project_type = db.Column(db.String(100))
    description = db.Column(db.Text)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    project_value = db.Column(db.Numeric(12, 2))  # Total project value
    billing_frequency = db.Column(db.String(20), default='milestone')  # monthly, milestone, completion
    hourly_budget = db.Column(db.Numeric(8, 2))  # Total hours budgeted
    hours_used = db.Column(db.Numeric(8, 2), default=0)  # Hours consumed
    budget_spent = db.Column(db.Numeric(12, 2), default=0)  # Amount already billed
    
    # Relationships
    reports = db.relationship('Report', backref='project', lazy=True)

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # UPDATED: ForeignKey now points to the 'admins' table.
    client_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # admin/manager/viewer
    status = db.Column(db.String(20), default='active')
    password_hash = db.Column(db.String(255))
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
