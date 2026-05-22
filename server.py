import os
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from modules import InterviewConductor, InterviewScorer

app = FastAPI()

# Allow CORS for local development if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize modules
conductor = InterviewConductor()
scorer = InterviewScorer()

# Default profiles for demo
DEFAULT_ICP = {
    "icp_type": "high_wage",
    "target_role": "Frontend Developer",
    "round_type": "technical",
    "company_tier": "enterprise",
    "language": "en"
}

DEFAULT_HIRING_BAR = {
    "communication": 80,
    "technical": 85,
    "problem_solving": 80,
    "behavioral": 75,
    "delivery": 80
}

class ConductRequest(BaseModel):
    previous_qa_pairs: List[Dict[str, str]]
    icp_profile: Optional[Dict[str, str]] = None

class ScoreRequest(BaseModel):
    full_transcript: List[Dict[str, str]]
    icp_profile: Optional[Dict[str, str]] = None
    hiring_bar: Optional[Dict[str, int]] = None

@app.post("/api/conduct")
async def api_conduct(request: ConductRequest):
    icp = request.icp_profile or DEFAULT_ICP
    
    question_data = conductor.generate_next_question(
        icp_type=icp["icp_type"],
        target_role=icp["target_role"],
        round_type=icp["round_type"],
        company_tier=icp["company_tier"],
        language=icp["language"],
        previous_qa_pairs=request.previous_qa_pairs
    )
    return question_data

@app.post("/api/score")
async def api_score(request: ScoreRequest):
    icp = request.icp_profile or DEFAULT_ICP
    bar = request.hiring_bar or DEFAULT_HIRING_BAR
    
    score_report = scorer.score_interview(
        full_transcript=request.full_transcript,
        icp_type=icp["icp_type"],
        target_role=icp["target_role"],
        round_type=icp["round_type"],
        hiring_bar=bar
    )
    return score_report

# Mount the static web folder so the frontend can be served at root
app.mount("/", StaticFiles(directory="web", html=True), name="web")

if __name__ == "__main__":
    import uvicorn
    # Make sure to run this via `python server.py`
    print("Starting server at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
