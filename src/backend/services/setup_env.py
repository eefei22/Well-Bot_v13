"""
Environment setup script for Well-Bot database integration.
Creates .env file with Supabase credentials.
"""

import os
from pathlib import Path

def create_env_file():
    """Create .env file with Supabase credentials."""
    
    # Get the project root directory (3 levels up from this file)
    project_root = Path(__file__).parent.parent.parent.parent
    
    env_file_path = project_root / ".env"
    
    # Supabase credentials
    env_content = """# Supabase Configuration
SUPABASE_URL=https://otymmdatyozfljzsqrhy.supabase.co
SUPABASE_ANON_KEY=sb_publishable_T3WPHIBl_b_-WTPWjZiG-g_S2K5Esjv
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Im90eW1tZGF0eW96ZmxqenNxcmh5Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1NTE0NDkxOSwiZXhwIjoyMDcwNzIwOTE5fQ.CDnJ-pLc2xet3bqJg__Wwhs90B_FyN3nFlCT5nS0yPY

# FastMCP Configuration
FASTMCP_HOST=0.0.0.0
FASTMCP_PORT=8000
FASTMCP_AUTH_MODE=supabase
FASTMCP_AUTH_KEY=dev-secret
"""
    
    try:
        with open(env_file_path, 'w') as f:
            f.write(env_content)
        
        print(f"[OK] Created .env file at: {env_file_path}")
        print("Environment variables set:")
        print("   - SUPABASE_URL")
        print("   - SUPABASE_ANON_KEY") 
        print("   - SUPABASE_SERVICE_ROLE_KEY")
        print("   - FastMCP configuration")
        
        return True
        
    except Exception as e:
        print(f"[ERROR] Failed to create .env file: {str(e)}")
        return False

def check_env_vars():
    """Check if environment variables are properly set."""
    required_vars = [
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY"
    ]
    
    print("Checking environment variables...")
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            if "KEY" in var:
                masked_value = value[:10] + "..." + value[-10:] if len(value) > 20 else "***"
                print(f"[OK] {var}: {masked_value}")
            else:
                print(f"[OK] {var}: {value}")
        else:
            missing_vars.append(var)
            print(f"[ERROR] {var}: Not set")
    
    if missing_vars:
        print(f"\nMissing variables: {', '.join(missing_vars)}")
        print("Run this script to create .env file with credentials")
        return False
    else:
        print("\n[OK] All required environment variables are set!")
        return True

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Setup Well-Bot environment variables")
    parser.add_argument("--check", action="store_true", help="Check existing environment variables")
    args = parser.parse_args()
    
    if args.check:
        success = check_env_vars()
    else:
        print("Setting up Well-Bot environment...")
        success = create_env_file()
        
        if success:
            print("\nVerifying setup...")
            success = check_env_vars()
    
    if success:
        print("\n[SUCCESS] Environment setup complete!")
    else:
        print("\n[ERROR] Environment setup failed!")
        exit(1)
