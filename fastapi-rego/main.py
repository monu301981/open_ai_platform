from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import re
import os
import requests
from opa_client.opa import OpaClient
from fastapi.responses import JSONResponse
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from urllib.parse import urlparse, urljoin
import logging
from rego_service import RegoService

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = FastAPI(title="AI Chat API for Rego Policy Evaluation")

# Pydantic model for chat query
class ChatQuery(BaseModel):
    query: str

# OPA server configuration
OPA_HOST = "http://localhost:8181"

rego_service = RegoService(OPA_HOST)

# Parse chat query to extract product and parameters
def parse_query(query: str) -> tuple[str, dict]:
    # Expected format: "Check access for product <product> with <key1> <value1>, <key2> <value2>, ..."
    pattern = r"Check access for product\s+([a-zA-Z0-9]+)\s+with\s+(.+)"
    match = re.match(pattern, query, re.IGNORECASE)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid query format. Use: 'Check access for product <product> with <key1> <value1>, <key2> <value2>, ...'")
    product = match.group(1)
    attrs_str = match.group(2)
    # Parse key-value pairs
    input_data = {}
    for pair in attrs_str.split(','):
        if ':' in pair:
            key, value = pair.split(':', 1)
        else:
            parts = pair.strip().split()
            if len(parts) >= 2:
                key = parts[0].strip()
                value = ' '.join(parts[1:]).strip()
            else:
                continue
        input_data[key.strip()] = value.strip()
    return product, input_data

@app.on_event("startup")
async def startup_event():
    # Ensure policies and data directories exist
    os.makedirs("policies", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    
    # Check OPA server availability
    try:
        rego_service.check_opa_health()
    except requests.RequestException:
        raise HTTPException(status_code=500, detail=f"OPA server not available at {OPA_HOST}. Please ensure OPA is running (e.g., 'opa run --server').")

@app.post("/chat")
async def chat_query(query: ChatQuery):
    try:
        # Parse user query to get product and input data
        product, input_data = parse_query(query.query)
        
        # Load data file
        data = rego_service.load_data_file(product)
        
        # Load and upload policy to OPA
        policy_content = rego_service.load_policy_file(product)
        rego_service.upload_policy_to_opa(product, policy_content)
        
        # Combine user input with data file (user input takes precedence)
        combined_input = {**data, **input_data}
        
        # Evaluate policy using RegoService
        result = rego_service.evaluate_policy(product, combined_input)
        
        # Prepare response
        response = {
            "query": query.query,
            "product": product,
            "input": combined_input,
            "allowed": result,
            "message": "Access granted" if result else "Access denied"
        }
        return JSONResponse(content=response)
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/")
async def root():
    return {"message": "AI Chat API for Rego Policy Evaluation"}