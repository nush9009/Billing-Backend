# Updated run.py - Enhanced with better error handling
from app import create_app
from flask import Flask
import os
from pathlib import Path

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['DATABASE_URL', 'JWT_SECRET_KEY']
    missing_vars = []
    
    for var in required_vars:
        # if not os.getenv(var):
        #     missing_vars.append(var)
        pass
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(f"   - {var}")
        print("\nPlease create a .env file with the required variables.")
        print("Example .env file:")
        print("DATABASE_URL=postgresql://saas_user:password@localhost:5432/saas_platform")
        print("JWT_SECRET_KEY=your-super-secret-jwt-key")
        return False
    
    return True

def setup_react_integration(app):
    """Setup React frontend integration"""
    react_build_path = Path("dist")
    
    if react_build_path.exists():
        print("🌐 React frontend available at http://localhost:5021")
        print("📱 API endpoints available at http://localhost:5021/api/*")
        return True
    else:
        print("⚠️  React build not found!")
        print("📋 To integrate your React frontend:")
        print("  1. Build your React app: npm run build")
        print("  2. Copy the 'dist' folder to your Flask project root")
        print("  3. Restart this Flask server")
        print("  4. Your React app will be available at http://localhost:5021")
        return False

if __name__ == '__main__':
    print("🚀 Starting Flask SaaS Application with React Integration...")
    
    # Create Flask app
    app = create_app()
    
    # Check React integration
    react_available = setup_react_integration(app)
    
    if react_available:
        print("🎉 Full-stack application ready!")
        print("   Frontend: http://localhost:5021")
        print("   API: http://localhost:5021/api")
    else:
        print("🔧 API-only mode")
        print("   API: http://localhost:5021/api")
    
    app.run(host='0.0.0.0', port=5021, debug=True)