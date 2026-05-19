import json
import os
from modules import InterviewConductor, InterviewScorer

# Mock profiles based on PDF
icp_a = {
    "icp_type": "high_wage",
    "target_role": "Software Engineer",
    "round_type": "screening",
    "company_tier": "startup",
    "language": "en"
}

icp_b = {
    "icp_type": "low_wage",
    "target_role": "Data entry executive",
    "round_type": "behavioral",
    "company_tier": "mid",
    "language": "hi"
}

# Mock answers
mock_answers_a = [
    "I have used Python for a few basic scripts and understand basic OOP concepts.",
    "I don't really know how to use databases or SQL efficiently, I usually just save to CSV files.",
    "I try to debug by adding print statements everywhere until I find the issue."
]

mock_answers_b = [
    "Haan sir, maine pichle do saal delivery ka kaam kiya hai aur main logo se hamesha achhe se baat karta hu.",
    "Excel me bas thoda bahut data entry dekha hai, formulas ya zyada kuch nahi aata mujhe.",
    "Main naya kaam jaldi seekh lunga sir, mujhe bas ek chance chahiye apne parivaar ke liye."
]

hiring_bar_a = {
    "communication": 70,
    "technical": 75,
    "problem_solving": 75,
    "behavioral": 70,
    "delivery": 70
}

hiring_bar_b = {
    "communication": 60,
    "technical": 40,
    "problem_solving": 50,
    "behavioral": 75,
    "delivery": 60
}

def run_demo(icp_profile, mock_answers, hiring_bar, candidate_name="Candidate"):
    print(f"\n{'='*50}\nStarting Demo for: {candidate_name} ({icp_profile['icp_type']})\n{'='*50}")
    
    conductor = InterviewConductor()
    scorer = InterviewScorer()
    
    qa_pairs = []
    
    # 3 Turns of Interview
    for turn in range(3):
        print(f"\n--- Turn {turn + 1} ---")
        
        # Conductor asks a question
        question_data = conductor.generate_next_question(
            icp_type=icp_profile["icp_type"],
            target_role=icp_profile["target_role"],
            round_type=icp_profile["round_type"],
            company_tier=icp_profile["company_tier"],
            language=icp_profile["language"],
            previous_qa_pairs=qa_pairs
        )
        
        print(f"Agent [Reasoning]: {question_data.get('reasoning')}")
        print(f"Agent [Diff: {question_data.get('difficulty_level')} | Type: {question_data.get('question_type')}]: {question_data.get('next_question')}")
        
        # Candidate answers
        answer = mock_answers[turn]
        print(f"Candidate: {answer}")
        
        # Save to transcript
        qa_pairs.append({
            "question": question_data.get("next_question"),
            "answer_transcript": answer
        })
        
    print(f"\n--- Interview Complete. Generating Score Report ---")
    
    # Scoring
    # Rename answer_transcript to answer for Scorer as per schema
    scorer_transcript = [{"question": pair["question"], "answer": pair["answer_transcript"]} for pair in qa_pairs]
    
    score_report = scorer.score_interview(
        full_transcript=scorer_transcript,
        icp_type=icp_profile["icp_type"],
        target_role=icp_profile["target_role"],
        round_type=icp_profile["round_type"],
        hiring_bar=hiring_bar
    )
    
    print("\nScore Report JSON:")
    print(json.dumps(score_report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("WARNING: ANTHROPIC_API_KEY environment variable is not set. Please set it before running.")
    else:
        # Run ICP-A (High wage, English)
        run_demo(icp_a, mock_answers_a, hiring_bar_a, "Riya Sharma")
        
        # Run ICP-B (Low wage, Hindi)
        run_demo(icp_b, mock_answers_b, hiring_bar_b, "Arjun Yadav")
