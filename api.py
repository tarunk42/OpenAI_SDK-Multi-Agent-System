import os
import asyncio
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any # Add Any for structured_data

# Load environment variables from .env file at the project root
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Import the orchestration runner function AFTER loading .env
from .orchestrator import run_orchestration

# --- Pydantic Models for Request/Response ---
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    query: str
    conversation_id: str
    history: Optional[List[ChatMessage]] = None # Allow optional history override

class ChatResponse(BaseModel):
    response: str # Natural language response
    conversation_id: str
    structured_data: Optional[Any] = None # Add field for structured data
    # Optionally return history:
    # history: List[ChatMessage] = Field(default_factory=list)

# --- FastAPI App Setup ---
app = FastAPI(title="Multi-Agent API")

# --- CORS Middleware Configuration (Simplified for Debugging) ---
# Allow all origins, methods, and headers.
# WARNING: This is insecure for production environments.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow any origin
    allow_credentials=False, # Set to False when using wildcard origin
    allow_methods=["*"], # Allow all methods
    allow_headers=["*"], # Allow all headers
)

# --- In-memory History Store ---
# Maps conversation ID to a list of message dictionaries
conversation_histories: Dict[str, List[Dict[str, str]]] = {}

# --- API Endpoint ---
@app.post("/chat", response_model=ChatResponse)
async def handle_chat(request_data: ChatRequest):
    """
    API endpoint to interact with the orchestrated agent system using FastAPI.
    """
    query = request_data.query
    conversation_id = request_data.conversation_id
    history_override = request_data.history

    print(f"\n--- New FastAPI Request ---")
    print(f"Conversation ID: {conversation_id}")
    print(f"Received API query: '{query}'")

    # Retrieve or initialize history
    history_messages = conversation_histories.get(conversation_id, [])

    # Handle optional history override
    if history_override is not None:
        # Convert Pydantic models back to dicts for the orchestrator function
        history_messages = [msg.model_dump() for msg in history_override]
        print("Using history override from request.")
    else:
        print(f"Retrieved history length: {len(history_messages)}")

    # Add user query to history (as dict) before calling orchestrator
    current_turn_history = history_messages + [{"role": "user", "content": query}]

    try:
        # Run the orchestration logic (expects list of dicts)
        # Run orchestration, now returns a tuple (nl_response, structured_data)
        nl_response, structured_data = await run_orchestration(query, current_turn_history)

        # Add assistant response (NL part) to history
        assistant_message = {"role": "assistant", "content": nl_response}
        updated_history = current_turn_history + [assistant_message]

        # Store updated history
        conversation_histories[conversation_id] = updated_history
        print(f"Stored updated history length: {len(updated_history)}")

        print(f"Agent NL response for API: {nl_response}")
        if structured_data:
            print(f"Agent structured data for API: {structured_data}")

        # Return Pydantic model response, including structured_data if present
        return ChatResponse(
            response=nl_response,
            conversation_id=conversation_id,
            structured_data=structured_data
            # Optionally include history:
            # history=[ChatMessage(**msg) for msg in updated_history]
        )

    except Exception as e:
        print(f"Error processing API request: {e}")
        import traceback
        traceback.print_exc()
        # Use FastAPI's HTTPException for standard error responses
        raise HTTPException(status_code=500, detail=f"An internal server error occurred: {e}")

# --- How to Run ---
# Use Uvicorn to run the FastAPI application:
# Ensure virtual environment is active (`source env/bin/activate`)
# From the project root directory (`TestProj90`):
# uvicorn src.api:app --host 127.0.0.1 --port 5000 --reload
#
# --reload flag automatically restarts the server when code changes (useful for development)