import os
import uvicorn
from fastmcp import FastMCP
import httpx
from dotenv import load_dotenv
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Currency Converter")

# Authentication Middleware for MCP Connection (optional based on env)
class MCPAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Get the MCP authentication token from headers
        mcp_auth_token = request.headers.get("mcp-authentication")
        
        # Get expected token from environment
        expected_token = os.getenv("MCP_AUTH_TOKEN")
        
        # This should never happen if middleware is conditionally added,
        # but kept for safety
        if not expected_token:
            # If no token configured, allow request to proceed
            response = await call_next(request)
            return response
        
        # Validate MCP authentication
        if not mcp_auth_token:
            return JSONResponse(
                {"error": "Unauthorized: MCP-Auth header required"},
                status_code=401
            )
        
        if mcp_auth_token != expected_token:
            return JSONResponse(
                {"error": "Unauthorized: Invalid MCP authentication token"},
                status_code=403
            )
        
        # If authentication passes, continue
        response = await call_next(request)
        return response


# Get API key from environment or headers
def get_api_key(context) -> str:
    """Extract API key from request headers or environment."""
    try:
        # Try to get from headers first (from mcp.json configuration)
        api_key = (
            context.request_context.headers.get("apikey")
            if hasattr(context, "request_context")
            and hasattr(context.request_context, "headers")
            else None
        )

        # Fallback to environment variable
        if not api_key:
            api_key = os.getenv("EXCHANGE_API_KEY")

        if not api_key:
            raise ValueError(
                "API key not found. Please set EXCHANGE_API_KEY in .env file"
            )

        return api_key
    except AttributeError as e:
        raise ValueError(f"Invalid context object: {e}")


# @mcp.tool()
# async def convert_currency(
#     amount: float, from_currency: str, to_currency: str, context
# ) -> dict:
#     """
#     Convert an amount from one currency to another using ExchangeRate-API.

#     Args:
#         amount: The amount to convert (e.g., 100.50)
#         from_currency: Source currency code (e.g., USD, EUR, GBP)
#         to_currency: Target currency code (e.g., USD, EUR, GBP)

#     Returns:
#         Dictionary with conversion details including rate and result
#     """
#     try:
#         # Get API key
#         api_key = get_api_key(context)
#         # Validate inputs
#         from_currency = from_currency.upper().strip()
#         to_currency = to_currency.upper().strip()

#         if amount <= 0:
#             return {"error": "Amount must be greater than 0", "success": False}

#         # Build API URL
#         url = f"https://v6.exchangerate-api.com/v6/{api_key}/pair/{from_currency}/{to_currency}/{amount}"

#         # Make API request
#         async with httpx.AsyncClient() as client:
#             response = await client.get(url, timeout=10.0)
#             data = response.json()
#             print(f"API Response: {data}")

#         # Check for errors
#         if data.get("result") == "error":
#             error_type = data.get("error-type", "unknown")
#             error_messages = {
#                 "unsupported-code": f"Currency code not supported. Please check {from_currency} and {to_currency}.",
#                 "malformed-request": "Request format is invalid.",
#                 "invalid-key": "API key is invalid.",
#                 "inactive-account": "Account is inactive. Please confirm your email.",
#                 "quota-reached": "API quota has been reached.",
#             }
#             return {
#                 "error": error_messages.get(error_type, f"Error: {error_type}"),
#                 "success": False,
#             }

#         # Return successful conversion
#         return {
#             "success": True,
#             "from": from_currency,
#             "to": to_currency,
#             "amount": amount,
#             "conversion_rate": data.get("conversion_rate"),
#             "converted_amount": data.get("conversion_result"),
#             "last_update": data.get("time_last_update_utc"),
#             "message": f"{amount} {from_currency} = {data.get('conversion_result'):.2f} {to_currency}",
#         }

#     except ValueError as e:
#         return {"error": str(e), "success": False}
#     except httpx.TimeoutException:
#         return {"error": "Request timed out. Please try again.", "success": False}
#     except Exception as e:
#         return {"error": f"Unexpected error: {str(e)}", "success": False}


@mcp.tool()
async def get_bullion_prices() -> dict:
    """
    Get current gold and silver prices in NPR currency.

    Returns:
        Dictionary with fine gold and silver prices in specified unit and NPR currency, along with date
    """
    try:
        url = os.getenv("BULLION_URL")

        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        # Return formatted response
        return {
            "success": True,
            "fine_gold": data.get("fine_gold"),
            "silver": data.get("silver"),
            "unit": data.get("unit"),
            "date": data.get("date"),
            "message": f"Fine Gold: {data.get('fine_gold')} per {data.get('unit')}, Silver: {data.get('silver')} per {data.get('unit')} (as of {data.get('date')})",
        }

    except httpx.TimeoutException:
        return {"error": "Request timed out. Please try again.", "success": False}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error occurred: {e.response.status_code}", "success": False}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "success": False}


@mcp.tool()
async def get_forex_rates(currency: str = None) -> dict:
    """
    Get current forex exchange rates for various currencies in NPR.

    Args:
        currency: Optional currency code to filter (e.g., USD, EUR, GBP). If not provided, returns all rates.

    Returns:
        Dictionary with forex rates including buy and sell prices, or filtered rate for specific currency
    """
    try:
        url = os.getenv("FOREX_URL")

        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        # If currency is specified, filter for that currency
        if currency:
            currency_lower = currency.lower().strip()
            filtered = [rate for rate in data if rate.get("currency") == currency_lower]
            
            if not filtered:
                available_currencies = ", ".join([rate.get("currency", "").upper() for rate in data])
                return {
                    "error": f"Currency '{currency.upper()}' not found. Available currencies: {available_currencies}",
                    "success": False
                }
            
            rate_info = filtered[0]
            return {
                "success": True,
                "currency": rate_info.get("currency", "").upper(),
                "unit": rate_info.get("unit"),
                "buy": rate_info.get("buy"),
                "sell": rate_info.get("sell"),
                "date": rate_info.get("date"),
                "message": f"{rate_info.get('currency', '').upper()} - Buy: NPR {rate_info.get('buy')}, Sell: NPR {rate_info.get('sell')} per {rate_info.get('unit')} unit(s)"
            }

        # Return all rates
        return {
            "success": True,
            "rates": data,
            "count": len(data),
            "message": f"Retrieved {len(data)} forex rates"
        }

    except httpx.TimeoutException:
        return {"error": "Request timed out. Please try again.", "success": False}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error occurred: {e.response.status_code}", "success": False}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "success": False}


if __name__ == "__main__":
    # Build middleware list conditionally
    middleware = []

    # Only add MCPAuthMiddleware if MCP_AUTH_TOKEN is set and non-empty
    mcp_auth_token = os.getenv("MCP_AUTH_TOKEN")
    if mcp_auth_token and mcp_auth_token.strip():
        middleware.append(Middleware(MCPAuthMiddleware))

    # Always add CORS middleware
    middleware.append(
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],          # Restrict in production!
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
            expose_headers=["*"],
        )
    )
    app = mcp.http_app(middleware=middleware)
    uvicorn.run(app, host="0.0.0.0", port=8000, ws="wsproto")