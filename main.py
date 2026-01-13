import os
import uvicorn
from fastmcp import FastMCP
import httpx
from dotenv import load_dotenv
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware
from datetime import datetime, timedelta
import pytz

# Load environment variables from .env file
load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("Currency Converter")

# Cache storage with expiration
_cache = {
    "forex": {"data": None, "expires_at": None},
    "bullion": {"data": None, "expires_at": None},
}

def get_cache_expiration() -> datetime:
    """
    Calculate cache expiration time - next 11 AM NPT.
    If current time is before 11 AM, expire at 11 AM today.
    If current time is after 11 AM, expire at 11 AM tomorrow.
    """
    npt_tz = pytz.timezone("Asia/Kathmandu")
    now = datetime.now(npt_tz)
    
    # Set expiration to 11 AM today
    expiration = now.replace(hour=11, minute=0, second=0, microsecond=0)
    
    # If we're past 11 AM, set it to 11 AM tomorrow
    if now >= expiration:
        expiration += timedelta(days=1)
    
    return expiration

def is_cache_valid(cache_key: str) -> bool:
    """Check if cache is valid for the given key."""
    cache_entry = _cache.get(cache_key)
    if not cache_entry or cache_entry["data"] is None:
        return False
    
    expires_at = cache_entry["expires_at"]
    if expires_at is None:
        return False
    
    npt_tz = pytz.timezone("Asia/Kathmandu")
    now = datetime.now(npt_tz)
    return now < expires_at

def set_cache(cache_key: str, data: dict) -> None:
    """Set cache data with expiration."""
    _cache[cache_key] = {
        "data": data,
        "expires_at": get_cache_expiration()
    }

def get_cache(cache_key: str):
    """Get cached data if valid."""
    if is_cache_valid(cache_key):
        return _cache[cache_key]["data"]
    return None

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
    Fetch current bullion (gold and silver) prices for Nepal in NPR currency.

    This tool returns a clear, machine-readable schema so language models
    can confidently select it when the user asks for bullion prices.

    Example usage by LLMs: choose this tool when the user asks for "today's gold price", "current
    gold price in NPR", "silver rate in NPR", or "bullion prices in Nepal".
    
    Note: Results are cached until 11 AM NPT daily to reduce latency and API calls.
    """
    try:
        # Check cache first
        cached_data = get_cache("bullion")
        if cached_data:
            cached_data["cached"] = True
            return cached_data
        
        url = os.getenv("BULLION_URL")

        # Make API request
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()
            data = response.json()

        # Build a clear, machine-readable response while keeping
        # legacy top-level keys for compatibility.
        unit = data.get("unit")
        fine_gold = data.get("fine_gold")
        silver = data.get("silver")
        date = data.get("date")

        result = {
            "success": True,
            "tool": "get_bullion_prices",
            "category": "bullion_prices",
            "schema_version": "1.0",
            "cached": False,
            # Machine-readable payload
            "data": {
                "gold": {"amount": fine_gold, "unit": unit, "currency": "NPR"},
                "silver": {"amount": silver, "unit": unit, "currency": "NPR"},
                "date": date,
                "source": url,
            },
            # Backwards-compatible keys
            "fine_gold": fine_gold,
            "silver": silver,
            "unit": unit,
            "date": date,
            "raw": data,
            "message": f"Fine Gold: {fine_gold} per {unit}, Silver: {silver} per {unit} (as of {date})",
        }
        
        # Cache the result
        set_cache("bullion", result)
        return result

    except httpx.TimeoutException:
        return {"error": "Request timed out. Please try again.", "success": False}
    except httpx.HTTPStatusError as e:
        return {"error": f"HTTP error occurred: {e.response.status_code}", "success": False}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}", "success": False}


@mcp.resource("banking://rates/daily")
async def get_banking_rates() -> str:
    """
    Get daily banking rates information from Nepal Rastra Bank.
    
    This resource provides a consolidated view of forex and bullion rates
    that are updated daily at 11:00 AM NPT.
    
    Returns:
        A formatted string with current banking rates information.
    
    Note: Results are cached until 11 AM NPT daily to reduce latency and API calls.
    """
    try:
        # Try to get from cache first
        forex_data = get_cache("forex")
        bullion_data = get_cache("bullion")
        from_cache = forex_data is not None and bullion_data is not None
        
        if not forex_data or not bullion_data:
            forex_url = os.getenv("FOREX_URL")
            bullion_url = os.getenv("BULLION_URL")
            
            async with httpx.AsyncClient() as client:
                # Get forex rates if not cached
                if not forex_data:
                    forex_response = await client.get(forex_url, timeout=10.0)
                    forex_response.raise_for_status()
                    forex_data = forex_response.json()
                    set_cache("forex", forex_data)
                
                # Get bullion prices if not cached
                if not bullion_data:
                    bullion_response = await client.get(bullion_url, timeout=10.0)
                    bullion_response.raise_for_status()
                    bullion_data = bullion_response.json()
                    # Cache the raw bullion data separately for resource
                    set_cache("bullion", bullion_data)
        
        # Format the response
        result = "# Nepal Rastra Bank - Daily Banking Rates\n\n"
        result += f"**Last Updated:** {forex_data[0].get('date', 'N/A')} at 11:00 AM NPT\n"
        result += f"**Cached:** {'Yes' if from_cache else 'No'}\n\n"
        
        # Bullion Prices - handle both cached dict and raw dict
        bullion_raw = bullion_data.get('raw', bullion_data) if isinstance(bullion_data, dict) and 'raw' in bullion_data else bullion_data
        result += "## Bullion Prices (NPR)\n\n"
        result += f"- **Fine Gold:** NPR {bullion_raw.get('fine_gold')} per {bullion_raw.get('unit')}\n"
        result += f"- **Silver:** NPR {bullion_raw.get('silver')} per {bullion_raw.get('unit')}\n"
        result += f"- **Date:** {bullion_raw.get('date')}\n\n"
        
        # Forex Rates
        result += "## Foreign Exchange Rates\n\n"
        result += "| Currency | Unit | Buy (NPR) | Sell (NPR) |\n"
        result += "|----------|------|-----------|------------|\n"
        
        for rate in forex_data[:10]:  # Show top 10 currencies
            currency = rate.get('currency', '').upper()
            unit = rate.get('unit', 1)
            buy = rate.get('buy', 'N/A')
            sell = rate.get('sell', 'N/A')
            result += f"| {currency} | {unit} | {buy} | {sell} |\n"
        
        result += f"\n**Total Currencies Available:** {len(forex_data)}\n"
        result += "\n---\n"
        result += "*Rates are updated daily at 11:00 AM NPT by Nepal Rastra Bank*\n"
        
        return result
        
    except Exception as e:
        return f"Error fetching banking rates: {str(e)}"


@mcp.tool()
async def get_forex_rates(currency: str) -> dict:
    """
    Fetch current forex buying and selling rates (NPR) provided by Nepal Rastra Bank.

    This tool is intended for requests seeking official Nepalese foreign
    exchange rates denominated in Nepalese Rupee (NPR). Language models should
    prefer this tool when the user asks for NRB / Nepal Rastra Bank buy/sell
    rates, forex rates, or currency conversion references tied to
    Nepal's official rates.

    Args:
        currency: ISO currency code to filter (e.g., USD, EUR, INR), or "ALL" to retrieve all rates.
            When a specific currency code is provided, returns a single structured rate object.
            Use "ALL" to get the complete list of all available forex rates.

    Example usage: "What's the USD buying rate in NPR?", "Show NRB forex rates", or
    "Nepal Rastra Bank buy/sell rates for EUR".
    
    Note: Results are cached until 11 AM NPT daily to reduce latency and API calls.
    """
    try:
        # Check cache first
        cached_data = get_cache("forex")
        data = cached_data if cached_data else None
        from_cache = data is not None
        
        if not data:
            url = os.getenv("FOREX_URL")

            # Make API request
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()
                data = response.json()
            
            # Cache the raw data
            set_cache("forex", data)

        # If currency is "ALL", return all rates
        if currency.upper().strip() == "ALL":
            return {
                "success": True,
                "tool": "get_forex_rates",
                "category": "forex_rates",
                "schema_version": "1.0",
                "cached": from_cache,
                "data": {"rates": data, "source": os.getenv("FOREX_URL")},
                "rates": data,
                "count": len(data),
                "raw": data,
                "message": f"Retrieved {len(data)} forex rates from Nepal Rastra Bank",
            }

        # Filter for the specific currency
        currency_lower = currency.lower().strip()
        filtered = [rate for rate in data if rate.get("currency") == currency_lower]

        if not filtered:
            available_currencies = ", ".join([rate.get("currency", "").upper() for rate in data])
            return {
                "success": False,
                "error": f"Currency '{currency.upper()}' not found. Available currencies: {available_currencies}",
                "tool": "get_forex_rates",
                "category": "forex_rates",
            }

        rate_info = filtered[0]
        rate_obj = {
            "currency": rate_info.get("currency", "").upper(),
            "unit": rate_info.get("unit"),
            "buy": rate_info.get("buy"),
            "sell": rate_info.get("sell"),
            "date": rate_info.get("date"),
            "source": os.getenv("FOREX_URL"),
        }

        return {
            "success": True,
            "tool": "get_forex_rates",
            "category": "forex_rates",
            "schema_version": "1.0",
            "cached": from_cache,
            "data": rate_obj,
            # Backwards-compatible keys
            "currency": rate_obj["currency"],
            "unit": rate_obj["unit"],
            "buy": rate_obj["buy"],
            "sell": rate_obj["sell"],
            "date": rate_obj["date"],
            "raw": rate_info,
            "message": f"{rate_obj['currency']} - Buy: NPR {rate_obj['buy']}, Sell: NPR {rate_obj['sell']} per {rate_obj['unit']} unit(s)",
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
            allow_origins=[*],          
            allow_methods=["*"],
            allow_headers=["*"],
            allow_credentials=True,
            expose_headers=["*"],
        )
    )
    app = mcp.http_app(middleware=middleware)
    uvicorn.run(app, host="0.0.0.0", port=8000, ws="wsproto")