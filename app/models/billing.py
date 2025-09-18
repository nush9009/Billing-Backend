from app import db
from datetime import datetime, timedelta
import uuid
from decimal import Decimal
from app.models import Project

# billing.py (Models)

from app import db
from datetime import datetime
import uuid

# REMOVED: ProjectPricing class is removed to simplify the flow.
# You can add it back later if you need a pricing catalog.

# -------------------- PROJECT BILLING --------------------
class ProjectBilling(db.Model):
    """A single billable item for a project."""
    __tablename__ = 'project_billing'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    
    
    billing_type = db.Column(db.String(50), nullable=False)  # e.g., 'Milestone', 'Monthly Retainer'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    description = db.Column(db.Text)
    
    # This status is now the single source of truth for payment.
    # ('pending', 'invoiced', 'paid', 'cancelled')
    status = db.Column(db.String(20), default='pending', nullable=False)
    due_date = db.Column(db.Date)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    project = db.relationship('Project', backref='billing_records')
    # This relationship links this bill to its one and only invoice.
    invoice = db.relationship('Invoice', back_populates='billing_record', uselist=False)


# -------------------- INVOICE --------------------
# billing.py (Models) - Invoice class only

class Invoice(db.Model):
    """The official invoice generated from a single ProjectBilling record."""
    __tablename__ = 'invoices'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    billing_record_id = db.Column(db.String(36), db.ForeignKey('project_billing.id'), nullable=False, unique=True)
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    
    

    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    
    status = db.Column(db.String(20), default='draft', nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date)
    
    notes = db.Column(db.Text)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    billing_record = db.relationship('ProjectBilling', back_populates='invoice')
    project = db.relationship('Project')


