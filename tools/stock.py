import os
import requests
from typing_extensions import TypedDict
from typing import Optional
from datetime import datetime # Import datetime for timestamp
# Removed: from dotenv import load_dotenv
# Environment variables should be loaded by the main application entry point (e.g., api.py)

from agents import function_tool

# Input schema for the stock tool
class StockInput(TypedDict):
    symbol: str # The stock ticker symbol (e.g., AAPL, GOOGL)

# Define the raw function first
def _fetch_stock_price_func(data: StockInput) -> dict:
    """
    (Internal) Fetch detailed stock quote (price, high, low, volume) for a given ticker symbol using the Financial Modeling Prep API.
    Returns a dictionary containing stock data on success, or an error dictionary on failure.
    """
    # Ensure the correct environment variable name is used (as seen in previous logs)
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        # print("Error: FMP_API_KEY not set in environment.") # Removed print
        return {"error": "Server configuration error: Stock API key not set."}

    symbol = data.get("symbol")
    if not symbol:
        return {"error": "Please provide a stock ticker symbol."}

    # Use the /quote endpoint instead of /quote-short
    base_url = f"https://financialmodelingprep.com/api/v3/quote/{symbol.upper()}"
    params = {"apikey": api_key}

    try:
        response = requests.get(base_url, params=params) # Pass params to requests.get
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        res = response.json()

        if isinstance(res, list) and len(res) > 0:
            stock_data = res[0]
            # Extract the required fields
            return {
                "symbol": stock_data.get("symbol"),
                "latest_price": stock_data.get("price"), # Map 'price' to 'latest_price'
                "high": stock_data.get("dayHigh"),      # Map 'dayHigh' to 'high'
                "low": stock_data.get("dayLow"),        # Map 'dayLow' to 'low'
                "volume": stock_data.get("volume"),
                "timestamp": datetime.now().isoformat() # Add current timestamp
            }
        elif isinstance(res, dict) and res.get("Error Message"):
             # print(f"Error from FMP API for {symbol}: {res.get('Error Message')}") # Removed print
             return {"error": f"Could not fetch data for symbol '{symbol}'. It might be invalid. {res.get('Error Message')}"}
        else:
            # print(f"Unexpected response format from FMP API for {symbol}: {res}") # Removed print
            return {"error": f"Could not fetch data for symbol '{symbol}'. Unexpected API response format."}

    except requests.exceptions.HTTPError as http_err:
        # print(f"HTTP error occurred: {http_err} - Response: {response.text}") # Removed print
        if response.status_code == 401:
             return {"error": "Server configuration error: Invalid Stock API key."}
        elif response.status_code == 404:
             return {"error": f"Stock symbol '{symbol}' not found."}
        else:
            return {"error": f"Failed to fetch stock data due to HTTP error: {http_err}"}
    except requests.exceptions.RequestException as req_err:
        # print(f"Request error occurred: {req_err}") # Removed print
        return {"error": f"Network error connecting to Stock API: {req_err}"}
    except Exception as e:
        # print(f"An unexpected error occurred in fetch_stock_price: {e}") # Removed print
        return {"error": f"An unexpected error occurred: {e}"}

# Create the FunctionTool object for the agent runner
fetch_stock_price_tool = function_tool(_fetch_stock_price_func)

# Expose the raw function for direct calls
fetch_stock_price = _fetch_stock_price_func