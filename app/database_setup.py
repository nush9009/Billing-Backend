# app/database_setup.py
"""
Automatic database setup and initialization
"""
from flask import current_app
from app import db, bcrypt
from app.models import Seller, Tier2Seller, SubscriptionPlan, Client, Project
from app.models.billing import ProjectPricing, ProjectBilling, Invoice
from app.models.project import User
import os
import uuid
from datetime import datetime, date
from decimal import Decimal
from datetime import datetime, timedelta

def check_database_exists():
    """Check if database tables exist"""
    try:
        # Try to query a table to see if it exists
        db.session.execute('SELECT 1 FROM sellers LIMIT 1')
        return True
    except Exception:
        return False
    
def create_billing_sample_data():
    """Create sample billing data"""
    try:
        print("Creating billing sample data...")
        
        # Check if billing data already exists
        if ProjectPricing.query.first():
            print("📋 Billing sample data already exists, skipping...")
            return True
        
        # Get existing sellers and projects
        market_trends = Seller.query.filter_by(subdomain='marketstrendai').first()
        xyz_seller = Seller.query.filter_by(subdomain='xyzseller').first()
        tier2_seller = Tier2Seller.query.filter_by(subdomain='datainsightspro').first()
        
        # Create project pricing structures
        pricing_data = [
            # MarketTrendsAI pricing
            {
                'seller_id': market_trends.id,
                'project_type': 'Market Research',
                'pricing_model': 'fixed',
                'base_price': 5000.00,
                'description': 'Comprehensive market analysis and research'
            },
            {
                'seller_id': market_trends.id,
                'project_type': 'Competitive Analysis', 
                'pricing_model': 'fixed',
                'base_price': 3500.00,
                'description': 'Detailed competitor analysis and positioning'
            },
            {
                'seller_id': market_trends.id,
                'project_type': 'Strategy Consulting',
                'pricing_model': 'hourly',
                'base_price': 0,
                'hourly_rate': 150.00,
                'description': 'Strategic planning and consulting services'
            },
            
            # XYZSeller pricing
            {
                'seller_id': xyz_seller.id,
                'project_type': 'Process Improvement',
                'pricing_model': 'milestone',
                'base_price': 8000.00,
                'description': 'Business process optimization and improvement'
            },
            {
                'seller_id': xyz_seller.id,
                'project_type': 'Technical Implementation',
                'pricing_model': 'hourly',
                'base_price': 0,
                'hourly_rate': 120.00,
                'description': 'Technical system implementation and support'
            },
            
            # Tier2 Seller pricing
            {
                'tier2_seller_id': tier2_seller.id,
                'project_type': 'Industry Analysis',
                'pricing_model': 'fixed',
                'base_price': 4500.00,
                'description': 'In-depth industry analysis and reporting'
            }
        ]
        
        pricing_records = []
        for pricing_info in pricing_data:
            pricing = ProjectPricing(**pricing_info)
            pricing_records.append(pricing)
        
        db.session.add_all(pricing_records)
        db.session.commit()
        
        # Update existing projects with billing information
        projects_billing_data = [
            {'name': 'Forte Market Analysis', 'project_value': 5000.00, 'billing_frequency': 'milestone', 'hourly_budget': 35},
            {'name': 'Forte Competitor Study', 'project_value': 3500.00, 'billing_frequency': 'completion', 'hourly_budget': 25},
            {'name': 'Servicon Growth Strategy', 'project_value': 12000.00, 'billing_frequency': 'monthly', 'hourly_budget': 80},
            {'name': 'Servicon Data Migration', 'project_value': 8000.00, 'billing_frequency': 'milestone', 'hourly_budget': 67},
            {'name': 'Cementech Industry Report', 'project_value': 4500.00, 'billing_frequency': 'completion', 'hourly_budget': 30},
            {'name': 'PPI Process Optimization', 'project_value': 8000.00, 'billing_frequency': 'milestone', 'hourly_budget': 67}
        ]
        
        for project_info in projects_billing_data:
            project = Project.query.filter_by(name=project_info['name']).first()
            if project:
                project.project_value = project_info['project_value']
                project.billing_frequency = project_info['billing_frequency']
                project.hourly_budget = project_info['hourly_budget']
                
                # Simulate some work done
                if project.status == 'active':
                    project.hours_used = project_info['hourly_budget'] * 0.6  # 60% complete
                elif project.status == 'completed':
                    project.hours_used = project_info['hourly_budget']
                elif project.status == 'paused':
                    project.hours_used = project_info['hourly_budget'] * 0.3  # 30% complete
        
        db.session.commit()
        
        # Create sample billing records
        forte_market_project = Project.query.filter_by(name='Forte Market Analysis').first()
        forte_competitor_project = Project.query.filter_by(name='Forte Competitor Study').first()
        servicon_strategy_project = Project.query.filter_by(name='Servicon Growth Strategy').first()
        cementech_project = Project.query.filter_by(name='Cementech Industry Report').first()
        ppi_project = Project.query.filter_by(name='PPI Process Optimization').first()
        
        billing_records = [
            # Forte Market Analysis - Milestone billing
            ProjectBilling(
                project_id=forte_market_project.id,
                billing_type='setup',
                amount=1500.00,
                status='paid',
                milestone_description='Project initiation and planning',
                paid_date=datetime.now().date() - timedelta(days=45)
            ),
            ProjectBilling(
                project_id=forte_market_project.id,
                billing_type='milestone',
                amount=2000.00,
                status='paid',
                milestone_description='Market research completion',
                paid_date=datetime.now().date() - timedelta(days=20)
            ),
            ProjectBilling(
                project_id=forte_market_project.id,
                billing_type='milestone',
                amount=1500.00,
                status='pending',
                milestone_description='Final report and presentation',
                due_date=datetime.now().date() + timedelta(days=15)
            ),
            
            # Forte Competitor Study - Completed project
            ProjectBilling(
                project_id=forte_competitor_project.id,
                billing_type='completion',
                amount=3500.00,
                status='paid',
                milestone_description='Complete competitive analysis report',
                paid_date=datetime.now().date() - timedelta(days=10)
            ),
            
            # Servicon Growth Strategy - Monthly billing
            ProjectBilling(
                project_id=servicon_strategy_project.id,
                billing_type='monthly',
                amount=3000.00,
                hours_worked=20.0,
                status='paid',
                milestone_description='Month 1 - Strategy development',
                paid_date=datetime.now().date() - timedelta(days=30)
            ),
            ProjectBilling(
                project_id=servicon_strategy_project.id,
                billing_type='monthly',
                amount=3000.00,
                hours_worked=20.0,
                status='invoiced',
                milestone_description='Month 2 - Implementation planning',
                invoice_date=datetime.now().date() - timedelta(days=5)
            ),
            
            # Cementech Industry Report
            ProjectBilling(
                project_id=cementech_project.id,
                billing_type='setup',
                amount=1500.00,
                status='paid',
                milestone_description='Research initiation',
                paid_date=datetime.now().date() - timedelta(days=25)
            ),
            ProjectBilling(
                project_id=cementech_project.id,
                billing_type='completion',
                amount=3000.00,
                status='pending',
                milestone_description='Final industry analysis report',
                due_date=datetime.now().date() + timedelta(days=20)
            ),
            
            # PPI Process Optimization - Milestone billing
            ProjectBilling(
                project_id=ppi_project.id,
                billing_type='milestone',
                amount=2500.00,
                status='paid',
                milestone_description='Process analysis and mapping',
                paid_date=datetime.now().date() - timedelta(days=15)
            ),
            ProjectBilling(
                project_id=ppi_project.id,
                billing_type='milestone',
                amount=3000.00,
                status='pending',
                milestone_description='Process improvement recommendations',
                due_date=datetime.now().date() + timedelta(days=10)
            ),
            ProjectBilling(
                project_id=ppi_project.id,
                billing_type='milestone',
                amount=2500.00,
                status='pending',
                milestone_description='Implementation support',
                due_date=datetime.now().date() + timedelta(days=45)
            )
        ]
        
        db.session.add_all(billing_records)
        db.session.commit()
        
        # Update project budget spent based on billing records
        for project in [forte_market_project, forte_competitor_project, servicon_strategy_project, cementech_project, ppi_project]:
            paid_amount = sum(
                Decimal(str(record.amount)) 
                for record in project.billing_records 
                if record.status in ['paid', 'invoiced']
            )
            project.budget_spent = paid_amount
        
        db.session.commit()
        
        print("✅ Billing sample data created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating billing sample data: {str(e)}")
        db.session.rollback()
        return False    

def create_database_tables():
    """Create all database tables"""
    try:
        print("Creating database tables...")
        db.create_all()
        print("✅ Database tables created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {str(e)}")
        return False

def create_sample_data():
    """Create sample data for development"""
    try:
        print("Creating sample data...")
        
        # Check if data already exists
        if Seller.query.first():
            print("📋 Sample data already exists, skipping...")
            return True
        
        # Create sample sellers
        password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
        
        # JupiterBrains Admin (Root)
        jupiter_admin = Seller(
            name='JupiterBrains',
            subdomain='admin',
            admin_email='admin@jupiterbrains.com',
            password_hash=password_hash,
            commission_type='percentage',
            commission_value=5.00,
            status='active',
            site_content={
                'company_description': 'Root admin for the platform',
                'theme': 'admin'
            }
        )
        
        # MarketTrendsAI (Tier-1 Seller)
        market_trends = Seller(
            name='MarketTrendsAI',
            subdomain='marketstrendai',
            admin_email='admin@marketstrendai.com',
            password_hash=password_hash,
            commission_type='percentage',
            commission_value=15.00,
            status='active',
            site_content={
                'company_description': 'AI-powered market analysis platform',
                'theme': 'blue'
            }
        )
        
        # XYZSeller (Tier-1 Seller)
        xyz_seller = Seller(
            name='XYZSeller',
            subdomain='xyzseller',
            admin_email='admin@xyzseller.com',
            password_hash=password_hash,
            commission_type='percentage',
            commission_value=20.00,
            status='active',
            site_content={
                'company_description': 'Professional services provider',
                'theme': 'green'
            }
        )
        
        db.session.add_all([jupiter_admin, market_trends, xyz_seller])
        db.session.commit()
        
        # Create Tier-2 seller under MarketTrendsAI
        tier2_seller = Tier2Seller(
            tier1_seller_id=market_trends.id,
            name='DataInsights Pro',
            subdomain='datainsightspro',
            admin_email='admin@datainsightspro.com',
            password_hash=password_hash,
            commission_type='percentage',
            commission_value=10.00
        )
        
        db.session.add(tier2_seller)
        db.session.commit()
        
        # Create subscription plans
        plans_data = [
            {
                'seller': market_trends,
                'plans': [
                    {'name': 'Basic Plan', 'price': 99.99, 'billing': 'monthly', 'features': ['Basic Analytics', 'Email Support', '5 Projects'], 'max_clients': 10},
                    {'name': 'Pro Plan', 'price': 199.99, 'billing': 'monthly', 'features': ['Advanced Analytics', 'Priority Support', '25 Projects', 'Custom Reports'], 'max_clients': 50},
                    {'name': 'Enterprise Plan', 'price': 499.99, 'billing': 'monthly', 'features': ['All Features', 'Dedicated Manager', 'Unlimited Projects', 'API Access'], 'max_clients': 200}
                ]
            },
            {
                'seller': xyz_seller,
                'plans': [
                    {'name': 'Starter Package', 'price': 149.99, 'billing': 'monthly', 'features': ['Core Services', 'Email Support', '3 Projects'], 'max_clients': 5},
                    {'name': 'Business Package', 'price': 299.99, 'billing': 'monthly', 'features': ['All Core Services', 'Phone Support', '15 Projects', 'Monthly Reports'], 'max_clients': 25}
                ]
            }
        ]
        
        all_plans = []
        for seller_data in plans_data:
            seller = seller_data['seller']
            for plan_info in seller_data['plans']:
                plan = SubscriptionPlan(
                    seller_id=seller.id,
                    name=plan_info['name'],
                    price=plan_info['price'],
                    billing=plan_info['billing'],
                    features=plan_info['features'],
                    max_clients=plan_info['max_clients']
                )
                all_plans.append(plan)
        
        # Add tier2 seller plan
        tier2_plan = SubscriptionPlan(
            tier2_seller_id=tier2_seller.id,
            name='Data Analytics Suite',
            price=179.99,
            billing='monthly',
            features=['Data Visualization', 'Trend Analysis', '10 Projects'],
            max_clients=15
        )
        all_plans.append(tier2_plan)
        
        db.session.add_all(all_plans)
        db.session.commit()
        
        # Create sample clients
        basic_plan = SubscriptionPlan.query.filter_by(name='Basic Plan').first()
        pro_plan = SubscriptionPlan.query.filter_by(name='Pro Plan').first()
        tier2_plan_db = SubscriptionPlan.query.filter_by(name='Data Analytics Suite').first()
        
        clients_data = [
            {
                'seller_id': market_trends.id,
                'plan_id': basic_plan.id,
                'name': 'John Smith',
                'email': 'john@forte.com',
                'company': 'Forte Corp',
                'intake_form_completed': True
            },
            {
                'seller_id': market_trends.id,
                'plan_id': pro_plan.id,
                'name': 'Sarah Johnson',
                'email': 'sarah@servicon.com',
                'company': 'Servicon Ltd',
                'intake_form_completed': True
            },
            {
                'tier2_seller_id': tier2_seller.id,
                'plan_id': tier2_plan_db.id,
                'name': 'Mike Davis',
                'email': 'mike@cementech.com',
                'company': 'Cementech Industries',
                'intake_form_completed': False
            },
            {
                'seller_id': xyz_seller.id,
                'plan_id': SubscriptionPlan.query.filter_by(name='Starter Package').first().id,
                'name': 'Lisa Wong',
                'email': 'lisa@ppi.com',
                'company': 'PPI Solutions',
                'intake_form_completed': True
            }
        ]
        
        clients = []
        for client_data in clients_data:
            client = Client(**client_data)
            clients.append(client)
        
        db.session.add_all(clients)
        db.session.commit()
        
        # Create sample projects
        forte_client = Client.query.filter_by(email='john@forte.com').first()
        servicon_client = Client.query.filter_by(email='sarah@servicon.com').first()
        cementech_client = Client.query.filter_by(email='mike@cementech.com').first()
        ppi_client = Client.query.filter_by(email='lisa@ppi.com').first()
        
        projects_data = [
            {'client_id': forte_client.id, 'name': 'Forte Market Analysis', 'status': 'active', 'project_type': 'Market Research'},
            {'client_id': forte_client.id, 'name': 'Forte Competitor Study', 'status': 'completed', 'project_type': 'Competitive Analysis'},
            {'client_id': servicon_client.id, 'name': 'Servicon Growth Strategy', 'status': 'active', 'project_type': 'Strategy Consulting'},
            {'client_id': servicon_client.id, 'name': 'Servicon Data Migration', 'status': 'paused', 'project_type': 'Technical Implementation'},
            {'client_id': cementech_client.id, 'name': 'Cementech Industry Report', 'status': 'active', 'project_type': 'Industry Analysis'},
            {'client_id': ppi_client.id, 'name': 'PPI Process Optimization', 'status': 'active', 'project_type': 'Process Improvement'}
        ]
        
        projects = []
        for project_data in projects_data:
            project = Project(**project_data)
            projects.append(project)
        
        db.session.add_all(projects)
        db.session.commit()
        
        # Create sample users for client portals
        client_password_hash = bcrypt.generate_password_hash('client123').decode('utf-8')
        
        users_data = [
            {'client_id': forte_client.id, 'email': 'john@forte.com', 'name': 'John Smith', 'role': 'admin', 'password_hash': client_password_hash},
            {'client_id': forte_client.id, 'email': 'jane@forte.com', 'name': 'Jane Smith', 'role': 'manager', 'password_hash': client_password_hash},
            {'client_id': servicon_client.id, 'email': 'sarah@servicon.com', 'name': 'Sarah Johnson', 'role': 'admin', 'password_hash': client_password_hash},
            {'client_id': servicon_client.id, 'email': 'tom@servicon.com', 'name': 'Tom Wilson', 'role': 'viewer', 'password_hash': client_password_hash},
            {'client_id': cementech_client.id, 'email': 'mike@cementech.com', 'name': 'Mike Davis', 'role': 'admin', 'password_hash': client_password_hash},
            {'client_id': ppi_client.id, 'email': 'lisa@ppi.com', 'name': 'Lisa Wong', 'role': 'admin', 'password_hash': client_password_hash}
        ]
        
        users = []
        for user_data in users_data:
            user = User(**user_data)
            users.append(user)
        
        db.session.add_all(users)
        db.session.commit()
        
        print("✅ Sample data created successfully!")
        print("\n🔐 Default Login Credentials:")
        print("=================================")
        print("Admin (JupiterBrains):")
        print("  Email: admin@jupiterbrains.com")
        print("  Password: admin123")
        print("  User Type: seller")
        print("\nMarketTrendsAI Admin:")
        print("  Email: admin@marketstrendai.com") 
        print("  Password: admin123")
        print("  User Type: seller")
        print("\nXYZSeller Admin:")
        print("  Email: admin@xyzseller.com")
        print("  Password: admin123")
        print("  User Type: seller")
        print("\nTier2 Seller Admin:")
        print("  Email: admin@datainsightspro.com")
        print("  Password: admin123")
        print("  User Type: tier2_seller")
        print("\nSample Client:")
        print("  Email: john@forte.com")
        print("  Password: client123")
        print("  User Type: client")
        print("=================================")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {str(e)}")
        db.session.rollback()
        return False

def initialize_database():
    """Initialize database with tables and sample data"""
    print("\n🚀 Initializing Database Setup...")
    print("=" * 50)
    
    # Check if database exists
    if check_database_exists():
        print("✅ Database already initialized!")
        return True
    
    # Create tables
    if not create_database_tables():
        return False
    
    # Create sample data
    if not create_sample_data():
        return False
    
    print("\n✅ Database initialization completed successfully!")
    print("🎉 Your Flask application is ready to use!")
    return True
