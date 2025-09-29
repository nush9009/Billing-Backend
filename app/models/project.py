from app import db
from datetime import datetime
import uuid

# class Project(db.Model):
#     __tablename__ = 'projects'
    
#     id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
#     name = db.Column(db.String(255), nullable=False)
#     status = db.Column(db.String(20), default='active')
#     project_type = db.Column(db.String(100))
#     description = db.Column(db.Text)
#     start_date = db.Column(db.Date)
#     end_date = db.Column(db.Date)
#     billing_frequency = db.Column(db.String(20), default='milestone')
#     hourly_budget = db.Column(db.Numeric(8, 2))
#     hours_used = db.Column(db.Numeric(8, 2), default=0)
#     budget_spent = db.Column(db.Numeric(12, 2), default=0)
#     admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True) 
#     tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'), nullable=True)
#     tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'), nullable=True)
#     subscription_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'), nullable=True)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     # Relationships
#     clients = db.relationship('Client', backref='project', lazy=True)



# class Client(db.Model):
#     __tablename__ = 'clients'
    
#     id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
#     project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
#     admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True)
#     name = db.Column(db.String(255), nullable=False)
#     company = db.Column(db.String(255))  # optional
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



# class SubscriptionPlan(db.Model):
#     __tablename__ = 'subscription_plans'

#     id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
#     name = db.Column(db.String(100), nullable=False)
#     description = db.Column(db.Text)
#     price = db.Column(db.Numeric(12, 2), nullable=False)

#     # Who created the plan? (Admin OR Tier1)
#     created_by_admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True)
#     created_by_tier1_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'), nullable=True)

#     # Commission rules
#     admin_commission_pct = db.Column(db.Numeric(5, 2), nullable=True)   # % Admin earns
#     tier1_commission_pct = db.Column(db.Numeric(5, 2), nullable=True)   # % Tier1 earns from Tier2

#     billing_cycle = db.Column(db.String(20), default='monthly') 
#     status = db.Column(db.String(20), default='active')

#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     # Relationships
#     projects = db.relationship('Project', backref='subscription_plan', lazy=True)
#     admin = db.relationship('Admin', backref='subscription_plans')
#     tier1_seller = db.relationship('Tier1Seller', backref='subscription_plans')


# class Commission(db.Model):
#     __tablename__ = 'commissions'

#     id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

#     subscription_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'), nullable=False)
#     tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'), nullable=True)  
#     tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'), nullable=True)  
#     admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True)

#     # Commission percentages
#     tier1_commission_pct = db.Column(db.Numeric(5, 2), nullable=True)   # Tier1 takes from Tier2
#     admin_commission_pct = db.Column(db.Numeric(5, 2), nullable=True)  # Admin always takes
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

#     # Relationships
#     subscription_plan = db.relationship('SubscriptionPlan', backref='commissions')
#     tier1_seller = db.relationship('Tier1Seller', backref='commissions')
#     tier2_seller = db.relationship('Tier2Seller', backref='commissions')
#     admin = db.relationship('Admin', backref='commissions')

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
    billing_frequency = db.Column(db.String(20), default='milestone')
    hourly_budget = db.Column(db.Numeric(8, 2))
    hours_used = db.Column(db.Numeric(8, 2), default=0)
    budget_spent = db.Column(db.Numeric(12, 2), default=0)
    admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True) 
    tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'), nullable=True)
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'), nullable=True)
    subscription_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    clients = db.relationship('Client', backref='project', lazy=True)
    subscription_plan = db.relationship('SubscriptionPlan', backref='projects')



class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = db.Column(db.String(36), db.ForeignKey('projects.id'), nullable=False)
    admin_id = db.Column(db.String(36), db.ForeignKey('admins.id'), nullable=True)
    name = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255))  # optional
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)



class SubscriptionPlan(db.Model):
    __tablename__ = 'subscription_plans'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    billing_cycle = db.Column(db.String(20), default='monthly') 
    status = db.Column(db.String(20), default='active')

    # Who created the plan? (Admin OR Tier1)
    creator_id = db.Column(db.String(36), nullable=False)
    creator_type = db.Column(db.String(50), nullable=False) # 'admin' or 'tier1_seller'
    
    # Parent plan for white-labeling
    parent_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'), nullable=True)

    # Commission rules
    admin_commission_pct = db.Column(db.Numeric(5, 2), nullable=True)   # % Admin earns
    tier1_commission_pct = db.Column(db.Numeric(5, 2), nullable=True)   # % Tier1 earns from Tier2

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent_plan = db.relationship('SubscriptionPlan', remote_side=[id], backref='child_plans')

class Tier1Subscription(db.Model):
    __tablename__ = 'tier1_subscriptions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tier1_seller_id = db.Column(db.String(36), db.ForeignKey('tier1_sellers.id'), nullable=False)
    subscription_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'), nullable=False)
    
    status = db.Column(db.String(20), default='active', nullable=False) # 'active', 'cancelled', 'expired'
    
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    # Relationships
    tier1_seller = db.relationship('Tier1Seller', backref='subscriptions')
    subscription_plan = db.relationship('SubscriptionPlan', backref='tier1_subscriptions')

class Tier2Subscription(db.Model):
    __tablename__ = 'tier2_subscriptions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tier2_seller_id = db.Column(db.String(36), db.ForeignKey('tier2_sellers.id'), nullable=False)
    subscription_plan_id = db.Column(db.String(36), db.ForeignKey('subscription_plans.id'), nullable=False)
    
    status = db.Column(db.String(20), default='active', nullable=False) # 'active', 'cancelled', 'expired'
    
    subscribed_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)

    # Relationships
    tier2_seller = db.relationship('Tier2Seller', backref='subscriptions')
    subscription_plan = db.relationship('SubscriptionPlan', backref='tier2_subscriptions')