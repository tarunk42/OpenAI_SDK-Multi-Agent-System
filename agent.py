from agents import Agent
from .tools.weather import fetch_weather_tool # Import the FunctionTool object

# Define the specialized Weather Agent
weather_agent = Agent(
    name="Weather Agent",
    handoff_description="Specialist agent for weather-related questions (current conditions, forecasts).",
    instructions="You are a helpful assistant that provides real-time weather updates based on user queries. Use the available tool to fetch the data.",
    tools=[fetch_weather_tool], # Use the FunctionTool object
)

# We will define other agents (Stock, Triage, Orchestrator) in separate files or below.
from .tools.stock import fetch_stock_price_tool # Import the FunctionTool object

# Define the specialized Stock Agent
stock_agent = Agent(
    name="Stock Agent",
    handoff_description="Specialist agent for fetching current stock prices.",
    instructions="You are an assistant that provides the latest stock price for a given ticker symbol using the available tool.",
    tools=[fetch_stock_price_tool], # Use the FunctionTool object
)
from .tools.historical_stock import fetch_historical_stock_tool # Import the new tool object

# Define the specialized Historical Stock Agent
historical_stock_agent = Agent(
    name="Historical Stock Agent",
    handoff_description="Specialist agent for fetching historical stock data for a given date range.",
    instructions=(
        "You are an assistant that provides historical end-of-day stock data (open, high, low, close, volume) "
        "for a specific ticker symbol between a start and end date. Use the available tool to fetch the data. "
        "When presenting the data, mention the symbol and the date range clearly. If there are many data points, "
        "summarize key trends or provide the first few and last few data points, rather than listing everything."
    ),
    tools=[fetch_historical_stock_tool],
)

# Define the Triage Agent (AFTER all specialist agents it references)
triage_agent = Agent(
    name="Triage Agent",
    instructions=(
        "Analyze the user's request and determine the primary topic. "
        "If the request is primarily about current weather conditions or forecasts, hand off to the Weather Agent. "
        "If the request is primarily about fetching the *current* price of a specific stock, hand off to the Stock Agent. "
        "If the request is about fetching *historical* stock data (e.g., price over a period, past performance), hand off to the Historical Stock Agent. "
        "If the request is ambiguous, very general, or doesn't clearly fall into weather or stock categories (current or historical), respond that you can currently only handle specific weather or stock price queries (current or historical)."
    ),
    handoffs=[weather_agent, stock_agent, historical_stock_agent], # List of agents it can hand off to
    # No tools needed for triage itself, it just routes based on instructions
)