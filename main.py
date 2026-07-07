"""
VyaparSathi â€“ FastAPI Backend Server
=================================
Serves the frontend, exposes the agent research pipeline as a
streaming SSE endpoint, and handles the strategy simulator.

Endpoints:
  GET  /                    â†’ serve the frontend
  POST /api/research        â†’ start research (returns SSE stream)
  GET  /api/report/{id}     â†’ retrieve a completed report
  POST /api/simulate        â†’ run a strategy simulation
"""

import asyncio
import json
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from models import ResearchRequest, SimulationRequest
from agent import VyaparSathiAgent
from config import HOST, PORT


# â”€â”€ App setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app = FastAPI(
    title="VyaparSathi",
    description="AI-Powered Autonomous Competitor Intelligence Agent",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory stores (sufficient for a demo / capstone)
reports: Dict[str, dict] = {}

agent = VyaparSathiAgent()


# â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/")
async def serve_index():
    """Serve the main single-page application."""
    return FileResponse("static/index.html")


@app.post("/api/research")
async def start_research(request: ResearchRequest):
    """
    Launch the VyaparSathi research pipeline.

    Returns a Server-Sent Events stream so the frontend can
    render the agent's reasoning in real-time.  The final event
    contains the full report JSON.
    """
    task_id = str(uuid.uuid4())

    async def event_stream():
        try:
            async for event in agent.run_research(
                niche=request.niche,
                location=request.location,
                business_size=request.business_size,
                budget_range=request.budget_range,
                competitor_type=request.competitor_type,
                custom_keywords=request.custom_keywords,
            ):
                if event["type"] == "report":
                    # Persist report so it can be fetched later
                    reports[task_id] = event["data"]
                # Send every event (logs AND report) to the client
                yield f"data: {json.dumps(event)}\n\n"
                await asyncio.sleep(0.05)
        except Exception as exc:
            error_event = {"type": "error", "message": str(exc)}
            yield f"data: {json.dumps(error_event)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Task-Id": task_id,
            "X-Accel-Buffering": "no",   # disable nginx buffering
        },
    )


@app.get("/api/report/{task_id}")
async def get_report(task_id: str):
    """Retrieve a previously completed research report."""
    if task_id not in reports:
        raise HTTPException(status_code=404, detail="Report not found")
    return reports[task_id]


@app.post("/api/simulate")
async def simulate_strategy(request: SimulationRequest):
    """
    Run a 'what-if' strategy simulation against the competitive
    landscape from an earlier research report.
    """
    if request.task_id not in reports:
        raise HTTPException(
            status_code=404,
            detail="Report not found. Please run a research task first.",
        )
    report = reports[request.task_id]
    result = await agent.simulate_strategy(report, request.scenario)
    return result


# â”€â”€ Static file mount (CSS / JS) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app.mount("/static", StaticFiles(directory="static"), name="static")


# â”€â”€ Direct execution â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=int(PORT), reload=True)


