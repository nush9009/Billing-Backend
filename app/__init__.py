from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_marshmallow import Marshmallow
from flask import send_from_directory, send_file, request
import os
from pathlib import Path


db = SQLAlchemy()
migrate = Migrate()
jwt = JWTManager()
bcrypt = Bcrypt()
ma = Marshmallow()

def create_app():
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.Config')
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    CORS(app)
    bcrypt.init_app(app)
    ma.init_app(app)
    
    # UPDATED: Import the renamed models
    from app.models import Tier1Seller, Tier2Seller, Admin, Project, Client
    
    # Initialize database automatically on first run
    with app.app_context():
        from app.database_setup import initialize_database, register_db_commands
        
        # Register CLI commands
        register_db_commands(app)
        
        # Auto-initialize database on startup
        initialize_database()
    
    
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.seller import seller_bp
    from app.routes.admin import admin_bp
    from app.routes.projects import projects_bp
    from app.routes.billing import billing_bp

    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(seller_bp, url_prefix='/api/seller')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(billing_bp, url_prefix='/api/billing')
    
    
    react_build_path = Path("dist")  # or Path("frontend/dist") if in subdirectory
    print(react_build_path)
    if react_build_path.exists():
        print("✅ React build found! Serving frontend...")
        
        # Serve static assets (CSS, JS files)
        @app.route('/assets/<path:filename>')
        def serve_assets(filename):
            return send_from_directory(react_build_path / 'assets', filename)
        
        # Serve manifest.json
        @app.route('/manifest.json')
        def serve_manifest():
            return send_file(react_build_path / 'manifest.json')
        
        # Serve favicon
        @app.route('/favicon.ico')
        def serve_favicon():
            return send_file(react_build_path / 'favicon.ico')
        
        # Serve React app for all non-API routes
        @app.route('/')
        @app.route('/<path:path>')
        def serve_react_app(path=''):
            # Don't serve React for API routes
            if path.startswith('api/'):
                return {"error": "API endpoint not found"}, 404
            return send_file(react_build_path / 'index.html')
    
    else:
        print("⚠️  React build folder not found. Please run 'npm run build' first.")
        
        @app.route('/')
        def no_react_build():
            return {
                "message": "React app not built. Run 'npm run build' first, then restart the server.",
                "instructions": [
                    "1. cd to your React project directory",
                    "2. Run: npm run build",
                    "3. Copy the 'dist' folder to your Flask project root",
                    "4. Restart Flask server"
                ]
            }
    
    # ADD THESE ENDPOINTS:
    
    @app.route('/api/health')
    def health_check():
        return {
            'status': 'healthy',
            'message': 'Flask SaaS API is running!',
            'version': '1.0.0',
            'port': 5021
        }, 200
    
    @app.route('/api/db-info')
    def db_info():
        try:
            # UPDATED: Use the new model names
            from app.models import Tier1Seller, Tier2Seller, Admin, Project, User, Commission
            
            tier1_seller_count = Tier1Seller.query.count()
            tier2_seller_count = Tier2Seller.query.count()
            admin_count = Admin.query.count()
            project_count = Project.query.count()
            user_count = User.query.count()
            commission_count = Commission.query.count()
            
            return {
                'database_status': 'connected',
                'stats': {
                    'tier1_sellers': tier1_seller_count,
                    'tier2_sellers': tier2_seller_count,
                    'admins': admin_count,
                    'projects': project_count,
                    'users': user_count,
                    'commissions': commission_count
                },
                'sample_data': {
                    'sellers_available': tier1_seller_count > 0,
                    'admins_available': admin_count > 0,
                    'projects_available': project_count > 0
                }
            }, 200
        except Exception as e:
            return {
                'database_status': 'error',
                'message': str(e),
                'stats': None
            }, 500
    
    @app.route('/api/status')
    def app_status():
        """Complete application status"""
        try:
            # UPDATED: Check against the new Tier1Seller model
            from app.models import Tier1Seller
            Tier1Seller.query.first()
            db_status = 'connected'
        except Exception as e:
            db_status = f'error: {str(e)}'
        
        return {
            'application': 'Flask SaaS Platform',
            'version': '1.0.0',
            'status': 'running',
            'database': db_status,
            'environment': os.getenv('FLASK_ENV', 'development'),
            'endpoints': {
                'health': '/api/health',
                'database_info': '/api/db-info',
                'auth': '/api/auth/login',
                'seller_dashboard': '/api/seller/dashboard',
                'client_dashboard': '/api/client/dashboard',
                'admin_dashboard': '/api/admin/dashboard'
            }
        }, 200
    
    @app.route('/api/sample-logins')
    def sample_logins():
        """Show available sample login accounts"""
        # Note: This is just for display, but updated for clarity
        return {
            'message': 'Available sample login accounts',
            'accounts': {
                'admin_accounts': [
                    {
                        'role': 'Root Admin',
                        'email': 'admin@jupiterbrains.com',
                        'password': 'admin123',
                        'user_type': 'seller',
                        'description': 'JupiterBrains system administrator'
                    },
                    {
                        'role': 'Tier-1 Seller',
                        'email': 'admin@marketstrendai.com',
                        'password': 'admin123',
                        'user_type': 'seller',
                        'description': 'MarketTrendsAI admin'
                    },
                    {
                        'role': 'Tier-2 Seller',
                        'email': 'admin@datainsightspro.com',
                        'password': 'admin123',
                        'user_type': 'tier2_seller',
                        'description': 'DataInsights Pro admin'
                    }
                ],
                'client_accounts': [
                    {
                        'role': 'Admin User (formerly Client)',
                        'email': 'john@forte.com',
                        'password': 'client123',
                        'user_type': 'client',
                        'company': 'Forte Corp'
                    }
                ]
            },
            'usage': 'Use these credentials with POST /api/auth/login'
        }, 200
    
    @app.errorhandler(404)
    def not_found(error):
        """Custom 404 handler"""
        return {
            'error': 'API endpoint not found',
            'message': f'The endpoint {request.path} does not exist.',
            'available_endpoints': [
                '/api/health',
                '/api/db-info',
                '/api/status',
                '/api/sample-logins'
            ]
        }, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        """Custom 500 handler"""
        return {
            'error': 'Internal server error',
            'message': 'Something went wrong on the server.',
            'suggestion': 'Check server logs for details.'
        }, 500
    
    return app

