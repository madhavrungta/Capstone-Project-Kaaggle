# VyaparSathi v2.0 — Autonomous Multi-Agent Market Intelligence

> **Kaggle 5-Day AI Agents: Intensive Vibe Coding Capstone Project**
> Track: Agents for Business / Freestyle

VyaparSathi is a verifiable, autonomous multi-agent system that researches any business niche and location, profiles competitors with evidence-backed data, identifies market gaps, and predicts strategic outcomes. It features a transparent **9-Phase Pipeline** governed by a strict **Critic Agent** that reviews and revises the primary agent's work.

## Key Features (v2.0)

| Feature | Description |
|---|---|
| **Critic Agent Self-Correction** | A secondary LLM pass acts as a skeptic. It reviews the generated SWOT and gaps for weak logic or unsupported claims, forcing a revision (Phase 8/9) if the quality isn't up to par. |
| **Evidence-Backed Outputs** | Eradicates hallucinations. Every competitor profile shows a `confidence_score` and exact `source_count`. Market Gaps include `root_cause` and `data_gaps`. |
| **Market Scorecard & Go/No-Go** | Generates an executive summary complete with Opportunity, Differentiation, and Competition Intensity scores, delivering a final Go / Proceed with Caution / No-Go decision. |
| **Price vs. Quality Quadrant** | Automatically clusters competitors and plots them on a dynamic Chart.js scatter grid to visualize "empty space" in the market. |
| **Agent Trace Transparency** | A dedicated UI pane that shows exactly how many queries were generated, pages scraped, and critic issues found. |
| **90-Day Strategy Simulator** | Enter a hypothetical business move, and the agent predicts a phased 90-day timeline of competitor reactions, risk, and success probability. |

## Tech Stack

- **Backend:** Python, FastAPI, Uvicorn
- **AI Engine:** Google Gemini & Groq (Reasoning + Structured Outputs)
- **Search & Scrape:** DuckDuckGo + httpx + BeautifulSoup4
- **Data Validation:** Strict Pydantic v2 schemas for all JSON parsing
- **Frontend:** Vanilla HTML / CSS / JS (Dynamic dashboards, SVG Ring Charts, Chart.js)

## Quick Start

### 1. Clone & Install

```bash
cd "Capstone project"
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env and add your preferred API keys:
#   GROQ_API_KEY=your_groq_key
#   GEMINI_API_KEY=your_gemini_key
#   AI_PROVIDER=groq  # or 'gemini'
```

### 3. Run

```bash
python main.py
```

Open **http://localhost:8000** in your browser.

## Multi-Agent Architecture

```
User Input --> FastAPI --> Orchestrator
                               |
               +-------------------------------+
               | Phase 1: Smart Query Gen      | <-- reasoning
               | Phase 2: Web Search           | <-- DDG tool
               | Phase 3: Page Scrape          | <-- httpx/BS4
               | Phase 4: Extraction           | <-- structured output + evidence
               | Phase 5: SWOT Analysis        |
               | Phase 6: Market Gaps          | <-- root cause analysis
               | Phase 7: Report & Scorecard   |
               |-------------------------------|
               | Phase 8: CRITIC REVIEW        | <-- skeptic agent checks logic
               | Phase 9: REVISION PASS        | <-- fixes issues found
               +-------------------------------+
                               |
                   SSE Stream --> Frontend UI
```

## Project Structure

```
Capstone project/
  main.py            # FastAPI server + SSE endpoints
  agent.py           # Multi-agent research pipeline (Researcher + Critic)
  models.py          # Pydantic v2 data schemas
  tools.py           # Web search (DuckDuckGo) + page scraper
  config.py          # Environment config loader
  requirements.txt   # Python dependencies
  .env.example       # Template for API keys
  run.bat            # Windows quick-start script
  static/
    index.html       # Single-page dashboard UI
    app.js           # Frontend logic (SSE, charts, rendering)
    styles.css       # Full CSS design system
```

## License

MIT — built for the Kaggle AI Agents Capstone 2026.
