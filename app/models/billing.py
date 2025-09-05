from app import db
from datetime import datetime, date
import uuid
from decimal import Decimal
from sqlalchemy import func

class ProjectPricing(db.Model):
    """Pricing structure for different project types"""
    __tablename__ = 'project_pricing'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    seller_id = db.Column(db.String(36), db.ForeignKey('sellers.id'))
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'))
    project_type = db.Column(db.String(100), nullable=False)  # Market Research, Strategy, etc.
    pricing_model = db.Column(db.String(50), nullable=False)  # fixed, hourly, milestone
    base_price = db.Column(db.Numeric(12, 2), nullable=False)
    hourly_rate = db.Column(db.Numeric(10, 2))  # If hourly pricing
    currency = db.Column(db.String(3), default='USD')
    description = db.Column(db.Text)
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ProjectBilling(db.Model):
    """Billing records for individual projects"""
    __tablename__ = 'project_billing'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    pricing_id = db.Column(db.String(36), db.ForeignKey('project_pricing.id'))
    
    # Billing details
    billing_type = db.Column(db.String(50), nullable=False)  # setup, monthly, milestone, completion
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    hours_worked = db.Column(db.Numeric(8, 2))  # For hourly billing
    milestone_description = db.Column(db.Text)
    
    # Status and dates
    status = db.Column(db.String(20), default='pending')  # pending, invoiced, paid, cancelled
    due_date = db.Column(db.Date)
    invoice_date = db.Column(db.Date)
    paid_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref='billing_records', lazy=True)
    pricing = db.relationship('ProjectPricing', backref='billing_records', lazy=True)

class Invoice(db.Model):
    """Invoice generation for clients"""
    __tablename__ = 'invoices'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    client_id = db.Column(db.String(36), db.ForeignKey('clients.id'), nullable=False)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # Invoice totals
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(12, 2), default=0)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    # Status and dates
    status = db.Column(db.String(20), default='draft')  # draft, sent, paid, overdue, cancelled
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    
    # Invoice details
    invoice_data = db.Column(db.JSON)  # Detailed line items
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    client = db.relationship('Client', backref='invoices', lazy=True)