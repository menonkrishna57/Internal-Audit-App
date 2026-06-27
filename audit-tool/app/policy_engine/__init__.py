"""
Policy Engine — PDF ingestion pipeline that extracts compliance policy clauses,
stores them in Qdrant for semantic search, and auto-generates or updates audit
YAML rules from those clauses using the Gemini AI API.
"""
