# AI Chat API for Rego Policy Evaluation

This project is a FastAPI-based REST API that allows users to query Rego policies (using Open Policy Agent, OPA) with a chat-like interface. It dynamically loads Rego policy and data files based on the product name specified in the query (e.g., `policies/<product>.rego` and `data/<product>.json`) and evaluates access permissions.

## Features
- Accepts chat-like queries (e.g., "Check access for product mediacomposer with region us, usage 1 TB, license Avid Platinum").
- Dynamically loads `<product>.rego` and `<product>.json` based on the product name.
- Supports flexible attribute querying (any key-value pairs in the query).
- Uploads policies to OPA via the `/v1/policies` endpoint with retry logic.
- Evaluates queries against the specified Rego policy using OPA.
- Combines user input with data from the product's JSON file.
- Returns whether access is allowed based on the policy.
- Separate service for Rego handling (`rego_service.py`).

## Prerequisites
- Python 3.8+
- OPA server running locally (`http://localhost:8181`)
- Required Python packages: `fastapi`, `uvicorn`, `opa-python-client`, `pydantic`, `requests`, `tenacity`

## Setup Instructions

1. **Clone the Repository** (or create the project structure):
   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. **Install Dependencies**:
   Install all required Python packages:
   ```bash
   pip install fastapi uvicorn opa-python-client pydantic requests tenacity
   ```
   Ensure `tenacity` is installed for retry logic and the latest `opa-python-client` for OPA interactions:
   ```bash
   pip install --upgrade opa-python-client
   ```

3. **Start the OPA Server**:
   Ensure OPA is installed ([OPA Installation Guide](https://www.openpolicyagent.org/docs/latest/#running-opa)).
   Run OPA in server mode:
   ```bash
   opa run --server
   ```

4. **Prepare Files**:
   - Place Rego policy files (e.g., `mediacomposer.rego`) in the `policies/` directory.
   - Place corresponding data files (e.g., `mediacomposer.json`) in the `data/` directory.
   - Example files (`mediacomposer.rego` and `mediacomposer.json`) should follow the structure of the provided `test1.rego` and `test1.json`.

5. **Run the FastAPI Application**:
   ```bash
   uvicorn main:app --reload
   ```
   The API will be available at `http://localhost:8000`.

## Project Structure
```
├── main.py           # FastAPI application code
├── rego_service.py  # Separate service for Rego/OPA handling
├── policies/        # Directory for Rego policy files (<product>.rego)
├── data/           # Directory for data files (<product>.json)
├── README.md       # Project overview (this file)
└── REST_API_USAGE.md # API usage documentation
```

## Usage
- Send a POST request to `/chat` with a JSON payload containing a query specifying the product name.
- Example query: `{"query": "Check access for product mediacomposer with region us, usage 1 TB, license Avid Platinum"}`
- Flexible attributes: You can include any key-value pairs, e.g., "Check access for product mediacomposer with region us, custom_attr value".
- See `REST_API_USAGE.md` for detailed API usage instructions.

## Troubleshooting
- **ModuleNotFoundError: No module named 'tenacity'**:
  - Install the `tenacity` package:
    ```bash
    pip install tenacity
    ```
  - Verify installation:
    ```bash
    pip list | grep tenacity
    ```
- **OPA Connection Error**:
  - If you see an error like `Failed to upload policy to OPA: ... No connection could be made ...` or `NameResolutionError: Failed to resolve 'http'`, ensure the OPA server is running:
    ```bash
    opa run --server
    ```
  - Verify OPA is accessible by checking `http://localhost:8181/health` in a browser or with `curl`:
    ```bash
    curl http://localhost:8181/health
    ```
  - Ensure `OPA_HOST` in `main.py` is set to `http://localhost:8181` and does not include invalid characters or formats.
  - If the error shows an invalid URL like `http://http:80/localhost:8181:8181/...`, verify that `OPA_HOST` is correctly set and the `opa-python-client` library is up-to-date:
    ```bash
    pip install --upgrade opa-python-client
    ```
  - If OPA is running on a different port or host, update the `OPA_HOST` variable in `main.py` (e.g., `OPA_HOST = "http://localhost:8182"`).
  - On Windows, check for firewall restrictions blocking port 8181:
    - Open Windows Defender Firewall -> Advanced Settings -> Inbound Rules -> New Rule.
    - Select "Port", TCP, port 8181, and allow the connection.
    - Alternatively, temporarily disable the firewall for testing:
      ```bash
      netsh advfirewall set allprofiles state off
      ```
- **OpaClient.check_permission Errors**:
  - If you see errors like `OpaClient.check_permission() got an unexpected keyword argument 'input_dict'`, `'package_path'`, `'policy_path'`, or `missing 1 required positional argument: 'rule_name'`, ensure you have the latest version of `opa-python-client`:
    ```bash
    pip install --upgrade opa-python-client
    ```
  - The code uses `input_data`, `policy_name`, and `rule_name` as positional arguments for compatibility with recent versions of the library.
  - If issues persist, check the console logs for debug information about the `check_permission` call or fallback HTTP request.
- **Missing Files**:
  - Ensure `<product>.rego` and `<product>.json` files exist in the `policies/` and `data/` directories, respectively.

## License
MIT License