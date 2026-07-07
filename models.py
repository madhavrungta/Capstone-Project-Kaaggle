"""
VyaparSathi Data Models
====================
Pydantic schemas that enforce strict structure on all agent outputs.
These schemas are used for validation after every AI call, ensuring
the frontend dashboard never breaks due to malformed JSON.

Includes:
   CompetitorProfile  ” with evidence fields & clustering
   SWOTAnalysis       ” standard framework
   MarketGap          ” with root-cause analysis & data gaps
   Scorecard          ” final Go/No-Go market assessment
   CriticReview       ” output of the Critic agent
   ResearchTrace      ” full pipeline transparency log
   ResearchReport     ” the complete intelligence package
"""

from pydantic import BaseModel, Field
from typing import List, Optional


# Competitor Profile 
class CompetitorProfile(BaseModel):
    """A single competitor extracted from research data."""
    name: str = Field(description="Business name")
    description: str = Field(description="One-line description of the business")
    location: str = Field(description="Business address or area")
    website: Optional[str] = Field(default=None, description="Website URL if found")
    rating: Optional[float] = Field(default=None, description="Customer rating out of 5")
    pricing_tier: str = Field(default="mid-range", description="One of: budget, mid-range, premium, luxury")
    key_products: List[str] = Field(default_factory=list, description="Main products or services offered")
    strengths: List[str] = Field(default_factory=list, description="Competitive advantages")
    weaknesses: List[str] = Field(default_factory=list, description="Identified weaknesses or gaps")
    unique_selling_point: str = Field(default="", description="What sets this competitor apart")
    growth_years: List[str] = Field(default=["2023", "2024", "2025"], description="Years of historical records")
    growth_rates: List[float] = Field(default=[0.0, 0.0, 0.0], description="Growth rates per year (%)")

    # Evidence fields (Items 4 & 10)
    source_count: int = Field(default=0, description="Number of data sources used to build this profile")
    confidence_score: float = Field(default=0.5, description="Confidence in accuracy (0.0 to 1.0)")
    source_urls: List[str] = Field(default_factory=list, description="URLs used as evidence")
    cluster: str = Field(default="general", description="Market cluster, e.g. budget-fast, premium-experience, family-focused")

    # Quality scores for quadrant chart (Item 7)
    quality_score: float = Field(default=5.0, description="Quality/experience score 1-10")
    price_score: float = Field(default=5.0, description="Price positioning score 1-10 (1=cheapest, 10=most expensive)")


#  SWOT Analysis 
class SWOTAnalysis(BaseModel):
    """SWOT framework for a new market entrant."""
    strengths: List[str] = Field(default_factory=list, description="Internal strengths for a new entrant")
    weaknesses: List[str] = Field(default_factory=list, description="Internal challenges a new entrant faces")
    opportunities: List[str] = Field(default_factory=list, description="External market opportunities")
    threats: List[str] = Field(default_factory=list, description="External threats and risks")


#  Market Gap 
class MarketGap(BaseModel):
    """A single exploitable gap in the competitive landscape."""
    gap: str = Field(description="Short name for the gap")
    description: str = Field(description="Detailed explanation")
    potential_impact: str = Field(default="medium", description="Revenue potential: low, medium, or high")
    difficulty: str = Field(default="moderate", description="Difficulty to exploit: easy, moderate, or hard")
    recommended_action: str = Field(default="", description="Concrete next step")

    # Evidence & depth fields (Items 4 & 11)
    source_count: int = Field(default=0, description="Number of sources supporting this gap")
    confidence_score: float = Field(default=0.5, description="Confidence this gap is real (0.0 to 1.0)")
    root_cause: str = Field(default="", description="Why this gap exists in the market")
    data_gaps: str = Field(default="", description="What additional data would increase confidence")


#  Final Scorecard (Item 5) 
class Scorecard(BaseModel):
    """Aggregated market assessment scores."""
    opportunity_score: int = Field(default=50, description="Overall opportunity rating 1-100")
    differentiation_score: int = Field(default=50, description="How easy to differentiate 1-100")
    competition_intensity_score: int = Field(default=50, description="How intense competition is 1-100")
    launch_difficulty: str = Field(default="moderate", description="easy, moderate, or hard")
    confidence_level: str = Field(default="medium", description="low, medium, or high based on data quality")
    go_no_go: str = Field(default="PROCEED WITH CAUTION", description="GO, PROCEED WITH CAUTION, or NO-GO")
    rationale: str = Field(default="", description="Brief justification for the recommendation")


#  Critic Review (Item 3) 
class CriticIssue(BaseModel):
    """A single issue identified by the Critic agent."""
    section: str = Field(description="Which section has the issue: competitors, swot, market_gaps, recommendations")
    issue: str = Field(description="Description of the problem")
    severity: str = Field(default="medium", description="low, medium, or high")
    suggestion: str = Field(default="", description="How to fix it")


class CriticReview(BaseModel):
    """Output of the Critic agent's review."""
    overall_quality: str = Field(default="good", description="poor, fair, good, excellent")
    issues: List[CriticIssue] = Field(default_factory=list, description="List of issues found")
    revision_needed: bool = Field(default=False, description="Whether the report needs revision")


#  Research Trace (Item 6) 
class ResearchTrace(BaseModel):
    """Full pipeline transparency log."""
    queries_generated: List[str] = Field(default_factory=list)
    search_hits_total: int = Field(default=0)
    unique_results: int = Field(default=0)
    pages_scraped: int = Field(default=0)
    pages_blocked: int = Field(default=0)
    competitors_extracted: int = Field(default=0)
    critic_issues_found: int = Field(default=0)
    critic_issues: List[str] = Field(default_factory=list)
    revision_made: bool = Field(default=False)
    total_time_seconds: float = Field(default=0.0)
    ai_provider: str = Field(default="")
    ai_model: str = Field(default="")


#  Full Research Report 
class ResearchReport(BaseModel):
    """The complete intelligence report returned to the frontend."""
    niche: str
    location: str
    executive_summary: str = Field(default="")
    competitors: List[CompetitorProfile] = Field(default_factory=list)
    swot: SWOTAnalysis = Field(default_factory=SWOTAnalysis)
    market_gaps: List[MarketGap] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    competitive_intensity: str = Field(default="moderate", description="low, moderate, high, or very_high")

    # New fields
    scorecard: Optional[Scorecard] = Field(default=None, description="Final market scorecard")
    research_trace: Optional[ResearchTrace] = Field(default=None, description="Pipeline transparency log")
    critic_review: Optional[CriticReview] = Field(default=None, description="Critic agent's assessment")


#  API Request / Response Bodies 
class ResearchRequest(BaseModel):
    """Incoming request to start a research task."""
    niche: str = Field(min_length=2, description="Business niche to research")
    location: str = Field(min_length=2, description="Geographic location")
    business_size: Optional[str] = Field(default=None, description="Business size: small, medium, or large")
    budget_range: Optional[str] = Field(default=None, description="Budget range")
    competitor_type: Optional[str] = Field(default=None, description="Competitor type: direct, indirect, both")
    custom_keywords: Optional[str] = Field(default=None, description="Additional keywords for the search")


class SimulationRequest(BaseModel):
    """Request to simulate a strategic business scenario."""
    task_id: str
    scenario: str = Field(description='Hypothetical move, e.g. "Lower prices by 20%"')


class SimulationResponse(BaseModel):
    """Agent's analysis of a simulated scenario."""
    scenario: str
    competitor_reactions: List[dict] = Field(default_factory=list)
    risk_assessment: str = Field(default="medium")
    recommendation: str = Field(default="")
    # Enhanced simulator fields (Item 8)
    phases: List[dict] = Field(default_factory=list, description="Phased timeline predictions")
    success_probability: int = Field(default=50, description="Estimated success rate 0-100")
    counter_strategies: List[str] = Field(default_factory=list, description="Possible counter-moves")

