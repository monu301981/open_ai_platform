import requests
from urllib.parse import urljoin
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type
from fastapi import HTTPException
import logging
import json
import os

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class RegoService:
    def __init__(self, opa_host: str):
        self.opa_host = self.validate_opa_host(opa_host)
        self.opa_client = self.init_opa_client()

    def validate_opa_host(self, host: str):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(host)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("Invalid OPA_HOST format")
            return host.rstrip("/")
        except ValueValue as e:
            logger.error(f"Invalid OPA_HOST configuration: {host}. Error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Invalid OPA_HOST configuration: {host}. Must be a valid URL (e.g., http://localhost:8181)")

    def init_opa_client(self):
        from opa_client.opa import OpaClient
        return OpaClient(host=self.opa_host)

    def check_opa_health(self):
        health_url = urljoin(self.opa_host, "/health")
        logger.debug(f"Checking OPA server health at {health_url}")
        response = requests.get(health_url)
        response.raise_for_status()

    def load_data_file(self, product: str):
        data_file = f"data/{product}.json"
        try:
            with open(data_file, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail=f"Data file {data_file} not found")
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Invalid JSON in {data_file}")

    def load_policy_file(self, product: str):
        policy_file = f"policies/{product}.rego"
        try:
            with open(policy_file, "r") as f:
                return f.read()
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail=f"Policy file {policy_file} not found")

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(2), retry=retry_if_exception_type(requests.RequestException))
    def upload_policy_to_opa(self, product: str, policy_content: str):
        opa_url = urljoin(self.opa_host, f"/v1/policies/{product}")
        logger.debug(f"Uploading policy to OPA at {opa_url}")
        response = requests.put(opa_url, data=policy_content.encode('utf-8'))
        response.raise_for_status()

    def evaluate_policy(self, product: str, combined_input: dict):
        try:
            logger.debug(f"Evaluating policy for {product} with input: {combined_input}")
            result = self.opa_client.check_permission(combined_input, product, "allow")
            logger.debug(f"Policy evaluation result for {product}: {result}")
            return result
        except Exception as e:
            logger.error(f"OpaClient.check_permission failed: {str(e)}. Falling back to direct HTTP request.")
            # Fallback to direct HTTP request
            eval_url = urljoin(self.opa_host, f"/v1/data/policies/{product}/l4/allow")
            logger.debug(f"Evaluating policy via HTTP at {eval_url}")
            response = requests.post(
                eval_url,
                json={"input": combined_input},
                headers={"Content-Type": "application/json"}
            )
            response.raise_for_status()
            return response.json().get("result", False)