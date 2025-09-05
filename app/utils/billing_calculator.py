from app.models.billing import ProjectPricing, ProjectBilling, Invoice
from app.models import Project, Client, Seller
from decimal import Decimal
from datetime import datetime, timedelta
from app import db

class BillingCalculator:
    """Handle all billing calculations for projects"""
    
    @staticmethod
    def calculate_project_billing(project_id):
        """Calculate total billing for a specific project"""
        project = Project.query.get(project_id)
        if not project:
            return None
        
        billing_records = ProjectBilling.query.filter_by(project_id=project_id).all()
        
        total_billed = sum(Decimal(str(record.amount)) for record in billing_records)
        pending_amount = sum(Decimal(str(record.amount)) for record in billing_records if record.status == 'pending')
        paid_amount = sum(Decimal(str(record.amount)) for record in billing_records if record.status == 'paid')
        
        return {
            'project_id': project_id,
            'project_name': project.name,
            'total_project_value': float(project.project_value) if project.project_value else 0,
            'total_billed': float(total_billed),
            'pending_amount': float(pending_amount),
            'paid_amount': float(paid_amount),
            'remaining_value': float(project.project_value - total_billed) if project.project_value else 0,
            'billing_records': len(billing_records)
        }
    
    @staticmethod
    def calculate_seller_revenue(seller_id):
        """Calculate total revenue for a Tier-1 seller across all projects"""
        seller = Seller.query.get(seller_id)
        if not seller:
            return None
        
        # Get all clients under this seller
        clients = Client.query.filter_by(seller_id=seller_id).all()
        client_ids = [client.id for client in clients]
        
        # Get all projects for these clients
        projects = Project.query.filter(Project.client_id.in_(client_ids)).all()
        
        total_revenue = Decimal('0')
        total_pending = Decimal('0')
        total_paid = Decimal('0')
        project_breakdown = []
        
        for project in projects:
            billing_summary = BillingCalculator.calculate_project_billing(project.id)
            if billing_summary:
                total_revenue += Decimal(str(billing_summary['total_billed']))
                total_pending += Decimal(str(billing_summary['pending_amount']))
                total_paid += Decimal(str(billing_summary['paid_amount']))
                project_breakdown.append(billing_summary)
        
        return {
            'seller_id': seller_id,
            'seller_name': seller.name,
            'total_revenue': float(total_revenue),
            'total_pending': float(total_pending),
            'total_paid': float(total_paid),
            'total_projects': len(projects),
            'active_projects': len([p for p in projects if p.status == 'active']),
            'project_breakdown': project_breakdown
        }
    
    @staticmethod
    def create_project_billing(project_id, billing_type, amount, hours_worked=None, milestone_description=None):
        """Create a new billing record for a project"""
        try:
            new_billing = ProjectBilling(
                project_id=project_id,
                billing_type=billing_type,
                amount=amount,
                hours_worked=hours_worked,
                milestone_description=milestone_description,
                due_date=datetime.now().date() + timedelta(days=30)  # 30 days payment terms
            )
            
            db.session.add(new_billing)
            
            # Update project budget spent
            project = Project.query.get(project_id)
            if project:
                current_spent = project.budget_spent or Decimal('0')
                project.budget_spent = current_spent + Decimal(str(amount))
                
                if hours_worked:
                    current_hours = project.hours_used or Decimal('0')
                    project.hours_used = current_hours + Decimal(str(hours_worked))
            
            db.session.commit()
            return new_billing
            
        except Exception as e:
            db.session.rollback()
            raise e
    
    @staticmethod
    def generate_invoice_for_client(client_id, billing_records_ids):
        """Generate an invoice for a client based on billing records"""
        client = Client.query.get(client_id)
        if not client:
            return None
        
        billing_records = ProjectBilling.query.filter(
            ProjectBilling.id.in_(billing_records_ids),
            ProjectBilling.status == 'pending'
        ).all()
        
        if not billing_records:
            return None
        
        subtotal = sum(Decimal(str(record.amount)) for record in billing_records)
        tax_rate = Decimal('0.08')  # 8% tax (configurable)
        tax_amount = subtotal * tax_rate
        total_amount = subtotal + tax_amount
        
        # Generate invoice number
        invoice_count = Invoice.query.count() + 1
        invoice_number = f"INV-{datetime.now().year}-{invoice_count:04d}"
        
        # Create invoice
        invoice = Invoice(
            client_id=client_id,
            invoice_number=invoice_number,
            subtotal=subtotal,
            tax_amount=tax_amount,
            total_amount=total_amount,
            issue_date=datetime.now().date(),
            due_date=datetime.now().date() + timedelta(days=30),
            invoice_data={
                'line_items': [
                    {
                        'project_name': record.project.name,
                        'billing_type': record.billing_type,
                        'description': record.milestone_description or f"{record.billing_type.title()} payment",
                        'amount': float(record.amount),
                        'hours': float(record.hours_worked) if record.hours_worked else None
                    }
                    for record in billing_records
                ]
            }
        )
        
        db.session.add(invoice)
        
        # Update billing records status
        for record in billing_records:
            record.status = 'invoiced'
            record.invoice_date = datetime.now().date()
        
        db.session.commit()
        return invoice