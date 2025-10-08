# app/tasks.py

from datetime import date
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import uuid

from . import create_app, db
from .models.project import Project
from .models.billing import ProjectBilling, Invoice
def generate_monthly_invoices():
    """
    A scheduled task to automatically generate bills and invoices for active projects.
    """
    app = create_app()
    with app.app_context():
        today = date.today()
        print(f"Running monthly billing job on {today}...")

        projects_to_bill = Project.query.filter(
            Project.status == 'active',
            Project.next_billing_date <= today
        ).all()

        if not projects_to_bill:
            print("No projects are due for billing today.")
            return

        for project in projects_to_bill:
            try:
                if not project.subscription_plan or not project.subscription_plan.price:
                    print(f"Skipping project {project.id} - no active subscription plan with a price.")
                    continue

                new_bill = ProjectBilling(
                    project_id=project.id,
                    billing_type='Monthly Retainer',
                    amount=Decimal(project.subscription_plan.price),
                    description=f"Monthly service for {today.strftime('%B %Y')}",
                    status='pending',
                    due_date=today + relativedelta(days=15)
                )
                db.session.add(new_bill)

                new_invoice = Invoice(
                    billing_record=new_bill,
                    project_id=project.id,
                    invoice_number=f"INV-{uuid.uuid4().hex[:6].upper()}",
                    total_amount=new_bill.amount,
                    issue_date=today,
                    due_date=new_bill.due_date,
                    status='sent'
                )
                new_bill.status = 'invoiced'
                db.session.add(new_invoice)

                project.next_billing_date = today + relativedelta(months=1)
                
                print(f"Successfully generated invoice for project {project.id}.")

            except Exception as e:
                db.session.rollback()
                print(f"Error processing project {project.id}: {str(e)}")
                continue
        
        db.session.commit()
        print("Monthly billing job finished.")