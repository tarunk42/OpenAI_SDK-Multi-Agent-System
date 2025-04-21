import os
import requests
from typing_extensions import TypedDict
from typing import Optional, List, Dict, Any
from datetime import date

# Environment variables loaded by api.py
from agents import function_tool

# Input schema
class HistoricalStockInput(TypedDict):
    symbol: str       # Stock ticker symbol (e.g., AAPL)
    start_date: str   # Start date in YYYY-MM-DD format
    end_date: str     # End date in YYYY-MM-DD format (defaults to today if not provided)

# Define the raw function first
def _fetch_historical_stock_func(data: HistoricalStockInput) -> Dict[str, Any]:
    """
    (Internal) Fetches historical end-of-day stock data for a given symbol and date range
    using the Financial Modeling Prep API. Returns a dictionary containing a list of
    historical data points or an error dictionary.
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return {"error": "Server configuration error: Stock API key not set."}

    symbol = data.get("symbol")
    start_date_str = data.get("start_date")
    end_date_str = data.get("end_date", date.today().isoformat()) # Default end date to today

    if not symbol:
        return {"error": "Please provide a stock ticker symbol."}
    if not start_date_str:
        return {"error": "Please provide a start date (YYYY-MM-DD)."}

    # Basic validation for date format (more robust validation could be added)
    try:
        date.fromisoformat(start_date_str)
        date.fromisoformat(end_date_str)
    except ValueError:
        return {"error": "Invalid date format. Please use YYYY-MM-DD."}

    base_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol.upper()}"
    params = {
        "apikey": api_key,
        "from": start_date_str,
        "to": end_date_str
    }

    print(f"Fetching historical data: URL={base_url}, Params={params}")

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()
        res = response.json()

        # The API response structure might contain a 'historical' key
        if isinstance(res, dict) and 'historical' in res and isinstance(res['historical'], list):
            historical_data = res['historical']
            # Optionally filter/format the data if needed
            formatted_data = [
                {
                    "date": item.get("date"),
                    "open": item.get("open"),
                    "high": item.get("high"),
                    "low": item.get("low"),
                    "close": item.get("close"),
                    "volume": item.get("volume")
                } for item in historical_data
            ]
            # Sort by date ascending (API might already do this)
            formatted_data.sort(key=lambda x: x.get("date", ""))
            print(f"Successfully fetched {len(formatted_data)} historical records.")
            return {"symbol": symbol, "historical": formatted_data}
        elif isinstance(res, dict) and res.get("Error Message"):
             return {"error": f"Could not fetch historical data for symbol '{symbol}'. API Error: {res.get('Error Message')}"}
        else:
            print(f"Unexpected response format for historical data: {res}")
            return {"error": f"Could not fetch historical data for symbol '{symbol}'. Unexpected API response format."}

    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err} - Response: {response.text}")
        if response.status_code == 401:
             return {"error": "Server configuration error: Invalid Stock API key."}
        elif response.status_code == 404: # May indicate invalid symbol or no data for range
             return {"error": f"Historical data for symbol '{symbol}' not found or unavailable for the specified date range."}
        else:
            return {"error": f"Failed to fetch historical stock data due to HTTP error: {http_err}"}
    except requests.exceptions.RequestException as req_err:
        return {"error": f"Network error connecting to Stock API: {req_err}"}
    except Exception as e:
        return {"error": f"An unexpected error occurred: {e}"}

# Create the FunctionTool object for the agent runner
fetch_historical_stock_tool = function_tool(_fetch_historical_stock_func)

# Expose the raw function for direct calls
fetch_historical_stock = _fetch_historical_stock_func