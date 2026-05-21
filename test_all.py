import os
import json
import traceback
from dotenv import load_dotenv
from modules import InterviewConductor, InterviewScorer

load_dotenv()

def validate_conductor_schema(data):
    required_keys = {"next_question": str, "question_type": str, "difficulty_level": int, "reasoning": str}
    for k, v_type in required_keys.items():
        if k not in data:
            raise ValueError(f"Missing key in Conductor output: {k}")
        if not isinstance(data[k], v_type):
            raise ValueError(f"Invalid type for {k} in Conductor output, expected {v_type.__name__}")
    if data["question_type"] not in ["technical", "behavioral", "follow_up"]:
        raise ValueError(f"Invalid question_type: {data['question_type']}")
    if not (1 <= data["difficulty_level"] <= 5):
        raise ValueError(f"Invalid difficulty_level: {data['difficulty_level']}")

def validate_scorer_schema(data, hiring_bar):
    required_keys = {"overall_score": int, "scores_per_axis": dict, "gap_vs_bar": dict, "weak_moment": dict, "strong_moment": dict, "next_action": str}
    for k, v_type in required_keys.items():
        if k not in data:
            raise ValueError(f"Missing key in Scorer output: {k}")
        if not isinstance(data[k], v_type):
            raise ValueError(f"Invalid type for {k} in Scorer output, expected {v_type.__name__}")
            
    axes = ["communication", "technical", "problem_solving", "behavioral", "delivery"]
    for axis in axes:
        if axis not in data["scores_per_axis"] or not isinstance(data["scores_per_axis"][axis], int):
            raise ValueError(f"Missing or invalid {axis} in scores_per_axis")
        if axis not in data["gap_vs_bar"] or not isinstance(data["gap_vs_bar"][axis], int):
            raise ValueError(f"Missing or invalid {axis} in gap_vs_bar")
        
        # Check gap vs bar logic
        expected_gap = data["scores_per_axis"][axis] - hiring_bar[axis]
        actual_gap = data["gap_vs_bar"][axis]
        if data["scores_per_axis"][axis] < hiring_bar[axis] and actual_gap >= 0:
            raise ValueError(f"gap_vs_bar for {axis} is not negative despite user_score < hiring_bar. user: {data['scores_per_axis'][axis]}, bar: {hiring_bar[axis]}, gap: {actual_gap}")

    weak_keys = {"timestamp_approx": str, "quote": str, "why_it_hurt": str}
    for k, v in weak_keys.items():
        if k not in data["weak_moment"] or not isinstance(data["weak_moment"][k], v):
            raise ValueError(f"Missing or invalid {k} in weak_moment")

    strong_keys = {"quote": str, "why_it_helped": str}
    for k, v in strong_keys.items():
        if k not in data["strong_moment"] or not isinstance(data["strong_moment"][k], v):
            raise ValueError(f"Missing or invalid {k} in strong_moment")

def main():
    test_dir = "test_cases"
    conductor = InterviewConductor()
    scorer = InterviewScorer()

    files = [f for f in os.listdir(test_dir) if f.endswith(".json")]
    
    success_count = 0
    fail_count = 0
    
    for file in files:
        file_path = os.path.join(test_dir, file)
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        profile = data["profile"]
        hiring_bar = data["hiring_bar"]
        turns = data["turns"]
        
        print(f"\nProcessing {file} ({profile['icp_type']}) ...")
        
        qa_pairs = []
        new_turns = []
        
        try:
            for turn in turns:
                # Re-run conductor for this turn
                agent_question_data = conductor.generate_next_question(
                    icp_type=profile["icp_type"],
                    target_role=profile["target_role"],
                    round_type=profile["round_type"],
                    company_tier=profile["company_tier"],
                    language=profile["language"],
                    previous_qa_pairs=qa_pairs
                )
                
                # Validate schema
                validate_conductor_schema(agent_question_data)
                
                candidate_answer = turn["candidate_answer"]
                
                new_turns.append({
                    "agent_question_data": agent_question_data,
                    "candidate_answer": candidate_answer
                })
                
                qa_pairs.append({
                    "question": agent_question_data["next_question"],
                    "answer_transcript": candidate_answer
                })
                
            scorer_transcript = [{"question": pair["question"], "answer": pair["answer_transcript"]} for pair in qa_pairs]
            
            score_report = scorer.score_interview(
                full_transcript=scorer_transcript,
                icp_type=profile["icp_type"],
                target_role=profile["target_role"],
                round_type=profile["round_type"],
                hiring_bar=hiring_bar
            )
            
            # Validate schema
            validate_scorer_schema(score_report, hiring_bar)
            
            # Update data
            data["turns"] = new_turns
            data["score_report"] = score_report
            
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            print(f"SUCCESS: {file} processed successfully and schema validated.")
            success_count += 1
            
        except Exception as e:
            print(f"FAILED on {file}: {str(e)}")
            traceback.print_exc()
            fail_count += 1

    print(f"\nCompleted! Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
