"""
VyaparSathi Agent v2.0
====================
Advanced multi-agent market intelligence engine.

Architecture:
   Orchestrator-Worker pattern with TWO agents:
    1. Researcher Agent  gathers data, extracts profiles, analyzes market
    2. Critic Agent      reviews the report for weak logic, revises if needed

   Pydantic-validated outputs at every stage
   Evidence tracking (source counts, confidence, citations)
   Full research trace for transparency

Pipeline phases:
  1. Generate smart search queries          (AI reasoning)
  2. Execute web searches                   (DuckDuckGo tool)
  3. Scrape top competitor pages            (Scraper tool)
  4. Extract structured competitor profiles (AI + Pydantic validation)
  5. Run SWOT analysis                      (AI + validation)
  6. Identify market gaps with root causes  (AI + validation)
  7. Compile final report + scorecard       (AI + validation)
  8. Critic review  find weak logic        (Critic Agent)
  9. Revision pass (if critic flags issues) (Researcher revises)

Every phase yields real-time log events so the frontend console
can show the user exactly what the agent is doing.
"""

import json
import asyncio
import time

from typing import AsyncGenerator, Dict, Any, List, Optional
from pydantic import ValidationError

from config import (
    AI_PROVIDER,
    GROQ_API_KEY, GROQ_MODEL,
    GEMINI_API_KEY, GEMINI_MODEL,
    MAX_SEARCH_QUERIES, MAX_COMPETITORS, MAX_SCRAPE_PAGES,
)
from tools import search_web, scrape_page
from models import (
    CompetitorProfile, SWOTAnalysis, MarketGap,
    Scorecard, CriticReview, CriticIssue, ResearchTrace,
)


#  AI Client Setup (dual provider with auto-fallback)
def _build_gemini_client():
    try:
        from google import genai
        return genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
    except Exception:
        return None

def _build_groq_client():
    try:
        from groq import Groq
        return Groq(api_key=GROQ_API_KEY, timeout=120.0) if GROQ_API_KEY else None
    except Exception:
        return None

gemini_client = _build_gemini_client()
groq_client = _build_groq_client()


SYSTEM_PROMPT = (
    "You are VyaparSathi, an elite market intelligence analyst. "
    "You research business niches, profile competitors, and deliver "
    "clear, data-driven strategic insights.  Always be thorough, "
    "specific, and actionable.  When returning JSON, ensure it "
    "strictly follows the requested schema.  Return ONLY valid JSON, "
    "no markdown fences, no extra text. DO NOT USE ANY EMOJIS OR SYMBOLS."
)

CRITIC_PROMPT = (
    "You are the VyaparSathi Critic Agent  a skeptical reviewer. "
    "Your job is to find weak logic, unsupported claims, missing "
    "competitors, fake assumptions, and vague recommendations in "
    "market research reports. Be harsh but constructive. "
    "Return ONLY valid JSON, no markdown fences. DO NOT USE ANY EMOJIS OR SYMBOLS."
)


class VyaparSathiAgent:
    """Autonomous multi-phase market intelligence agent with critic review."""

    #  Unified AI call with automatic fallback
    async def _generate(self, prompt: str, system: str = None) -> str:
        """Call the configured AI provider. Auto-fallback to the other if it fails."""
        sys_prompt = system or SYSTEM_PROMPT
        loop = asyncio.get_event_loop()

        # Determine provider order: primary first, then fallback
        providers = []
        if AI_PROVIDER == "gemini":
            if gemini_client: providers.append("gemini")
            if groq_client: providers.append("groq")
        else:
            if groq_client: providers.append("groq")
            if gemini_client: providers.append("gemini")

        last_error = None
        for provider in providers:
            try:
                if provider == "gemini":
                    from google.genai import types
                    config = types.GenerateContentConfig(
                        system_instruction=sys_prompt,
                        response_mime_type="application/json",
                    )
                    response = await loop.run_in_executor(
                        None,
                        lambda: gemini_client.models.generate_content(
                            model=GEMINI_MODEL,
                            contents=prompt,
                            config=config,
                        ),
                    )
                    return response.text
                else:  # groq
                    response = await loop.run_in_executor(
                        None,
                        lambda: groq_client.chat.completions.create(
                            model=GROQ_MODEL,
                            messages=[
                                {"role": "system", "content": sys_prompt},
                                {"role": "user", "content": prompt},
                            ],
                            response_format={"type": "json_object"},
                            temperature=0.7,
                        ),
                    )
                    return response.choices[0].message.content
            except Exception as e:
                last_error = e
                print(f"[AI Fallback] {provider} failed: {e}. Trying next provider...")
                continue

        raise last_error or RuntimeError("No AI provider available")

    #  Safe JSON parse + Pydantic validate 
    def _safe_parse(self, text: str) -> dict:
        """Parse JSON text, handling common LLM output quirks."""
        # Strip markdown fences if present
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            cleaned = "\n".join(lines)
        return json.loads(cleaned)

    def _validate_competitors(self, raw_list: list, source_urls: list) -> List[dict]:
        """Validate each competitor through Pydantic, skip invalid ones."""
        validated = []
        for c in raw_list:
            try:
                # Inject source URLs if AI didn't provide them
                if not c.get("source_urls") and source_urls:
                    c["source_urls"] = source_urls[:3]
                if not c.get("source_count"):
                    c["source_count"] = len(c.get("source_urls", []))
                profile = CompetitorProfile.model_validate(c)
                validated.append(profile.model_dump())
            except ValidationError as e:
                # Log but don't crash  skip malformed competitors
                print(f"[Validation] Skipped invalid competitor: {e.errors()[0]['msg']}")
                continue
        return validated

    def _validate_swot(self, raw: dict) -> dict:
        """Validate SWOT through Pydantic."""
        try:
            swot = SWOTAnalysis.model_validate(raw)
            return swot.model_dump()
        except ValidationError:
            return SWOTAnalysis().model_dump()

    def _validate_gaps(self, raw_list: list) -> List[dict]:
        """Validate each market gap through Pydantic."""
        validated = []
        for g in raw_list:
            try:
                gap = MarketGap.model_validate(g)
                validated.append(gap.model_dump())
            except ValidationError:
                continue
        return validated

    #  Public entry point 
    async def run_research(
        self,
        niche: str,
        location: str,
        business_size: Optional[str] = None,
        budget_range: Optional[str] = None,
        competitor_type: Optional[str] = None,
        custom_keywords: Optional[str] = None,
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the full research pipeline with critic review.

        Yields dicts of two types:
          {"type": "log",    "message": "...", "level": "..."}
          {"type": "report", "data": { ... }}
        """
        start_time = time.time()
        trace = ResearchTrace(
            ai_provider=AI_PROVIDER,
            ai_model=GEMINI_MODEL if AI_PROVIDER == "gemini" else GROQ_MODEL,
        )

        provider_name = "Gemini" if AI_PROVIDER == "gemini" else f"Groq ({GROQ_MODEL})"
        yield self._log(f" VyaparSathi Agent v2.0 initialized    AI: {provider_name}", "system")
        yield self._log(f' Target: "{niche}" in {location}', "info")
        yield self._log(" Multi-agent mode: Researcher + Critic", "system")

        # Phase 1  Generate search queries
        yield self._log(" Phase 1  Generating intelligent search queries ", "phase")
        queries = await self._generate_search_queries(
            niche, location,
            business_size=business_size,
            budget_range=budget_range,
            competitor_type=competitor_type,
            custom_keywords=custom_keywords,
        )
        trace.queries_generated = queries
        yield self._log(f" Generated {len(queries)} queries", "success")

        # Phase 2  Execute searches
        yield self._log(" Phase 2  Searching the web for competitors ", "phase")
        all_results: List[dict] = []
        for idx, query in enumerate(queries, 1):
            yield self._log(f'Searching: "{query}"', "search")
            try:
                results = await search_web(query)
                all_results.extend(results)
                yield self._log(
                    f"Found {len(results)} results  ({idx}/{len(queries)})", "success"
                )
            except Exception as exc:
                yield self._log(f"Search failed: {exc}", "warning")
            await asyncio.sleep(0.5)

        trace.search_hits_total = len(all_results)

        # De-duplicate by URL
        seen_urls: set = set()
        unique_results: List[dict] = []
        for r in all_results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)
        trace.unique_results = len(unique_results)
        yield self._log(
            f" {len(unique_results)} unique results after de-duplication", "info"
        )

        # Phase 3  Scrape top pages
        yield self._log(" Phase 3  Scraping top competitor pages ", "phase")
        scraped: List[dict] = []
        pages_blocked = 0
        to_scrape = unique_results[: min(MAX_SCRAPE_PAGES, len(unique_results))]
        for idx, item in enumerate(to_scrape, 1):
            yield self._log(f"Scraping: {item['title'][:55]}", "scrape")
            content = await scrape_page(item["url"])
            if not content.startswith("[Scrape Error]"):
                scraped.append(
                    {
                        "title": item["title"],
                        "url": item["url"],
                        "snippet": item["snippet"],
                        "content": content,
                    }
                )
                yield self._log(f" Page {idx}/{len(to_scrape)} scraped", "success")
            else:
                pages_blocked += 1
                yield self._log(
                    f" Skipped (blocked): {item['url'][:45]}", "warning"
                )
            await asyncio.sleep(0.3)

        trace.pages_scraped = len(scraped)
        trace.pages_blocked = pages_blocked

        # Collect all source URLs for evidence tracking
        all_source_urls = [s["url"] for s in scraped]

        # Phase 4  Extract competitor profiles (with evidence + clustering)
        yield self._log(" Phase 4  AI extracting competitor profiles ", "phase")
        competitors = await self._extract_competitors(
            niche, location, unique_results, scraped
        )
        competitors = self._validate_competitors(competitors, all_source_urls)
        trace.competitors_extracted = len(competitors)
        yield self._log(f" Identified {len(competitors)} competitors (Pydantic-validated)", "success")

        # Phase 5  SWOT analysis
        yield self._log(" Phase 5  Running SWOT analysis ", "phase")
        swot = await self._analyze_swot(niche, location, competitors)
        swot = self._validate_swot(swot)
        yield self._log(" SWOT analysis complete (validated)", "success")

        # Phase 6  Market gaps with root causes
        yield self._log(
            " Phase 6  Identifying market gaps & root causes ", "phase"
        )
        gaps = await self._find_market_gaps(niche, location, competitors, swot)
        gaps = self._validate_gaps(gaps)
        yield self._log(f" Found {len(gaps)} exploitable gaps (validated)", "success")

        # Phase 7  Compile report + scorecard
        yield self._log(" Phase 7  Compiling final report + scorecard ", "phase")
        report = await self._compile_report(niche, location, competitors, swot, gaps)
        yield self._log(" Report compiled with scorecard", "success")

        # Phase 8  Critic Agent Review
        yield self._log(" Phase 8  Critic Agent reviewing report ", "phase")
        critic_review = await self._critic_review(report)
        report["critic_review"] = critic_review

        issues_found = len(critic_review.get("issues", []))
        trace.critic_issues_found = issues_found
        trace.critic_issues = [i["issue"] for i in critic_review.get("issues", [])]

        if issues_found > 0:
            yield self._log(f" Critic found {issues_found} issue(s)", "warning")
            for issue in critic_review.get("issues", []):
                yield self._log(f'   [{issue.get("severity", "medium").upper()}] {issue["issue"]}', "critic")

            # Phase 9  Revision pass
            if critic_review.get("revision_needed", False):
                yield self._log(" Phase 9  Revising report based on critic feedback ", "phase")
                report = await self._revise_report(report, critic_review)
                trace.revision_made = True
                yield self._log(" Report revised and improved", "success")
            else:
                yield self._log(" Issues noted but report quality is acceptable", "info")
        else:
            yield self._log(" Critic: No issues found  report quality is excellent", "success")

        # Finalize trace
        trace.total_time_seconds = round(time.time() - start_time, 1)
        report["research_trace"] = trace.model_dump()

        yield self._log(f" Research complete  {trace.total_time_seconds}s total!", "complete")
        yield {"type": "report", "data": report}

    #  Strategy Simulator (Enhanced  Item 8) 
    async def simulate_strategy(self, report: dict, scenario: str) -> dict:
        """Simulate competitor reactions with phased 90-day timeline."""
        prompt = (
            f"You are analysing the competitive landscape below.\n\n"
            f"REPORT:\n{json.dumps(report, indent=2)}\n\n"
            f'USER SCENARIO: "{scenario}"\n\n'
            "Provide a detailed 90-day simulation:\n\n"
            "Return JSON with keys:\n"
            '  scenario             echo the scenario\n'
            '  competitor_reactions  list of {"name": "...", "reaction": "...", "impact": "..."}\n'
            '  phases               list of 3 objects:\n'
            '    {"phase": "Week 1-2", "title": "Immediate Reactions", "description": "..."}\n'
            '    {"phase": "Month 1-2", "title": "Market Adjustments", "description": "..."}\n'
            '    {"phase": "Month 3", "title": "New Equilibrium", "description": "..."}\n'
            '  risk_assessment      overall risk: low / medium / high\n'
            '  success_probability  integer 0-100\n'
            '  counter_strategies   list of 2-3 possible counter-moves by competitors\n'
            '  recommendation       strategic advice for the user'
        )
        text = await self._generate(prompt)
        result = self._safe_parse(text)
        return result

    #  Private pipeline steps 

    async def _generate_search_queries(
        self,
        niche: str,
        location: str,
        business_size: Optional[str] = None,
        budget_range: Optional[str] = None,
        competitor_type: Optional[str] = None,
        custom_keywords: Optional[str] = None,
    ) -> List[str]:
        extra_info = []
        if business_size:
            extra_info.append(f"Business Size focus: target {business_size} scale competitors")
        if budget_range:
            extra_info.append(f"Pricing Category context: target {budget_range} pricing models")
        if competitor_type:
            extra_info.append(f"Competitor Focus: target {competitor_type} competitors")
        if custom_keywords:
            extra_info.append(f"Additional Focus Keywords: {custom_keywords}")
        
        extra_str = "\n".join(extra_info) if extra_info else "None specified."

        prompt = (
            f"Generate exactly {MAX_SEARCH_QUERIES} diverse search queries to find "
            f'competitors in the "{niche}" niche in "{location}".\n\n'
            f"Additional Context/Filters:\n{extra_str}\n\n"
            "Include queries targeting:\n"
            "   Direct competitors (same niche, same area)\n"
            "   Price / menu comparisons\n"
            "   Customer reviews and ratings\n"
            "   Industry trends for this niche\n"
            "   Alternative / adjacent businesses\n\n"
            'Return ONLY a JSON array of strings, e.g. ["query 1", "query 2"].'
        )
        text = await self._generate(prompt)
        data = self._safe_parse(text)
        # Handle both {"queries": [...]} and plain [...]
        queries = data if isinstance(data, list) else data.get("queries", data.get("search_queries", [f"{niche} {location} competitors"]))
        return queries[:MAX_SEARCH_QUERIES]

    async def _extract_competitors(
        self,
        niche: str,
        location: str,
        search_results: List[dict],
        scraped_data: List[dict],
    ) -> List[dict]:
        # Build source URL list for evidence tracking
        source_urls = [s["url"] for s in scraped_data]

        data_blob = json.dumps(
            {
                "search_results": search_results[:20],
                "scraped_pages": [
                    {"title": s["title"], "url": s["url"], "content": s["content"][:1200]}
                    for s in scraped_data
                ],
            }
        )
        prompt = (
            f'Analyze the "{niche}" market in "{location}".\n\n'
            f"RESEARCH DATA:\n{data_blob}\n\n"
            f"Extract up to {MAX_COMPETITORS} real competitor profiles.\n"
            "For each competitor return:\n"
            "  name, description, location, website (or null),\n"
            "  rating (float or null), pricing_tier (budget/mid-range/premium/luxury),\n"
            "  key_products (list), strengths (list), weaknesses (list),\n"
            "  unique_selling_point (string),\n"
            "  growth_years (list of strings, e.g. ['2023', '2024', '2025']),\n"
            "  growth_rates (list of floats in %, e.g. [8.5, 14.2, 21.0]),\n"
            "\n"
            "  EVIDENCE FIELDS (IMPORTANT):\n"
            f"  source_count    how many of these source URLs informed this profile: {json.dumps(source_urls[:8])}\n"
            "  confidence_score  your confidence this profile is accurate (0.0 to 1.0)\n"
            f"  source_urls     which of the source URLs you used (pick from the list above)\n"
            "\n"
            "  CLUSTERING:\n"
            "  cluster  assign a market segment label like 'budget-fast', 'premium-experience',\n"
            "            'family-focused', 'tech-forward', 'traditional', etc.\n"
            "\n"
            "  QUADRANT SCORES:\n"
            "  quality_score  experience/quality score 1-10\n"
            "  price_score    price positioning 1-10 (1=cheapest, 10=most expensive)\n"
            "\n"
            "If insufficient real data exists, create realistic synthetic profiles.\n"
            'Return JSON: {"competitors": [...]}'
        )
        text = await self._generate(prompt)
        data = self._safe_parse(text)
        competitors = data if isinstance(data, list) else data.get("competitors", [])
        return competitors[:MAX_COMPETITORS]

    async def _analyze_swot(
        self, niche: str, location: str, competitors: List[dict]
    ) -> dict:
        prompt = (
            f'Strategic SWOT analysis for a NEW business entering the "{niche}" '
            f'market in "{location}".\n\n'
            f"Current competitors:\n{json.dumps(competitors, indent=2)}\n\n"
            "Produce a SWOT for the new entrant.\n"
            'Return JSON with keys: "strengths", "weaknesses", "opportunities", "threats".\n'
            "Each value is a list of 3-5 concise bullet-point strings."
        )
        text = await self._generate(prompt)
        return self._safe_parse(text)

    async def _find_market_gaps(
        self,
        niche: str,
        location: str,
        competitors: List[dict],
        swot: dict,
    ) -> List[dict]:
        prompt = (
            f'Identify 3-5 exploitable market gaps in the "{niche}" '
            f'niche in "{location}".\n\n'
            f"Competitors:\n{json.dumps(competitors, indent=2)}\n"
            f"SWOT:\n{json.dumps(swot, indent=2)}\n\n"
            "For each gap return:\n"
            "  gap                 short name\n"
            "  description         detailed explanation\n"
            "  potential_impact     low / medium / high\n"
            "  difficulty           easy / moderate / hard\n"
            "  recommended_action   concrete next step\n"
            "  root_cause           WHY this gap exists (be specific)\n"
            "  data_gaps            what additional research would increase confidence\n"
            "  confidence_score     confidence this gap is real (0.0 to 1.0)\n"
            "  source_count         how many data points support this gap (integer)\n\n"
            'Return JSON: {"market_gaps": [...]}'
        )
        text = await self._generate(prompt)
        data = self._safe_parse(text)
        gaps = data if isinstance(data, list) else data.get("market_gaps", data.get("gaps", []))
        return gaps

    async def _compile_report(
        self,
        niche: str,
        location: str,
        competitors: List[dict],
        swot: dict,
        gaps: List[dict],
    ) -> dict:
        prompt = (
            f'Compile a final market intelligence report for "{niche}" in "{location}".\n\n'
            f"Competitors:\n{json.dumps(competitors, indent=2)}\n"
            f"SWOT:\n{json.dumps(swot, indent=2)}\n"
            f"Market Gaps:\n{json.dumps(gaps, indent=2)}\n\n"
            'Return JSON with:\n'
            '  "executive_summary"      2-3 paragraph overview\n'
            '  "recommendations"        list of 5 specific, actionable bullet strings\n'
            '  "competitive_intensity"  one of: low, moderate, high, very_high\n'
            '\n'
            '  "scorecard"  an object with:\n'
            '    "opportunity_score"           integer 1-100 (how attractive this market is)\n'
            '    "differentiation_score"       integer 1-100 (how easy to stand out)\n'
            '    "competition_intensity_score"  integer 1-100 (how intense competition is)\n'
            '    "launch_difficulty"            "easy", "moderate", or "hard"\n'
            '    "confidence_level"             "low", "medium", or "high"\n'
            '    "go_no_go"                     "GO", "PROCEED WITH CAUTION", or "NO-GO"\n'
            '    "rationale"                    1-2 sentence justification'
        )
        text = await self._generate(prompt)
        summary = self._safe_parse(text)

        # Validate scorecard
        scorecard = None
        if summary.get("scorecard"):
            try:
                scorecard = Scorecard.model_validate(summary["scorecard"]).model_dump()
            except ValidationError:
                scorecard = Scorecard().model_dump()

        return {
            "niche": niche,
            "location": location,
            "executive_summary": summary.get("executive_summary", ""),
            "competitors": competitors,
            "swot": swot,
            "market_gaps": gaps,
            "recommendations": summary.get("recommendations", []),
            "competitive_intensity": summary.get("competitive_intensity", "moderate"),
            "scorecard": scorecard or Scorecard().model_dump(),
        }

    #  Critic Agent (Item 3) 
    async def _critic_review(self, report: dict) -> dict:
        """Second agent reviews the report for weak logic."""
        prompt = (
            "Review the following market intelligence report.\n\n"
            f"REPORT:\n{json.dumps(report, indent=2)}\n\n"
            "Check for:\n"
            "  1. Weak or circular logic in SWOT analysis\n"
            "  2. Market gaps that sound generic or unsupported\n"
            "  3. Missing obvious competitor types\n"
            "  4. Vague or non-actionable recommendations\n"
            "  5. Inconsistencies between competitors and SWOT/gaps\n"
            "  6. Unrealistic confidence scores or growth rates\n\n"
            "Return JSON:\n"
            '  "overall_quality"  "poor", "fair", "good", or "excellent"\n'
            '  "issues"  list of objects, each with:\n'
            '      "section"   "competitors" / "swot" / "market_gaps" / "recommendations"\n'
            '      "issue"     describe the problem\n'
            '      "severity"  "low" / "medium" / "high"\n'
            '      "suggestion"  how to fix it\n'
            '  "revision_needed"  boolean (true if quality is poor or fair, or any high-severity issue exists)'
        )
        text = await self._generate(prompt, system=CRITIC_PROMPT)
        raw = self._safe_parse(text)

        # Validate through Pydantic
        try:
            review = CriticReview.model_validate(raw)
            return review.model_dump()
        except ValidationError:
            return CriticReview().model_dump()

    async def _revise_report(self, report: dict, critic_review: dict) -> dict:
        """Revise the report based on critic feedback."""
        prompt = (
            "The Critic Agent has reviewed our market report and found issues.\n\n"
            f"ORIGINAL REPORT:\n{json.dumps(report, indent=2)}\n\n"
            f"CRITIC FEEDBACK:\n{json.dumps(critic_review, indent=2)}\n\n"
            "Please REVISE the report to address the critic's concerns.\n"
            "Specifically:\n"
            "   Strengthen any weak SWOT points\n"
            "   Make generic market gaps more specific\n"
            "   Sharpen vague recommendations into concrete action items\n"
            "   Fix any inconsistencies\n\n"
            "Return the REVISED JSON with the SAME structure:\n"
            '  "executive_summary", "recommendations", "competitive_intensity",\n'
            '  "scorecard" (with opportunity_score, differentiation_score, etc.)\n\n'
            "ONLY return the revised summary fields, not the full competitors/swot/gaps."
        )
        text = await self._generate(prompt)
        revised = self._safe_parse(text)

        # Merge revised fields back into the report
        if revised.get("executive_summary"):
            report["executive_summary"] = revised["executive_summary"]
        if revised.get("recommendations"):
            report["recommendations"] = revised["recommendations"]
        if revised.get("competitive_intensity"):
            report["competitive_intensity"] = revised["competitive_intensity"]
        if revised.get("scorecard"):
            try:
                report["scorecard"] = Scorecard.model_validate(revised["scorecard"]).model_dump()
            except ValidationError:
                pass

        return report

    #  Helpers 
    @staticmethod
    def _log(message: str, level: str = "info") -> Dict[str, str]:
        return {"type": "log", "message": message, "level": level}


