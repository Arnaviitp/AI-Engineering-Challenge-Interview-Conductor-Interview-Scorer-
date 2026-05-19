import json
import os
import anthropic
from typing import List, Dict, Any

class InterviewConductor:
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        # Using the exact model string required by the challenge rules
        self.model = "claude-sonnet-4-20250514"

    def generate_next_question(
        self, 
        icp_type: str, 
        target_role: str, 
        round_type: str, 
        company_tier: str, 
        language: str, 
        previous_qa_pairs: List[Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        Generates the next interview question adaptively based on the context and previous answers.
        """
        prompt = f"""You are an expert AI Interview Conductor. Your task is to conduct a live mock interview.
You will generate the NEXT question for the candidate based on their profile and the previous questions and answers.

Candidate Profile:
- ICP Type: {icp_type}
- Target Role: {target_role}
- Round Type: {round_type}
- Company Tier: {company_tier}
- Language: {language}

Previous QA Pairs:
{json.dumps(previous_qa_pairs, indent=2, ensure_ascii=False)}

Instructions:
1. Adapt to the previous answer. If the candidate showed strength, ask a harder extension question or move to a new topic. If they showed weakness or gap, ask a simpler follow-up probing the same gap. If there are no previous answers, start with an appropriate introductory technical/behavioral question.
2. The language of the question MUST be '{language}'. If 'hi', use natural conversational Hindi. If 'en', use English.
3. You MUST return ONLY a JSON object with the following schema:
{{
  "next_question": "the question text",
  "question_type": "technical" | "behavioral" | "follow_up",
  "difficulty_level": <integer from 1 to 5>,
  "reasoning": "explanation of why this question was chosen based on the previous answer (or profile if first question)"
}}

Output ONLY the raw JSON without any markdown formatting, backticks, or extra text. Do not wrap the JSON in ```json blocks.
"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1000,
            temperature=0.7,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text.strip()
        # Clean up in case the LLM returned markdown despite instructions
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from Conductor. Raw Response: {content}")
            raise e


class InterviewScorer:
    def __init__(self, api_key: str = None):
        self.client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))
        # Using the exact model string required by the challenge rules
        self.model = "claude-sonnet-4-20250514"

    def score_interview(
        self, 
        full_transcript: List[Dict[str, str]], 
        icp_type: str, 
        target_role: str, 
        round_type: str, 
        hiring_bar: Dict[str, int]
    ) -> Dict[str, Any]:
        """
        Scores the full interview transcript against the hiring bar and provides specific feedback.
        """
        prompt = f"""You are an expert AI Interview Scorer. Evaluate the candidate based on the provided interview transcript.

Interview Details:
- ICP Type: {icp_type}
- Target Role: {target_role}
- Round Type: {round_type}
- Hiring Bar: {json.dumps(hiring_bar)}

Transcript:
{json.dumps(full_transcript, indent=2, ensure_ascii=False)}

Instructions:
1. Provide an honest, objective evaluation.
2. Evaluate across 5 axes: communication, technical, problem_solving, behavioral, delivery. Score each from 0-100.
3. Calculate gap_vs_bar for each axis: (user_score - hiring_bar). THIS MUST BE A NEGATIVE NUMBER IF THE SCORE IS BELOW THE BAR. Do not soften this.
4. Extract exactly one weak_moment and one strong_moment. You MUST quote the EXACT text from the candidate's answers in the transcript. Invented quotes will result in failure.
5. You MUST return ONLY a JSON object with the following schema:
{{
  "overall_score": <int 0-100>,
  "scores_per_axis": {{
    "communication": <int>,
    "technical": <int>,
    "problem_solving": <int>,
    "behavioral": <int>,
    "delivery": <int>
  }},
  "gap_vs_bar": {{
    "communication": <int>,
    "technical": <int>,
    "problem_solving": <int>,
    "behavioral": <int>,
    "delivery": <int>
  }},
  "weak_moment": {{
    "timestamp_approx": "e.g., Turn 2",
    "quote": "EXACT substring from the candidate's answer transcript",
    "why_it_hurt": "reason"
  }},
  "strong_moment": {{
    "quote": "EXACT substring from the candidate's answer transcript",
    "why_it_helped": "reason"
  }},
  "next_action": "1 specific drill recommendation"
}}

Output ONLY the raw JSON without any markdown formatting, backticks, or extra text. Do not wrap the JSON in ```json blocks.
"""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            temperature=0.3,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        content = response.content[0].text.strip()
        # Clean up in case the LLM returned markdown despite instructions
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        try:
            return json.loads(content.strip())
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON from Scorer. Raw Response: {content}")
            raise e
