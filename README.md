# Currency Converter API (FastMCP)

## Description
The Currency Converter API is a lightweight and efficient service built using FastMCP. It allows users to convert amounts between different currencies using the ExchangeRate-API. The project is designed to be simple, fast, and easy to integrate into other applications.

## Features
- Convert amounts between any two supported currencies.
- Handles API key management via headers or environment variables.
- Provides detailed error messages for unsupported currencies, invalid API keys, and more.
- Asynchronous API calls for better performance.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/currency-converter-api.git
   ```

2. Navigate to the project directory:
   ```bash
   cd currency-converter-api
   ```

3. Install dependencies:
   ```bash
    uv add -r requirements.txt
   ```

4. Create a `.env` file in the root directory and add your ExchangeRate-API key using:
   ```sh
   cp env.example .env
   ```

## Usage

1. Start the server:
   ```bash
   uv run main.py
   ```

2. Access the API at `http://localhost:8000`.

3. Add the MCP server information in the mcp.json in <strong>VSCode</strong>

- ctrl + shift + p > MCP: Open User Configuration
- add the following lines:

```json
{
    "servers": {
        "exchange-rate-mcp": {
			"url": "http://localhost:8000/mcp",
			"type": "http"
		}
    }
}
```


## API Endpoints

### `GET /mcp`
- **Description**: Returns the list of available tools.

### `POST /mcp/convert_currency`
- **Description**: Converts an amount from one currency to another.
- **Request Body**:
  ```json
  {
    "amount": 1,
    "from_currency": "USD",
    "to_currency": "NPR"
  }
  ```
- **Response**:
  ```json
  {
    "success": true,
    "from": "USD",
    "to": "NPR",
    "amount": 1,
    "conversion_rate": 143.6115,
    "converted_amount": 143.6115,
    "last_update": "Tue, 23 Dec 2025 00:00:01 +0000",
    "message": "1.0 USD = 143.61 NPR"
  }
  ```

## Environment Variables
The following environment variables are required:
- `EXCHANGE_API_KEY`: Your API key for ExchangeRate-API.

## Dependencies
- `fastmcp`
- `httpx`
- `python-dotenv`
