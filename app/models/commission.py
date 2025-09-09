from app import db
from datetime import datetime
import uuid

class Commission(db.Model):
    __tablename__ = 'commissions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # UPDATED: ForeignKey now points to the 'tier1_sellers' table.
    seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'))
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'))
    # UPDATED: ForeignKey now points to the 'admins' table.
    client_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    commission_amount = db.Column(db.Numeric(10, 2), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # setup_fee/recurring_fee
    status = db.Column(db.String(20), default='pending')  # pending/paid/cancelled
    transaction_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Report(db.Model):
    __tablename__ = 'reports'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # UPDATED: ForeignKey now points to the 'admins' table.
    client_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=False)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'))
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')  # draft/published/archived
    sections = db.Column(db.JSON)
    file_url = db.Column(db.Text)
    published_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
