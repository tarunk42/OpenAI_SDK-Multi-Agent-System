# 🧠 OpenAI Agent SDK - Personal Assistant

A modular AI-native assistant powered by the **OpenAI Agent SDK**, capable of intelligently answering real-time weather and stock-related queries through specialized agents and tool integrations.

Built with:
- 🔁 **OpenAI Agent SDK**
- ⚙️ FunctionTool-based modular tools
- 🚀 FastAPI for backend orchestration
- 🌤️ OpenWeather API + 📈 FinancialModelingPrep API
- 🤖 LLM-driven intent routing and summarization

---

## 📸 Demo Flow

1. **User:** "What's the weather in Tokyo?"
2. **→ Orchestrator Agent** decides it's a weather query.
3. **→ Triage Agent** routes to **Weather Agent**.
4. **→ Weather Tool** fetches data from OpenWeather.
5. **→ Weather Agent** summarizes and responds.

---

## 🏗️ Architecture
```
                        User Query
                            ↓
                    FastAPI /chat endpoint
                            ↓
                    Orchestrator Agent
                            ↓
            ┌──────────────────────────────────────┐
            │         Triage Agent                 │
            │ ┌──────────────┐ ┌─────────┐         │
            │ │ WeatherAgent │ │ StockAgent (live) │
            │ │              │ │ HistoricalAgent   │
            │ └──────────────┘ └─────────┘         │
            └──────────────────────────────────────┘
                           ↓
                External APIs (OpenWeather, FMP)
```

---

## 🚀 Quick Start

### 1. 📦 Install dependencies

```bash
pip install -r requirements.txt
```

### 2. 🔑 Set up environment variables

Create a `.env` file at the project root:

```env
OPEN_WEATHER_API_KEY=your_openweather_key
FMP_API_KEY=your_financial_modeling_prep_key
OPENAI_API_KEY=your_openai_api_key
```

### 3. 🔁 Run the FastAPI server

```bash
uvicorn src.api:app --host 127.0.0.1 --port 5000 --reload
```

---

## 🧩 Available Agents

| Agent                  | Purpose                                      | Tool Backend                      |
|------------------------|----------------------------------------------|-----------------------------------|
| `Weather Agent`        | Get current weather and forecasts            | OpenWeather API                   |
| `Stock Agent`          | Real-time stock quotes                       | FMP `/quote` API                  |
| `Historical Stock Agent` | Historical stock OHLCV data                 | FMP `/historical-price-full` API  |
| `Triage Agent`         | Routes based on intent                       | N/A                               |
| `Orchestrator Agent`   | Manages flow, user context & conversations   | N/A                               |

---

## 📦 API Usage

### POST `/chat`

#### Request Body

```json
{
  "query": "What's the price of AAPL?",
  "conversation_id": "user-123"
}
```

#### Response Body

```json
{
  "response": "As of now, AAPL is trading at $172.34...",
  "conversation_id": "user-123",
  "structured_data": {
    "symbol": "AAPL",
    "latest_price": 172.34,
    "high": 174.0,
    "low": 169.5,
    "volume": 31000000,
    "timestamp": "2025-04-21T10:34:00"
  }
}
```

---

## 🔍 Project Structure

```
src/
├── api.py                # FastAPI entry point
├── orchestrator.py       # Main logic for routing + NL generation
├── agent.py              # Agent definitions (weather, stock, triage, etc.)
└── tools/                # Tool implementations
    ├── weather.py
    ├── stock.py
    └── historical_stock.py
```

---

## 🧠 Powered by OpenAI Agent SDK

This project uses:

- `Agent`: LLM-driven modules with personas and instructions.
- `FunctionTool`: to wrap external APIs in a tool interface.
- `Runner.run(agent, prompt)`: to generate responses from structured data.

---

## ✅ TODO / Extensions

- [ ] Add support for crypto, news, or ETF data
- [ ] Implement user authentication / sessions
- [ ] Standardize structured output schemas

---

## 🧪 Example Queries

- `"What’s the weather like in Paris?"`
- `"Show me Tesla stock price"`
- `"Give me Apple's stock performance for the last month"`
- `"What’s the forecast for this weekend in Bangalore?"`

---

## 👨‍💻 Author

**Tarun Kashyap**  
🧠 AWS Certified ML Engineer  
📈 Building AI-native tools for smarter investing  
🌐 [LinkedIn](https://www.linkedin.com/in/tarun-kashyap/) | [GitHub](https://github.com/tarunk42)

---

## 🛡 License

MIT License. Use freely with attribution.