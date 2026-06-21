# 2hr-jobs-mcp-server

**MCP server for Polish IT job board [2hr.pl](https://2hr.pl) — search IT jobs, salary data and market analytics via Model Context Protocol.**

Built with [FastMCP](https://github.com/jlowin/fastmcp) and Python 3.12. Works with Claude Desktop, Cursor, Windsurf, VS Code, and any MCP-compatible AI client.

---

## What is MCP?

[Model Context Protocol (MCP)](https://modelcontextprotocol.io) is an open standard by Anthropic that allows AI models like Claude to securely call external APIs and databases in real time. Instead of pasting data manually into a chat, your AI agent fetches live data automatically.

This server connects Claude (or any MCP-compatible client) to the 2hr.pl job board — so you can ask:

- *"Find remote Python senior jobs above 20 000 PLN B2B"*
- *"Is 18 000 PLN fair for a mid React developer in Warsaw?"*
- *"Compare salaries: PHP vs Go for a senior in Poland"*
- *"What skills do I need to become a DevOps engineer?"*
- *"Which technologies are trending in Poland right now?"*

---

## Tools

### Job search

| Tool | Description |
|------|-------------|
| `search_jobs` | Search IT jobs by keyword, city, salary range, experience level, contract type |
| `find_remote_jobs` | Remote-only positions, optional keyword and salary filter |
| `find_jobs_in_city` | Jobs in a specific Polish city (Warsaw, Krakow, Wroclaw, Gdansk, Poznan...) |
| `get_latest_jobs` | Newest job listings added to the board |

### Salary analysis

| Tool | Description |
|------|-------------|
| `get_salary_report` | Full salary report for a technology: median, p25/p75/p90, B2B vs UoP, by city, trend |
| `compare_salaries` | Side-by-side salary comparison of two technologies |
| `check_salary_fairness` | Assess whether a job offer salary is fair vs current market data |

### Market analytics

| Tool | Description |
|------|-------------|
| `get_top_technologies` | Technology ranking by active job count with monthly trend |
| `compare_roles` | Compare two IT roles: jobs count, salary, required skills, remote availability |
| `get_market_trends` | IT job market trends for 1m / 3m / 6m / 1y periods |
| `get_required_skills` | Must-have, nice-to-have, and differentiating skills for a role |
| `get_top_employers` | Companies with most active IT job listings, filterable by tech and city |

---

## Quick start

### Prerequisites

- Python 3.10+
- Redis (for caching)
- A jobs REST API backend (configure in `.env`)

### Install

```bash
git clone https://github.com/your-username/2hr-jobs-mcp-server.git
cd 2hr-jobs-mcp-server

python3 -m venv venv
source venv/bin/activate       # Linux/macOS
# .\venv\Scripts\activate      # Windows

pip install -r requirements.txt

cp .env.example .env
# Edit .env — set JOBS_API_URL, JOBS_API_KEY, REDIS_URL
```

### Run locally (stdio transport)

```bash
python server.py
```

### Run as HTTP server

```bash
python server_http.py
# Starts on http://0.0.0.0:8765
```

### Test with MCP Inspector

```bash
npx @modelcontextprotocol/inspector python server.py
# Opens http://localhost:5173 — call any tool interactively
```

---

## Claude Desktop integration

Edit the Claude Desktop config file:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "2hr-jobs": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/2hr-jobs-mcp-server/server.py"],
      "env": {
        "JOBS_API_URL": "https://api.2hr.pl/v1",
        "JOBS_API_KEY": "your_api_key",
        "REDIS_URL": "redis://localhost:6379/0"
      }
    }
  }
}
```

Restart Claude Desktop. The server appears in the tools panel — Claude will automatically call the right tool based on your questions.

---

## Cursor integration

Edit `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (per project):

```json
{
  "mcpServers": {
    "2hr-jobs": {
      "command": "python",
      "args": ["/path/to/server.py"],
      "env": {
        "JOBS_API_URL": "https://api.2hr.pl/v1",
        "JOBS_API_KEY": "your_api_key"
      }
    }
  }
}
```

In Cursor's Agent Mode (Ctrl+Shift+I), the tools are available automatically.

---

## Remote HTTP server (production)

For production use, configure the client with the remote URL:

```json
{
  "mcpServers": {
    "2hr-jobs-remote": {
      "url": "https://mcp.your-domain.com/sse",
      "transport": "sse"
    }
  }
}
```

---

## Docker deployment

```bash
cp .env.example .env
# Fill in JOBS_API_URL and JOBS_API_KEY

docker compose up -d

# Check status
docker compose ps
docker compose logs mcp-server
```

For HTTPS, use the included `nginx.conf` as a reverse proxy template with Let's Encrypt.

---

## Project structure

```
2hr-jobs-mcp-server/
├── server.py              # Entry point — stdio transport (Claude Desktop, Cursor)
├── server_http.py         # Entry point — HTTP/SSE transport (production)
├── api/
│   └── client.py          # Async httpx client for backend REST API
├── cache/
│   └── redis_cache.py     # Redis cache with cache-aside pattern
├── tools/
│   ├── search.py          # search_jobs, find_remote_jobs, find_jobs_in_city, get_latest_jobs
│   ├── salary.py          # get_salary_report, compare_salaries, check_salary_fairness
│   └── analytics.py       # get_top_technologies, compare_roles, get_market_trends, ...
├── resources/
│   └── documentation.py   # MCP Resources (API docs, market summary)
├── prompts/
│   └── templates.py       # MCP Prompts (job search assistant, salary negotiation)
├── security/
│   └── validators.py      # Input sanitization, rate limiting, injection detection
├── monitoring/
│   └── metrics.py         # Tool call tracking, latency monitoring
├── tests/
│   └── test_search.py     # Unit tests for validators and formatters
├── Dockerfile
├── docker-compose.yml
├── nginx.conf
└── .env.example
```

---

## Configuration

All settings via environment variables (copy `.env.example` to `.env`):

| Variable | Default | Description |
|----------|---------|-------------|
| `JOBS_API_URL` | — | Backend REST API base URL |
| `JOBS_API_KEY` | — | API authentication key |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `CACHE_TTL_JOBS` | `300` | Job listings cache TTL in seconds |
| `CACHE_TTL_SALARY` | `3600` | Salary reports cache TTL |
| `CACHE_TTL_ANALYTICS` | `1800` | Analytics cache TTL |
| `CACHE_TTL_TRENDS` | `3600` | Market trends cache TTL |
| `MCP_PORT` | `8765` | HTTP server port |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

---

## Running tests

```bash
pip install pytest pytest-asyncio
pytest tests/ -v
```

---

## Security features

- Input sanitization: SQL injection, XSS, path traversal detection via regex patterns
- Pydantic v2 validation with strict bounds on salary and limit parameters
- Redis-based rate limiting per client identifier
- Non-privileged `mcp` user in Docker container
- API key authentication between MCP server and backend API
- `fail open` on Redis errors — cache miss, not service failure

---

## Architecture

```
AI Client (Claude / Cursor)
         |
    MCP Protocol
    (stdio or HTTP/SSE)
         |
   MCP Server (Python)
   FastMCP + tools/salary/analytics
         |
   Redis Cache (TTL 5-60 min)
         |
   REST API (your backend)
         |
   Database (MySQL / PostgreSQL)
```

The MCP server is a stateless middleware layer — it holds no data of its own. All job and salary data lives in your existing backend, which the MCP server proxies through standardized tools.

---

## Data source

All data is powered by [2hr.pl](https://2hr.pl) — Polish IT job board aggregating thousands of IT job listings.

- Salaries in **PLN gross/month**
- Covers all major Polish cities: Warsaw, Krakow, Wroclaw, Gdansk, Gdynia, Poznan, Lodz, Katowice, Rzeszow, Szczecin
- Includes **remote** positions
- Data refreshed continuously

Read the full tutorial (Polish): [Jak zbudować serwer MCP w Pythonie dla portalu pracy](https://2hr.pl/blog/jak-zbudowac-serwer-mcp-python-portal-pracy-2026/)

---

## Related links

- [2hr.pl](https://2hr.pl) — Polish IT job board (data source)
- [Model Context Protocol spec](https://modelcontextprotocol.io) — MCP specification by Anthropic
- [FastMCP](https://github.com/jlowin/fastmcp) — High-level Python MCP SDK
- [MCP Inspector](https://github.com/modelcontextprotocol/inspector) — Interactive testing tool
- [Claude Desktop](https://claude.ai/download) — MCP-compatible AI client

---

## License

MIT — see [LICENSE](LICENSE)
