import os
import sys
import importlib
import inspect
from pathlib import Path
from flask import current_app
from app import db, bcrypt
from flask_migrate import Migrate, init, migrate, upgrade
from sqlalchemy import MetaData, Table, text
from sqlalchemy.exc import OperationalError

def discover_models():
    """Automatically discover all SQLAlchemy models in the models directory"""
    models_discovered = {}
    models_dir = Path(__file__).parent / 'models'
    
    if not models_dir.exists():
        print("Models directory not found!")
        return models_discovered
    
    model_files = [f for f in models_dir.glob('*.py') if f.name != '__init__.py']
    
    print(f"Discovering models in {len(model_files)} files...")
    
    for model_file in model_files:
        module_name = f"app.models.{model_file.stem}"
        
        try:
            module = importlib.import_module(module_name)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (hasattr(obj, '__tablename__') and 
                    hasattr(obj, '__table__') and 
                    hasattr(obj, 'query')):
                    
                    models_discovered[name] = {
                        'class': obj,
                        'table_name': obj.__tablename__,
                        'module': module_name,
                        'file': model_file.name
                    }
                    print(f"  Found model: {name} -> {obj.__tablename__}")
        
        except ImportError as e:
            print(f"  Warning: Could not import {module_name}: {e}")
        except Exception as e:
            print(f"  Error processing {model_file}: {e}")
    
    print(f"Total models discovered: {len(models_discovered)}")
    return models_discovered

def check_database_connection():
    """Check if database connection is working"""
    try:
        db.session.execute(text('SELECT 1'))
        return True
    except Exception as e:
        # Simplified error message for clarity
        print(f"Database connection failed.")
        return False

def get_existing_tables():
    """Get list of existing tables in the database"""
    try:
        from sqlalchemy import inspect as sql_inspect
        inspector = sql_inspect(db.engine)
        return inspector.get_table_names()
    except Exception as e:
        print(f"Error getting existing tables: {e}")
        return []

def check_migrations_folder():
    """Check if migrations folder exists, create if not"""
    migrations_dir = Path('migrations')
    
    if not migrations_dir.exists():
        print("Migrations folder not found. Initializing Flask-Migrate...")
        try:
            init()
            print("Flask-Migrate initialized successfully!")
            return True
        except Exception as e:
            print(f"Error initializing Flask-Migrate: {e}")
            return False
    else:
        # This message is not essential, can be removed for cleaner logs
        # print("Migrations folder found.")
        return True

def initialize_database():
    """Main database initialization function"""
    print("\n🚀 Initializing Database Setup...")
    
    with current_app.app_context():
        if not check_database_connection():
            print("Attempting to create database tables...")
            try:
                db.create_all()
                print("✅ Tables created successfully.")
                # After creating, re-check connection
                if not check_database_connection():
                    print("❌ Database connection failed even after creation. Check DATABASE_URL.")
                    return False
            except Exception as e:
                print(f"❌ Could not create tables. Error: {e}")
                return False
        
        print("✅ Database connection successful")
        
        # Check for missing tables
        models = discover_models()
        existing_tables = get_existing_tables()
        missing_tables_count = 0
        for model_info in models.values():
            if model_info['table_name'] not in existing_tables:
                missing_tables_count += 1
        
        if missing_tables_count > 0:
            print(f"📋 Found {missing_tables_count} missing tables. Recreating all tables to ensure schema is up to date.")
            db.create_all()
        else:
            print("✅ All model tables exist in the database.")

        # Create sample data if the database was empty
        create_sample_data_minimal()

    print("🎉 Database setup complete!")
    return True

def create_sample_data_minimal():
    """Create minimal sample data only if the database is empty."""
    try:
        models = discover_models()
        
        if 'Tier1Seller' in models:
            Tier1Seller = models['Tier1Seller']['class']
            if Tier1Seller.query.first():
                return True
        
        print("Creating minimal sample data...")
        
        if 'Tier1Seller' in models and bcrypt:
            Tier1Seller = models['Tier1Seller']['class']
            password_hash = bcrypt.generate_password_hash('admin123').decode('utf-8')
            
            # This user represents the main admin of the platform
            admin_user = Tier1Seller(
                name='JupiterBrains Admin',
                subdomain='admin',
                admin_email='admin@jupiterbrains.com',
                password_hash=password_hash,
                status='active'
                # REMOVED: role='admin' 
            )
            
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Minimal admin user created.")
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not create sample data. Error: {e}")
        db.session.rollback()
        return False

# Flask CLI commands registration
def register_db_commands(app):
    """Register database commands with Flask CLI"""
    
    @app.cli.command('init_db')
    def init_db_command():
        """Initializes the database with tables and sample data."""
        initialize_database()

    @app.cli.command('reset_db')
    def reset_db_command():
        """Drops all tables and re-initializes the database."""
        print("⚠️  WARNING: This will delete all data!")
        confirm = input("Are you sure you want to reset the database? (yes/no): ")
        if confirm.lower() == 'yes':
            with app.app_context():
                print("Dropping all tables...")
                db.drop_all()
                print("Re-initializing database...")
                initialize_database()
            print("✅ Database has been reset.")
        else:
            print("Database reset cancelled.")

