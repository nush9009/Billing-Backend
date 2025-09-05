from app import db
from datetime import datetime
import uuid

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = db.Column(db.String(36), db.ForeignKey('sellers.id'))
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'))
    plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'))
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))
    status = db.Column(db.String(20), default='active')
    intake_form_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects = db.relationship('Project', backref='client', lazy=True)
    users = db.relationship('User', backref='client', lazy=True)
    commissions = db.relationship('Commission', backref='client', lazy=True)
    reports = db.relationship('Report', backref='client', lazy=True)

class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = db.Column(db.String(36), db.ForeignKey('sellers.id'))
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'))
    name = db.Column(db.String(255), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), default='USD')
    billing = db.Column(db.String(20), nullable=False)  # monthly/yearly
    features = db.Column(db.JSON)
    max_clients = db.Column(db.Integer)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    clients = db.relationship('Client', backref='subscription_plan', lazy=True)