import json
import os
import requests
from typing import List, Dict, Any

def _call_llm_with_fallback(prompt: str, temperature: float = 0.7, max_tokens: int = 1500) -> str:
    """
    Calls LLM with fallback mechanism.
    1. Groq (llama3-70b-8192)
    2. Google Gemini (gemini-1.5-flash via Google API)
    3. OpenRouter (anthropic/claude-3-haiku)
    """
    groq_api_key = os.environ.get("GROQ_API_KEY")
    google_api_key = os.environ.get("GOOGLE_API_KEY")
    or_api_key = os.environ.get("OPENROUTER_API_KEY")

    # 1. Try Groq
    if groq_api_key:
        try:
            response = requests.post(
                url="https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {groq_api_key}"},
                json={
                    "model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"Groq failed: {e}. Falling back to Google.")
    
    # 2. Try Google
    if google_api_key:
        try:
            response = requests.post(
                url=f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={google_api_key}",
                headers={"Content-Type": "application/json"},
                json={
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": temperature,
                        "maxOutputTokens": max_tokens
                    }
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as e:
            print(f"Google failed: {e}. Falling back to OpenRouter.")

    # 3. Try OpenRouter
    if or_api_key:
        try:
            response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {or_api_key}",
                    "HTTP-Referer": "http://localhost:3000",
                    "X-Title": "AI Engineering Challenge"
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"OpenRouter failed: {e}.")
            
    raise Exception("All API fallbacks failed or no API keys found.")

class InterviewConductor:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        # Using the exact model string required by the challenge rules
        self.model = "claude-sonnet-4-20250514"
        
        # OpenRouter mapping for the required model string
        self._or_model = "anthropic/claude-3-haiku"

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
        prompt = f"""You are an expert AI Interview Conductor for a career upskilling platform. Your task is to conduct a live mock interview.
You will generate the NEXT question for the candidate based on their profile and the previous questions and answers.

<candidate_profile>
- ICP Type: {icp_type}  (Context: 'high_wage' implies a professional/technical corporate role needing rigorous scenarios. 'low_wage' implies an entry-level or gig worker moving to stable salaried work, needing accessible language, confidence building, and practical scenarios without corporate jargon.)
- Target Role: {target_role}
- Round Type: {round_type}
- Company Tier: {company_tier}
- Language: {language}
</candidate_profile>

<transcript>
{json.dumps(previous_qa_pairs, indent=2, ensure_ascii=False)}
</transcript>

Instructions:
1. ADAPTIVE LOGIC IS CRITICAL: You MUST explicitly respond to the candidate's last answer in the transcript. If they mentioned a specific tool, concept, or weakness, your next question MUST probe that specific thing. 
2. If they showed strength, ask a harder extension question or move to a new topic. If they showed weakness or gap, ask a simpler follow-up probing the same gap. If there are no previous answers, start with an appropriate introductory question.
3. CONTEXT & TONE FORKING:
   - If ICP Type is 'high_wage', use a professional, corporate tone. Ask rigorous, theoretical, or structured technical/behavioral questions suitable for {company_tier} companies.
   - If ICP Type is 'low_wage', use an encouraging, accessible, and grounded tone. Frame questions around practical, day-to-day scenarios. Avoid corporate jargon. Build their confidence while testing their fit for the {target_role} role.
4. The `reasoning` field MUST explicitly state your adaptive logic (e.g., "Because the candidate answered [X], I am asking [Y] to test [Z]").
5. LANGUAGE & FORMAT:
   - The language of the question MUST be '{language}'.
   - If 'hi' (Hindi), use colloquial, conversational Indian Hindi (Hinglish mix is fine if natural, like a real interviewer). DO NOT use formal textbook Hindi. DO NOT literally translate English idioms.
   - If 'en' (English), use natural spoken English.
6. You MUST return ONLY a valid JSON object matching the exact schema below, with NO missing fields, NO extra hallucinated fields, and correct data types:
{{
  "thought_process": "<string: your step-by-step reasoning about the candidate's previous answer and what gap or strength needs to be probed next>",
  "next_question": "<string: the exact question text to be asked>",
  "question_type": "<string: exactly one of 'technical', 'behavioral', or 'follow_up'>",
  "difficulty_level": <integer: 1 to 5>,
  "reasoning": "<string: brief explicit explanation of why this question was chosen based on the previous answer>"
}}

Output ONLY the raw JSON object without any markdown formatting, backticks, or extra text. Do not wrap the JSON in ```json blocks.
"""
        content = _call_llm_with_fallback(prompt, temperature=0.7, max_tokens=1500)
        
        # Extract JSON object from the response using regex in case of prepended text
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group(0)
            
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
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        # Using the exact model string required by the challenge rules
        self.model = "claude-sonnet-4-20250514"
        
        # OpenRouter mapping for the required model string
        self._or_model = "anthropic/claude-3-haiku"

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
        prompt = f"""You are an expert AI Interview Scorer for a career upskilling platform. Evaluate the candidate based on the provided interview transcript.

<interview_details>
- ICP Type: {icp_type} (Context: 'high_wage' implies corporate professional expectations. 'low_wage' implies entry-level/gig-worker moving to a stable salary - evaluate fairly based on this context, focusing on trainability, attitude, and basic skills rather than advanced corporate polish.)
- Target Role: {target_role}
- Round Type: {round_type}
</interview_details>

<hiring_bar>
{json.dumps(hiring_bar, indent=2)}
(These are the minimum scores required for each axis out of 100)
</hiring_bar>

<transcript>
{json.dumps(full_transcript, indent=2, ensure_ascii=False)}
</transcript>

Instructions:
1. Provide an honest, objective evaluation based ONLY on the <transcript> provided above. Do not hallucinate performance that isn't there.
2. Evaluate across 5 axes: communication, technical, problem_solving, behavioral, delivery. Score each from 0-100.
3. ADAPTIVE SCORING (ICP Differentiation):
   - For 'high_wage', hold them to a rigorous corporate standard for the {target_role} role.
   - For 'low_wage', calibrate your scoring for an entry-level worker. A good score in 'communication' or 'delivery' for a low_wage candidate means they are clear, polite, and eager, even if they don't use polished corporate English.
4. CALCULATE GAP VS BAR: For each axis, calculate `gap_vs_bar = user_score - hiring_bar`.
   - If the user_score is less than the hiring_bar, this MUST be a strictly NEGATIVE number (e.g., -15).
   - If user_score >= hiring_bar, it should be 0 or positive. Do not soften negative feedback.
5. EXTRACT EXACT QUOTES: For `weak_moment` and `strong_moment`, you MUST extract an EXACT, verbatim substring directly from the text of the candidate's answers in the <transcript>. DO NOT paraphrase. DO NOT hallucinate. If you invent a quote, you fail.
6. QUALITY FEEDBACK: The `why_it_hurt`, `why_it_helped`, and `next_action` fields must feel personal, specific, and real. Speak directly to the user (e.g., "When you said [X], it showed...", or "You did a great job explaining...").
7. You MUST return ONLY a valid JSON object matching the exact schema below, with NO missing fields, NO extra hallucinated fields, and correct data types:
{{
  "thought_process": "<string: your step-by-step reasoning evaluating the transcript against the hiring bar before scoring>",
  "overall_score": <integer: 0 to 100>,
  "scores_per_axis": {{
    "communication": <integer: 0 to 100>,
    "technical": <integer: 0 to 100>,
    "problem_solving": <integer: 0 to 100>,
    "behavioral": <integer: 0 to 100>,
    "delivery": <integer: 0 to 100>
  }},
  "gap_vs_bar": {{
    "communication": <integer: user_score minus hiring_bar>,
    "technical": <integer: user_score minus hiring_bar>,
    "problem_solving": <integer: user_score minus hiring_bar>,
    "behavioral": <integer: user_score minus hiring_bar>,
    "delivery": <integer: user_score minus hiring_bar>
  }},
  "weak_moment": {{
    "timestamp_approx": "<string: e.g., 'Turn 2'>",
    "quote": "<string: EXACT verbatim substring from the candidate's answer>",
    "why_it_hurt": "<string: personal, specific reason addressed to the user>"
  }},
  "strong_moment": {{
    "quote": "<string: EXACT verbatim substring from the candidate's answer>",
    "why_it_helped": "<string: personal, specific reason addressed to the user>"
  }},
  "next_action": "<string: 1 specific, highly actionable drill recommendation tailored to their ICP>"
}}

Output ONLY the raw JSON object without any markdown formatting, backticks, or extra text. Do not wrap the JSON in ```json blocks.
"""
        content = _call_llm_with_fallback(prompt, temperature=0.3, max_tokens=1500)
        
        # Extract JSON object from the response using regex in case of prepended text
        import re
        match = re.search(r'\{.*\}', content, re.DOTALL)
        if match:
            content = match.group(0)
            
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
