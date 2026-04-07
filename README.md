# Twain Outbound — Cold Email Campaign Pipeline

Orchestrate cold email campaigns using **Twain** (personalized copy), **Apollo** (lead enrichment), and **Email Bison** (sending & sequencing).

## Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your actual API keys
```

### 3. Connect MCP servers (for Claude Code)

**Twain MCP** (already configured in `.mcp.json`):
```bash
claude mcp add --transport http twain https://mcp.api.twain.ai --header "X-Api-Key: YOUR_TWAIN_API_KEY"
```

**Apollo MCP** (via plugin):
```bash
# In Claude Code:
/plugin marketplace add apolloio/apollo-mcp-plugin
/plugin install apollo@apollo-plugin-marketplace
# Then authenticate: /mcp -> Apollo -> Authenticate
```

## Usage

### Option A: Interactive (Recommended) — Claude Code + MCP

Run Claude Code in this project directory. With Apollo and Twain MCPs connected, tell Claude:

> "Load my leads from data/leads.csv. Use Apollo to enrich any missing contact info.
> Then use Twain to write a personalized cold email for each lead about [your product/service].
> Finally, push everything to Email Bison as a campaign called 'Q2 Outreach'."

Claude will use Apollo MCP to enrich leads, Twain MCP to generate per-contact copy, and the Python scripts to push to Email Bison.

### Option B: Standalone Python scripts

```bash
# Dry run (preview copy without sending)
python run_campaign.py \
  --csv data/leads.csv \
  --campaign "Q2 Outreach" \
  --context "We help B2B SaaS companies increase demo bookings by 3x" \
  --mode template \
  --dry-run

# Live run with Twain API
python run_campaign.py \
  --csv data/leads.csv \
  --campaign "Q2 Outreach" \
  --context "We help B2B SaaS companies increase demo bookings by 3x" \
  --mode twain_api \
  --sender-email-ids "1,2,3"
```

### CSV format

Place your leads CSV in `data/`. Required column: `email`. Optional columns:

| Column | Description |
|--------|-------------|
| `email` | **(required)** Contact email |
| `first_name` | First name |
| `last_name` | Last name |
| `company` | Company name |
| `domain` | Company domain |
| `title` | Job title |
| `linkedin_url` | LinkedIn profile URL |
| `phone` | Phone number |

## Project structure

```
├── .mcp.json              # MCP server config (Apollo + Twain)
├── .env.example           # API key template
├── .gitignore
├── requirements.txt
├── run_campaign.py        # Main orchestrator script
├── data/                  # Place your CSV files here
└── src/
    ├── config.py          # Environment config loader
    ├── lead_loader.py     # CSV lead loader & normalizer
    ├── copy_generator.py  # Twain API + template fallback
    └── emailbison_client.py  # Email Bison REST API client
```

## API References

- [Email Bison API Docs](https://docs.emailbison.com/get-started/introduction)
- [Email Bison API Reference](https://dedi.emailbison.com/api/reference)
- [Apollo MCP Plugin](https://github.com/apolloio/apollo-mcp-plugin)
- [Twain.ai](https://www.twain.ai/)
