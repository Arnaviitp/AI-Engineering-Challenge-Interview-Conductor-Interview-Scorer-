# AI Engineering Challenge - Group 4

## Interview Conductor + Interview Scorer

This repository contains the Proof of Concept (POC) for the AI Engineering Challenge (Group 4) building an Interview Conductor and an Interview Scorer.

### Project Structure
- `modules.py`: Contains `InterviewConductor` and `InterviewScorer` classes defining the core logic and prompts for adaptive interviewing and exact-quote-based transcript scoring.
- `demo.py`: A mini end-to-end demo script that runs both modules in succession for 3 turns on mock candidate profiles (one high-wage English SWE, and one low-wage Hindi CX associate).

### Requirements
- Python 3.8+
- Anthropic API Key (The challenge requires `claude-sonnet-4-20250514`. This model string is hardcoded inside `modules.py` as requested).

## Setup & Run (Under 2 Minutes)

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your API Key:**
   Create a `.env` file in the root directory and add your OpenRouter API key:
   ```
   OPENROUTER_API_KEY=sk-or-your-key-here
   ```
   *(Alternatively, export it in your terminal)*

3. **Run the Demonstration:**
   ```bash
   python demo.py
   ```

### Architecture Highlights
- **Module A (Conductor)**: Takes in context and previous QA pairs to dynamically output the next question with varying difficulty and question type (technical, behavioral, follow_up). It strictly outputs JSON.
- **Module B (Scorer)**: Evaluates across 5 specific axes against a numerical hiring bar. Gap logic is enforced: `(user_score - hiring_bar)`. It extracts literal quotes directly from the candidate transcripts without hallucination to highlight strong and weak moments.