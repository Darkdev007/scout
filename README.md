# Scout — Autonomous African Market Research Agent

An AI-powered research agent that takes a single natural language goal and autonomously decides which APIs to call, in what order, to return a comprehensive structured briefing on African markets, companies, and economic conditions.

When you type a query, Scout — an autonomous research agent — searches Wikipedia for background context, pulls the latest news from African and global sources, checks live exchange rates, and synthesizes everything into a structured report.

---

## Live Demo

| Resource | URL |
|----------|-----|
| Web UI | https://scoutcontainer.kindstone-48c6e346.westus2.azurecontainerapps.io/ |
| API Docs | https://scoutcontainer.kindstone-48c6e346.westus2.azurecontainerapps.io/docs |
| Health Check | https://scoutcontainer.kindstone-48c6e346.westus2.azurecontainerapps.io/health |

---

## Access

Scout is password protected. To access the web UI or API, you'll need login credentials.

**Request access:** Reach out to me directly on [LinkedIn](https://www.linkedin.com/in/tobiloba-ayodele/) and I'll send you the username and password.

---

## Architecture

```
User (Browser / Postman)
     ↓
FastAPI Backend (Azure Container Apps)
     ↓
LangGraph ReAct Agent (GPT-4o)
     ↓
┌─────────────────────────────────────────┐
│  Wikipedia API  │  GNews API            │
│  African RSS    │  ExchangeRate API      │
└─────────────────────────────────────────┘
```

A user sends a research query. The LangGraph agent reads the goal, decides which tools to call and in what order, executes them sequentially, observes each result, and loops until it has enough information to synthesize a structured briefing. The agent uses GPT-4o's function calling to make routing decisions dynamically — no hardcoded workflows.

---

## Tech Stack

| Layer | Choice | Justification |
|-------|--------|---------------|
| Agent framework | LangGraph | Explicit graph with full control over state, streaming, and tool routing. Production-grade, not a black box |
| LLM | GPT-4o (via OpenAI) | Reliable function calling, strong reasoning for multi-step research tasks |
| Backend | FastAPI (Python) | Async-native, automatic OpenAPI docs, fast to build with Pydantic validation |
| News (African) | RSS feeds (feedparser) | Techpoint, Nairametrics, Disrupt Africa, TechCrunch Africa — African coverage GNews misses |
| News (Global) | GNews API | 80,000+ sources, date filtering, keyword search |
| Background context | Wikipedia REST API | Free, no key, reliable entity summaries for companies and people |
| Exchange rates | ExchangeRate-API | Live NGN/USD/GBP/EUR/GHS/KES/ZAR rates, free tier, no key needed |
| Hosting | Azure Container Apps | Docker-native, scales to zero when idle, Consumption plan |
| Auth | HTTP Basic Auth | Simple username/password, browser-native popup, no database needed |

---

## Project Structure

```
├── agent.py              # LangGraph graph definition, system prompt, LLM setup
├── tools.py              # Four tool functions decorated with @tool
├── server.py             # FastAPI app, auth, /research and /health endpoints
├── dockerfile            # Container definition
├── requirements.txt      # Python dependencies
├── .env         # Environment variable 
└── templates/
    └── index.html        # Jinja2 frontend — search UI with agent trace display
```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | / | Yes | Scout web UI |
| POST | /research | Yes | Run a research query, returns answer + agent trace |
| GET | /health | No | Health check |
| GET | /docs | No | Auto-generated FastAPI docs |

### POST /research

**Request:**
```json
{
  "query": "Give me a full briefing on Flutterwave"
}
```

**Response:**
```json
{
  "answer": "## Flutterwave Briefing\n\n...",
  "trace": [
    {"tool": "get_wikipedia_summary", "input": {"topic": "Flutterwave"}},
    {"tool_result": "get_wikipedia_summary", "preview": "Title: Flutterwave..."},
    {"tool": "get_african_news", "input": {"query": "Flutterwave"}},
    {"tool_result": "get_african_news", "preview": "Found 3 articles..."},
    {"tool": "get_exchange_rates", "input": {"base_currency": "USD"}},
    {"tool_result": "get_exchange_rates", "preview": "Exchange rates (base: USD)..."}
  ]
}
```

---

## Agent Tools

The agent has access to 4 tools, all defined in `tools.py`:

| Tool | Source | Auth | Description |
|------|--------|------|-------------|
| `get_wikipedia_summary` | Wikipedia REST API | No key | Background context on companies, people, concepts. Tries title variations automatically |
| `get_african_news` | RSS feeds | No key | Latest articles from Techpoint Africa, Nairametrics, Disrupt Africa, TechCrunch Africa |
| `get_global_news` | GNews API | API key | International news with date filtering and keyword search |
| `get_exchange_rates` | ExchangeRate-API | No key | Live NGN, GBP, EUR, GHS, KES, ZAR rates against USD |

### Agent routing logic

The LangGraph ReAct loop follows this pattern per query:

1. `get_wikipedia_summary` — establishes background context first
2. `get_african_news` — checks African sources for recent coverage
3. `get_global_news` — fills gaps if African news returns nothing, or adds international perspective
4. `get_exchange_rates` — always called for African market and finance queries

If any tool returns `NO_RESULTS`, the agent automatically retries with a broader search term before falling back to the next tool.

---

## Data Model

### Query request
- `query` — string, the research goal in natural language

### Research response
- `answer` — markdown-formatted briefing with `##` section headers
- `trace` — array of tool calls and previews showing the agent's reasoning steps

---

## Environment Variables

Create a `.env` file at the root:

```env
OPENAI_API_KEY=your_openai_api_key
GNEWS_API=your_gnews_api_key
SCOUT_USERNAME=scout
SCOUT_PASSWORD=your_secure_password
```

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key for GPT-4o |
| `GNEWS_API` | Yes | GNews API key — free tier at gnews.io |
| `SCOUT_USERNAME` | No | Basic auth username, defaults to `scout` |
| `SCOUT_PASSWORD` | Yes | Basic auth password, set before deploying |

---

## Setup Instructions

### Local Development

1. **Clone the repository:**
```bash
git clone https://github.com/darkdev007/scout.git
cd scout
```

2. **Create a virtual environment:**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the server:**
```bash
uvicorn server:app --reload --port 8000
```

The server starts on `http://localhost:8000`. A browser login popup will appear — enter the username and password from your `.env`.

### Docker

1. **Build the image:**
```bash
docker build -t scout .
```

2. **Run the container:**
```bash
docker run -p 8000:8000 --env-file .env scout
```

Open `http://localhost:8000` to access the UI.

### Azure Deployment

1. **Login to Azure Container Registry:**
```bash
az acr login --name <your-acr-name>
```

2. **Tag your image:**
```bash
docker tag scout <your-acr-name>.azurecr.io/scout:latest
```

3. **Push to ACR:**
```bash
docker push <your-acr-name>.azurecr.io/scout:latest
```

4. **Deploy to Azure Container Apps:**
- Go to Azure Portal → Container Apps → Create
- Select your ACR image
- Set **Consumption** plan (not Standard/Dedicated)
- Set **min replicas: 0**, **max replicas: 1**
- Enable Ingress on port `8000`, traffic from anywhere
- Add environment variables: `OPENAI_API_KEY`, `GNEWS_API`, `SCOUT_USERNAME`, `SCOUT_PASSWORD`
- Save and deploy

> **Important:** Always use the Consumption plan with min replicas set to 0. This enables scale to zero — you pay nothing when Scout is idle.

---

## Example Queries

```
Give me a full briefing on Flutterwave
What is happening in Nigerian fintech this week?
Brief me on Moniepoint from an investor perspective
I am a foreign investor entering Nigeria — give me a full market brief
What does the current NGN/USD rate mean for Nigerian businesses?
Compare the fintech opportunity in Nigeria vs Kenya
Give me a briefing on the company Divest — a Nigerian fintech startup
```

---

## Known Limitations & Trade-offs

- **African RSS feeds are recent-only** — Techpoint, Nairametrics, and Disrupt Africa return the latest 10-20 articles per feed. Queries about companies not in recent news will return `NO_RESULTS` from African sources and fall back to GNews.
- **GNews free tier is 100 requests/day** — sufficient for personal and demo use. High traffic usage would require upgrading to a paid GNews plan.
- **Wikipedia variation matching** — the tool tries multiple title formats to handle African company naming conventions. Obscure entities with unusual Wikipedia titles may still return `NO_RESULTS`.
- **Single-turn only** — Scout processes one query at a time with no conversation memory. Each request is fully independent. Conversational follow-up is not supported in V1.
- **LLM non-determinism** — even at temperature=0, GPT-4o occasionally generates slightly different tool call arguments for identical queries. Search term variation can affect results, particularly for RSS feed matching.
- **Exchange rates lag** — ExchangeRate-API free tier updates once per day. Rates are current but not real-time tick data.

---

## Next Steps

- Add LangSmith tracing for production observability
- Implement per-user API keys for granular access control
- Add `summarize_url` tool to deep-read full articles beyond headlines
- Add Alpha Vantage for stock data on NSE-listed companies
- Add conversation memory with LangGraph checkpointing for multi-turn research sessions
- Add rate limiting per IP with slowapi

---

## Author

**[Ayodele Oluwatobiloba Joshua]**
GitHub: [@darkdev007](https://github.com/darkdev007)
LinkedIn: [Tobiloba Ayodele](https://www.linkedin.com/in/tobiloba-ayodele/)

---

## License

MIT License — feel free to use and build on this project.
