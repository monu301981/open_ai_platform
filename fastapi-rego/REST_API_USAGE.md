# REST API Usage Guide

This document describes how to use the FastAPI-based AI Chat API for evaluating Rego policies with Open Policy Agent (OPA). The API dynamically loads Rego policy and data files based on the product name specified in the query.

## Base URL
`http://localhost:8000`

## Endpoints

### 1. Root Endpoint
- **Method**: GET
- **Path**: `/`
- **Description**: Returns a welcome message.
- **Response**:
  ```json
  {
    "message": "AI Chat API for Rego Policy Evaluation"
  }
  ```

### 2. Chat Query Endpoint
- **Method**: POST
- **Path**: `/chat`
- **Description**: Evaluates a chat-like query against the Rego policy (`policies/<product>.rego`) and data (`data/<product>.json`) for the specified product.
- **Request Body**:
  ```json
  {
    "query": "Check access for product <product> with <key1> <value1>, <key2> <value2>, ..."
  }
  ```
  Example:
  ```json
  {
    "query": "Check access for product mediacomposer with region us, usage 1 TB, license Avid Platinum"
  }
  ```
  Flexible example:
  ```json
  {
    "query": "Check access for product mediacomposer with region us, custom_attr value"
  }
  ```
- **Response**:
  ```json
  {
    "query": "string",
    "product": "string",
    "input": {
      "key1": "value1",
      "key2": "value2"
    },
    "allowed": boolean,
    "message": "string"
  }
  ```
  Example (successful):
  ```json
  {
    "query": "Check access for product mediacomposer with region us, usage 1 TB, license Avid Platinum",
    "product": "mediacomposer",
    "input": {
      "region": "us",
      "usage": "1 TB",
      "License": "Avid Platinum"
    },
    "allowed": true,
    "message": "Access granted"
  }
  ```
  Example (denied):
  ```json
  {
    "query": "Check access for product mediacomposer with region eu, usage 1 TB, license Avid Platinum",
    "product": "mediacomposer",
    "input": {
      "region": "eu",
      "usage": "1 TB",
      "License": "Avid Platinum"
    },
    "allowed": false,
    "message": "Access denied"
  }
  ```

## Query Format
- The query must follow the format: `Check access for product <product> with <key1> <value1>, <key2> <value2>, ...`.
- The `<product>` specifies the Rego policy (`policies/<product>.rego`) and data file (`data/<product>.json`).
- Any key-value pairs can be provided; they are parsed dynamically and combined with the product's JSON data (user input takes precedence).
- The policy allows access if the conditions in `<product>.rego` are met (e.g., for `mediacomposer.rego`, `region` is "us", `usage` is "1 TB", `License` is "Avid Platinum").

## Example Requests

### Using `curl`
```bash
curl -X POST "http://localhost:8000/chat" \
-H "Content-Type: application/json" \
-d '{"query": "Check access for product mediacomposer with region us, usage 1 TB, license Avid Platinum"}'
```

### Using Python `requests`
```python
import requests

url = "http://localhost:8000/chat"
payload = {"query": "Check access for product mediacomposer with region us, usage 1 TB, license Avid Platinum"}
response = requests.post(url, json=payload)
print(response.json())
```

## Error Responses
- **400 Bad Request**: Invalid query format.
  ```json
  {
    "detail": "Invalid query format. Use: 'Check access for product <product> with <key1> <value1>, <key2> <value2>, ...'"
  }
  ```
- **500 Internal Server Error**: Issues with file loading, policy upload, or OPA evaluation.
  ```json
  {
    "detail": "Data file data/<product>.json not found"
  }
  ```
  or
  ```json
  {
    "detail": "Policy file policies/<product>.rego not found"
  }
  ```
  or
  ```json
  {
    "detail": "Failed to upload policy to OPA: <error message>. Ensure OPA server is running on http://localhost:8181."
  }
  ```

## Notes
- Ensure the OPA server is running at `http://localhost:8181`.
- Place `<product>.rego` files in the `policies/` directory and `<product>.json` files in the `data/` directory.
- The API assumes the query parameters match the structure expected by the product's Rego policy.
- The query parser supports flexible attributes; values with spaces are handled as part of the value.