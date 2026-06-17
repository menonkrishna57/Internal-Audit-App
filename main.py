# app/main.py
import os
from fastapi import FastAPI, HTTPException
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Bank Operational Audit Tool - PoC")

# Safely catch environment variables passed by Docker/Azure
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing critical Supabase configuration environment variables.")

# Initialize the Supabase Client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/health")
def health_check():
    """Confirms the API engine is alive."""
    return {"status": "healthy", "environment": "active"}

@app.get("/test-db")
def test_database_connection():
    """Quick verification to ensure Supabase credentials are valid."""
    try:
        # Pull just one row from employees to verify connectivity
        response = supabase.postgrest.schema("hr_schema").table("employees").select("id").limit(1).execute()
        return {"status": "connected", "data_verified": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")