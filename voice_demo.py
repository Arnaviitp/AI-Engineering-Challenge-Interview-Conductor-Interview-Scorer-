import json
import os
import sys
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from modules import InterviewConductor, InterviewScorer

import pyttsx3
import speech_recognition as sr
import sounddevice as sd
import numpy as np
import queue
import io
import wave

# Load environment variables from .env file securely
load_dotenv()

# Initialize STT recognizer
recognizer = sr.Recognizer()

# New ICP-A Profile for Demo Video (Live Change Exercise)
icp_a_new = {
    "icp_type": "high_wage",
    "target_role": "Frontend Developer",
    "round_type": "technical",
    "company_tier": "enterprise",
    "language": "en"
}

hiring_bar_a_new = {
    "communication": 80,
    "technical": 85,
    "problem_solving": 80,
    "behavioral": 75,
    "delivery": 80
}

def speak_text(text):
    print(f"\nAgent (Speaking): {text}")
    engine = pyttsx3.init()
    engine.say(text)
    engine.runAndWait()

def listen_to_candidate():
    print("\n[Microphone is ON - Please speak your answer...]")
    print("[Speak now. Recording will stop automatically after 2 seconds of silence]")
    
    sample_rate = 16000
    channels = 1
    q = queue.Queue()
    
    def callback(indata, frames, time, status):
        if status:
            pass # ignore status for now
        q.put(indata.copy())
    
    audio_data = []
    silence_threshold = 0.015  # Adjust if it's too sensitive or not enough
    silence_duration = 0
    max_silence = 2.0  # seconds of silence to stop
    has_spoken = False
    
    try:
        with sd.InputStream(samplerate=sample_rate, channels=channels, callback=callback):
            while True:
                data = q.get()
                audio_data.append(data)
                
                # Check for silence using RMS
                rms = np.sqrt(np.mean(data**2))
                if rms > silence_threshold:
                    has_spoken = True
                    silence_duration = 0
                elif has_spoken:
                    silence_duration += len(data) / sample_rate
                    if silence_duration > max_silence:
                        break
    except KeyboardInterrupt:
        pass

    print("\n[Processing speech...]")
    
    if not audio_data:
        return ""

    # Convert numpy array list to bytes
    audio_np = np.concatenate(audio_data, axis=0)
    # Convert to 16-bit PCM
    audio_pcm = (audio_np * 32767).astype(np.int16)
    
    # Write to in-memory WAV file
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_pcm.tobytes())
    
    wav_io.seek(0)
    
    try:
        with sr.AudioFile(wav_io) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio)
        return text
    except sr.UnknownValueError:
        print("[Error: Google Speech Recognition could not understand audio]")
        return ""
    except sr.RequestError as e:
        print(f"[Error: Could not request results from Google Speech Recognition service; {e}]")
        return ""

def run_voice_demo(icp_profile, hiring_bar, candidate_name="Candidate"):
    print(f"\n{'='*50}\nStarting Voice Demo for: {candidate_name} ({icp_profile['icp_type']})\n{'='*50}")
    
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
        
        next_q = question_data.get('next_question')
        
        # Speak the question
        speak_text(next_q)
        
        # Capture candidate's answer via STT
        # We will loop until we get a valid answer or the user cancels
        answer = ""
        while not answer:
            answer = listen_to_candidate()
            if not answer:
                print("Could not capture answer. Retrying in 2 seconds. Press Ctrl+C to abort.")
                time.sleep(2)
        
        print(f"Candidate (Transcribed): {answer}")
        
        # Save to transcript
        qa_pairs.append({
            "question": next_q,
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
    if not os.environ.get("OPENROUTER_API_KEY"):
        print("WARNING: OPENROUTER_API_KEY environment variable is not set. Please set it in your .env file or environment before running.")
    else:
        # Run Voice Demo for ICP-A (Frontend Developer, Enterprise, English)
        run_voice_demo(icp_a_new, hiring_bar_a_new, "Priya Sharma (Frontend Voice Demo)")
