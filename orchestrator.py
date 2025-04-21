import re # Import regex for parameter extraction
from agents import Agent, Runner
from datetime import date, timedelta # Import date utilities
from .agent import triage_agent, weather_agent, stock_agent, historical_stock_agent # Import ALL specialist agents
from .tools.weather import fetch_weather, WeatherInput
from .tools.stock import fetch_stock_price, StockInput
from .tools.historical_stock import fetch_historical_stock, HistoricalStockInput # Import historical tool
from typing import List, Dict, Tuple, Optional, Any

# Define the Orchestration Agent
# This agent is conversational and manages the interaction flow.
orchestrator_agent = Agent(
    name="Orchestrator Agent",
    instructions=(
        "You are the primary assistant managing the conversation. "
        "Your goal is to understand the user's request and delegate tasks to specialized agents via the Triage Agent. "
        "Maintain a friendly and conversational tone. "
        "Analyze the user's latest message in the context of the conversation history. "
        "If the user's request seems actionable (like asking for weather or stock price), formulate a clear query based on their request and pass it to the Triage Agent for routing. "
        "If the user is just chatting, respond conversationally without invoking the Triage Agent. "
        "If the Triage Agent provides a result, present it clearly to the user. "
        "If the Triage Agent indicates it cannot handle the request, inform the user politely. "
        "Do not directly answer weather or stock questions yourself; always delegate through the Triage Agent."
    ),
    # This agent doesn't directly use tools or handoffs in the traditional sense.
    # It orchestrates by deciding *whether* and *what* to send to the Triage Agent.
    # We'll handle the logic of calling the Triage Agent in the main run function.
)

# We need a function that handles the orchestration logic, including history.
# This function will use the orchestrator_agent to decide the next step
# and potentially call the triage_agent.

async def run_orchestration(query: str, history: List[Dict[str, str]]) -> Tuple[str, Optional[Any]]:
    """
    Manages the conversation using the orchestrator and triage agents.
    - Uses orchestrator_agent to interpret the query in context of history (list of dicts).
    - Decides whether to call triage_agent or respond directly.
    - Returns a tuple: (natural_language_response: str, structured_data: Optional[Any])
    """
    print(f"--- Running Orchestration ---")
    print(f"History: {history}") # Log history (already list of dicts)
    print(f"Current Query: {query}")

    # Combine history and current query for the orchestrator
    messages_for_orchestrator = history + [{"role": "user", "content": query}]

    # Run the orchestrator to decide the plan (or respond directly)
    # Runner.run likely accepts List[Dict[str, str]] for the messages argument
    # We expect its output to guide whether we call triage or not.
    # For simplicity here, we'll assume the orchestrator's primary role
    # is to decide IF delegation is needed. A more complex setup might
    # have the orchestrator *generate* the query for the triage agent.
    # Let's simplify: if the query looks like a task, we run triage.
    # A more robust approach would involve analyzing orchestrator_result.

    # Improved heuristic: Check for keywords OR potential company names/symbols
    # TODO: A more robust approach would involve analyzing the orchestrator_agent's
    #       output to determine intent, but this heuristic is a step up.
    # Keywords for different task types
    weather_keywords = ["weather", "temperature", "forecast", "conditions"]
    current_stock_keywords = ["stock", "price", "quote", "ticker", "symbol"] # Focus on current price
    historical_stock_keywords = ["historical", "history", "past", "performance", "last month", "last year", "between", "from", "since"]
    # Combine general stock terms that might apply to either current or historical
    general_stock_keywords = ["stock", "ticker", "symbol"]
    potential_symbols_or_names = ["ford", "microsoft", "tesla", "apple", "google", "nvidia", "aapl", "goog", "msft", "tsla", "f", "nvda"] # Add more as needed

    lower_query = query.lower()

    # --- Heuristic Refinement ---
    is_weather_query = any(keyword in lower_query for keyword in weather_keywords)
    # Add check for relative date patterns like "last X days/weeks/months"
    relative_date_pattern = r'\b(last|past)\s+(\d+)\s+(day|week|month)s?\b'
    has_relative_date = re.search(relative_date_pattern, query, re.IGNORECASE)
    is_historical_query = any(keyword in lower_query for keyword in historical_stock_keywords) or \
                          re.search(r'\b\d{4}-\d{2}-\d{2}\b', query) or \
                          has_relative_date # Add relative date check

    # Check for current stock only if not clearly historical
    is_current_stock_query = not is_historical_query and (
        any(keyword in lower_query for keyword in current_stock_keywords) or
        any(entity in lower_query for entity in potential_symbols_or_names) or
        any(word.isupper() and 3 <= len(word) <= 5 for word in query.split())
    )
    # If general stock terms are present but neither current nor historical flags are strong, lean towards current
    if not is_historical_query and not is_current_stock_query and any(keyword in lower_query for keyword in general_stock_keywords):
         is_current_stock_query = True

    is_task_query = is_weather_query or is_current_stock_query or is_historical_query

    if is_task_query:
        print("Orchestrator identified a potential task query.")
        nl_response = "I encountered an issue processing that request." # Default response
        structured_data = None
        tool_to_use = None
        tool_input = None

        # --- Determine Tool and Extract Parameters (Enhanced) ---

        def extract_symbol(text):
            # Try uppercase first
            match = re.search(r"\b([A-Z]{1,5})\b", text)
            if match: return match.group(1).upper()
            # Try known names (crude mapping)
            lower_text = text.lower()
            symbol_map = {"ford": "F", "microsoft": "MSFT", "tesla": "TSLA", "apple": "AAPL", "google": "GOOGL", "nvidia": "NVDA"}
            for name, sym in symbol_map.items():
                if name in lower_text:
                    return sym
            return None

        def extract_dates(text):
            today = date.today()
            lower_text = text.lower()

            # 1. Look for YYYY-MM-DD format (most specific)
            dates_iso = re.findall(r'\b(\d{4}-\d{2}-\d{2})\b', text)
            if len(dates_iso) >= 2:
                # Sort to ensure start is before end
                dates_iso.sort()
                return dates_iso[0], dates_iso[1]
            elif len(dates_iso) == 1:
                 # If only one specific date, maybe user wants data *since* that date?
                 # Or just that single day? API needs a range. Let's default to range from that day to today.
                 # Could ask for clarification, but let's try this default.
                 return dates_iso[0], today.isoformat()

            # 2. Look for relative ranges like "last X days/weeks/months"
            relative_match = re.search(relative_date_pattern, text, re.IGNORECASE)
            if relative_match:
                _, num_str, unit = relative_match.groups()
                num = int(num_str)
                end_date = today
                if unit == 'day':
                    start_date = end_date - timedelta(days=num)
                elif unit == 'week':
                    start_date = end_date - timedelta(weeks=num)
                elif unit == 'month':
                    # Approximate month by multiplying days (crude but simple)
                    start_date = end_date - timedelta(days=num * 30)
                else: # Should not happen based on regex
                    return None, None
                # Ensure start_date is not after end_date (can happen with num=0)
                if start_date >= end_date:
                    start_date = end_date - timedelta(days=1) # Default to 1 day if range is invalid
                return start_date.isoformat(), end_date.isoformat()


            # 3. Look for keywords like "last month", "last year"
            if "last month" in lower_text:
                first_day_this_month = today.replace(day=1)
                last_day_last_month = first_day_this_month - timedelta(days=1)
                first_day_last_month = last_day_last_month.replace(day=1)
                return first_day_last_month.isoformat(), last_day_last_month.isoformat()
            if "last year" in lower_text:
                first_day_last_year = date(today.year - 1, 1, 1)
                last_day_last_year = date(today.year - 1, 12, 31)
                return first_day_last_year.isoformat(), last_day_last_year.isoformat()

            # Add more specific keywords if needed, e.g., "this week", "year to date"

            # 4. If no dates found, return None
            return None, None


        # Prioritize based on flags
        if is_weather_query:
            weather_match = re.search(r"(?:weather in|forecast for|conditions in)\s+([\w\s]+)", query, re.IGNORECASE)
            if weather_match:
                tool_to_use = "weather"
                location = weather_match.group(1).strip()
                tool_input = WeatherInput(location=location, unit="metric")
                print(f"Determined tool: weather, location: {location}")
            else:
                 nl_response = "Which location's weather are you interested in?"

        elif is_historical_query:
            symbol = extract_symbol(query)
            start_date, end_date = extract_dates(query)
            if symbol and start_date: # Require symbol and at least start date
                tool_to_use = "historical_stock"
                # End date defaults to today in the tool if None
                tool_input = HistoricalStockInput(symbol=symbol, start_date=start_date, end_date=end_date)
                print(f"Determined tool: historical_stock, symbol: {symbol}, start: {start_date}, end: {end_date or 'today'}")
            elif not symbol:
                 nl_response = "Which stock symbol's historical data do you want?"
            else: # Symbol found, but no date
                 nl_response = f"For which date range do you want historical data for {symbol}?"

        elif is_current_stock_query:
            symbol = extract_symbol(query)
            if symbol:
                tool_to_use = "stock"
                tool_input = StockInput(symbol=symbol)
                print(f"Determined tool: stock, symbol: {symbol}")
            else:
                nl_response = "Which stock symbol are you interested in?"

        # --- Execute Tool Directly ---
        if tool_to_use and tool_input:
            print(f"Calling tool '{tool_to_use}' directly with input: {tool_input}")
            try:
                # Call the imported raw function directly
                if tool_to_use == "weather":
                    structured_data = fetch_weather(tool_input)
                elif tool_to_use == "stock":
                    structured_data = fetch_stock_price(tool_input)
                elif tool_to_use == "historical_stock":
                     structured_data = fetch_historical_stock(tool_input)

                print(f"Direct tool call result: {structured_data}")

                # --- Generate NL Response (using structured data) ---
                if structured_data and 'error' not in structured_data:
                    # Use the appropriate specialist agent to summarize the data
                    # Select the correct agent for summarization
                    if tool_to_use == "weather":
                        agent_to_summarize = weather_agent
                    elif tool_to_use == "stock":
                        agent_to_summarize = stock_agent
                    elif tool_to_use == "historical_stock":
                        agent_to_summarize = historical_stock_agent
                    else: # Should not happen
                         agent_to_summarize = orchestrator_agent # Fallback

                    # Create context for the summarizer agent
                    summary_prompt = f"User asked: '{query}'. You retrieved the following data: {structured_data}. Please summarize this data concisely for the user."
                    # For historical data, add a note about potential truncation if data is large
                    if tool_to_use == "historical_stock" and isinstance(structured_data.get('historical'), list) and len(structured_data['historical']) > 10:
                         summary_prompt += " Note: If there are many data points, summarize key trends or provide the first few and last few data points, rather than listing everything."

                    print(f"Running {agent_to_summarize.name} to generate NL response...")
                    summary_result = await Runner.run(agent_to_summarize, summary_prompt) # Pass data as context
                    if summary_result and hasattr(summary_result, 'final_output') and summary_result.final_output:
                        nl_response = str(summary_result.final_output)
                        print(f"Generated NL response: {nl_response}")
                    else:
                        print("Summarizer agent failed to generate NL response.")
                        nl_response = "I found the data, but had trouble summarizing it."
                        # Keep structured_data so frontend can still display it
                elif structured_data and 'error' in structured_data:
                    print(f"Tool returned an error: {structured_data['error']}")
                    # Ask orchestrator to formulate a polite error message based on the tool error
                    error_context = messages_for_orchestrator + [{"role": "assistant", "content": f"Internal Note: The {tool_to_use} tool failed with error: {structured_data['error']}. Inform user politely."}]
                    error_response_run = await Runner.run(orchestrator_agent, error_context)
                    nl_response = str(error_response_run.final_output) if error_response_run and hasattr(error_response_run, 'final_output') else f"Sorry, I couldn't get the {tool_to_use} data due to an error."
                    structured_data = None # Don't send error dict to frontend
                else:
                     # Should not happen if tool returns dict, but handle anyway
                     print("Tool call returned unexpected result.")
                     nl_response = f"Sorry, the {tool_to_use} tool returned an unexpected result."
                     structured_data = None

            except Exception as e:
                print(f"Error during direct tool call or NL generation: {e}")
                import traceback
                traceback.print_exc()
                nl_response = f"Sorry, an internal error occurred while processing the {tool_to_use} request."
                structured_data = None
        elif not tool_to_use:
             # If heuristic triggered but no specific tool/params identified
             print("Task query detected, but specific tool/parameters not identified. Asking orchestrator.")
             # Fallback to general orchestrator response
             try:
                 orchestrator_response = await Runner.run(orchestrator_agent, messages_for_orchestrator)
                 if orchestrator_response and hasattr(orchestrator_response, 'final_output') and orchestrator_response.final_output:
                     nl_response = str(orchestrator_response.final_output)
                 else:
                     nl_response = "I understand you're asking about something specific, but I need more details."
             except Exception as e:
                 print(f"Error during fallback orchestrator call: {e}")
                 nl_response = "Sorry, I had trouble understanding that request."
             structured_data = None


        return nl_response, structured_data
    else:
        # Query doesn't seem like a task, let the orchestrator handle conversationally
        print("Orchestrator decided to respond directly (not a task).")
        try:
            # Run orchestrator agent with history to get conversational response
            # Pass the list of message dicts as the second positional argument
            orchestrator_response = await Runner.run(orchestrator_agent, messages_for_orchestrator)
            if orchestrator_response and hasattr(orchestrator_response, 'final_output') and orchestrator_response.final_output:
                 print(f"Orchestrator direct response: {orchestrator_response.final_output}")
                 return str(orchestrator_response.final_output), None # Return NL response, no structured data
            else:
                 print("Orchestrator did not provide a direct response.")
                 return "I'm not sure how to respond to that right now.", None # Return NL response, no structured data
        except Exception as e:
            error_msg = f"An error occurred during Orchestrator direct response: {e}"
            print(error_msg)
            return f"Sorry, an internal error occurred while formulating a response: {e}", None # Return NL response, no structured data