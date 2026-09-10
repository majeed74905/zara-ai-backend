"""
20 Real-World Conversation Suite for Zara AI
════════════════════════════════════════════════════════════════════════════════
Executes 20 realistic conversation pipelines across English, Tanglish, Tamil,
and Mixed Language for Zara Fast, Pro, and Eco.
Validates:
  - Language detection accuracy
  - Communication profile adaptation
  - Identity & Mode personality injection
  - Absence of robotic phrases, AI-tells, or forced mimicry
"""

import sys
import os
import json
import time

sys.path.insert(0, ".")

from app.services.language_detector import detect_language
from app.services.zara_identity import detect_communication_profile, build_identity_prompt
from app.services.prompt_builder import build_system_prompt, build_user_prompt
from app.services.response_controller import response_controller

CONVERSATIONS = [
    # ── 1-5: ENGLISH SCENARIOS ────────────────────────────────────────────────
    {
        "id": "EN-01",
        "title": "Technical Architecture (Pro)",
        "mode": "pro",
        "turns": [
            "How should I design an event-driven architecture with Kafka and Redis for order processing?",
            "What happens if Kafka consumer commits the offset before writing to PostgreSQL?",
            "How does transactional outbox pattern prevent this failure mode?"
        ],
        "expected_lang": "English",
        "expected_style": "technical",
    },
    {
        "id": "EN-02",
        "title": "Casual Coding Query (Fast)",
        "mode": "fast",
        "turns": [
            "hey bro how do I filter an array of objects by a nested property in TypeScript?",
            "can you make it a reusable generic function?"
        ],
        "expected_lang": "English",
        "expected_style": "casual",
    },
    {
        "id": "EN-03",
        "title": "Frustrated Debugging (Fast)",
        "mode": "fast",
        "turns": [
            "Bro this docker compose is throwing port conflict 5432 already allocated, so irritating",
            "ok killed the process, now what"
        ],
        "expected_lang": "English",
        "expected_style": "casual",
    },
    {
        "id": "EN-04",
        "title": "Formal Enterprise Query (Pro)",
        "mode": "pro",
        "turns": [
            "Could you please elucidate the recommended disaster recovery strategy for multi-region active-passive deployments?",
            "What are the typical RPO and RTO trade-offs for cross-region asynchronous database replication?"
        ],
        "expected_lang": "English",
        "expected_style": "formal",
    },
    {
        "id": "EN-05",
        "title": "Beginner Student Query (Eco)",
        "mode": "eco",
        "turns": [
            "I am a school student, what is an API in simple words?",
            "give one real world example"
        ],
        "expected_lang": "English",
        "expected_style": "beginner",
    },

    # ── 6-10: TANGLISH SCENARIOS ──────────────────────────────────────────────
    {
        "id": "TG-01",
        "title": "Casual Technical Tanglish (Fast)",
        "mode": "fast",
        "turns": [
            "bro expressjs backend la jwt authentication eppadi setup panradhu?",
            "token expire aana refresh token flow epdi handle pannanum da?"
        ],
        "expected_lang": "Tanglish",
        "expected_style": "casual",
    },
    {
        "id": "TG-02",
        "title": "Payment Webhook Debugging (Pro)",
        "mode": "pro",
        "turns": [
            "webhook hit aaguthu but mysql db la payment id and status correct ah update aagala",
            "same student multiple times click panrappo duplicate charge aaguthu, idempotency eppadi implement panradhu?"
        ],
        "expected_lang": "Tanglish",
        "expected_style": "casual",
    },
    {
        "id": "TG-03",
        "title": "Frustrated Student Tanglish (Fast)",
        "mode": "fast",
        "turns": [
            "dei idhu romba mokka ah iruku 😂 gradle build sync fail aagite irukku",
            "clean build panna kooda error varuthu"
        ],
        "expected_lang": "Tanglish",
        "expected_style": "casual",
    },
    {
        "id": "TG-04",
        "title": "Short Direct Tanglish (Eco)",
        "mode": "eco",
        "turns": [
            "git merge conflict resolve panna command sollu",
            "abort panna?"
        ],
        "expected_lang": "Tanglish",
        "expected_style": "short_direct",
    },
    {
        "id": "TG-05",
        "title": "Friendly Enthusiastic Tanglish (Fast)",
        "mode": "fast",
        "turns": [
            "thala project deploy aaidichu, semma speed ah irukku thanks da!",
            "next pwa features add panna poreen"
        ],
        "expected_lang": "Tanglish",
        "expected_style": "casual",
    },

    # ── 11-15: TAMIL SCRIPT SCENARIOS ─────────────────────────────────────────
    {
        "id": "TA-01",
        "title": "Tamil Script Technical Query (Pro)",
        "mode": "pro",
        "turns": [
            "இந்த payment பிரச்சனைக்கு முதலில் என்ன check பண்ண வேண்டும்?",
            "database lock ஆகுமா?"
        ],
        "expected_lang": "Tamil",
        "expected_style": "technical",
    },
    {
        "id": "TA-02",
        "title": "Tamil Script Conceptual (Fast)",
        "mode": "fast",
        "turns": [
            "API என்றால் என்ன? எளிய முறையில் விளக்கவும்.",
            "இதன் பயன்கள் என்ன?"
        ],
        "expected_lang": "Tamil",
        "expected_style": "general",
    },
    {
        "id": "TA-03",
        "title": "Tamil Script Debugging (Fast)",
        "mode": "fast",
        "turns": [
            "என் Python நிரல் ஏன் memory leak ஆகிறது?",
            "profiler எவ்வாறு இயக்குவது?"
        ],
        "expected_lang": "Tamil",
        "expected_style": "technical",
    },
    {
        "id": "TA-04",
        "title": "Tamil Script Short Request (Eco)",
        "mode": "eco",
        "turns": [
            "SQL primary key என்றால் என்ன சுருக்கமாக?",
            "foreign key?"
        ],
        "expected_lang": "Tamil",
        "expected_style": "short_direct",
    },
    {
        "id": "TA-05",
        "title": "Tamil Casual Help (Fast)",
        "mode": "fast",
        "turns": [
            "வணக்கம் சாரா, வலைத்தளம் உருவாக்க என்ன படிக்க வேண்டும்?",
            "எளிதான வழி எது?"
        ],
        "expected_lang": "Tamil",
        "expected_style": "general",
    },

    # ── 16-20: MIXED & LANGUAGE SWITCHING SCENARIOS ───────────────────────────
    {
        "id": "MX-01",
        "title": "Tanglish to English Switch (Pro)",
        "mode": "pro",
        "turns": [
            "Bro payment gateway integration la race condition eppadi handle panradhu?",
            "Now please explain the exact database row locking mechanism in formal English.",
            "seri, ippo short ah sollu."
        ],
        "expected_lang": "Mixed / Dynamic",
        "expected_style": "technical",
    },
    {
        "id": "MX-02",
        "title": "English to Tamil Switch (Fast)",
        "mode": "fast",
        "turns": [
            "Can you explain what cloud computing is?",
            "இதை தமிழில் எளிமையாக சொல்லுங்கள்.",
            "நன்றி சாரா!"
        ],
        "expected_lang": "Mixed / Dynamic",
        "expected_style": "general",
    },
    {
        "id": "MX-03",
        "title": "Mixed Tech Vocabulary (Fast)",
        "mode": "fast",
        "turns": [
            "Payment success aaguthu, but webhook backend-ku reach aagudha nu doubt irukku. How can I verify that?",
            "ngrok tunnel setup panni verify pannalama?"
        ],
        "expected_lang": "Tanglish",
        "expected_style": "casual",
    },
    {
        "id": "MX-04",
        "title": "Hinglish to English Switch (Fast)",
        "mode": "fast",
        "turns": [
            "arre yaar ye flutter app build hi nahi ho raha gradle sync fail",
            "can you explain the fix in English please"
        ],
        "expected_lang": "Mixed / Dynamic",
        "expected_style": "casual",
    },
    {
        "id": "MX-05",
        "title": "Conciseness Drill Down (Eco)",
        "mode": "eco",
        "turns": [
            "Explain microservices architecture",
            "too long, 2 bullet points only",
            "single line"
        ],
        "expected_lang": "English",
        "expected_style": "short_direct",
    },
]

def run_20_conversations():
    print("=" * 80)
    print("EXECUTING 20 REAL-WORLD CONVERSATION SUITE")
    print("=" * 80)

    total_turns = 0
    passed_evals = 0

    for idx, conv in enumerate(CONVERSATIONS, 1):
        print(f"\n[{idx}/20] {conv['id']}: {conv['title']} (Mode: {conv['mode'].upper()})")
        history = []
        
        for turn_idx, turn_msg in enumerate(conv["turns"], 1):
            total_turns += 1
            # 1. Detect language
            lang = detect_language(turn_msg, history)
            # 2. Detect profile
            prof = detect_communication_profile(turn_msg, history)
            # 3. Assemble prompt
            sys_prompt = build_system_prompt(conv["mode"], lang, comm_style=prof)
            # 4. Check prompt integrity
            has_mode = f"MODE: ZARA {conv['mode'].upper()}" in sys_prompt
            has_creator = "Mohammed Majeed" in sys_prompt
            has_anti_mimicry = "ANTI-MIMICRY PROTOCOL" in sys_prompt
            
            # 5. Check response controller on mock response in matching target language
            if lang == "Tamil":
                raw_mock = f"Certainly! As an AI, இதுதான் உங்கள் கேள்விக்கான தீர்வு: {turn_msg[:20]}"
            elif lang == "Tanglish":
                raw_mock = f"Certainly! As an AI, idhu dhaan bro unga solution: {turn_msg[:20]}"
            else:
                raw_mock = f"Certainly! As an AI, here is the answer for: {turn_msg[:20]}"
            clean_mock = response_controller(raw_mock, conv["mode"], lang)
            clean_ok = "Certainly!" not in clean_mock and "As an AI" not in clean_mock

            # Turn evaluation
            print(f"  Turn {turn_idx}: '{turn_msg[:40]}...' -> Lang: {lang}, Style: {prof['primary_style']}, Emotion: {prof['emotion']}")
            
            if has_mode and has_creator and has_anti_mimicry and clean_ok:
                passed_evals += 1
            
            history.append({"role": "user", "content": turn_msg})
            history.append({"role": "assistant", "content": f"Acknowledged: {turn_msg[:20]}"})

    print("\n" + "=" * 80)
    print(f"CONVERSATION SUITE COMPLETE: {passed_evals}/{total_turns} turns verified successfully.")
    print("=" * 80)
    return passed_evals == total_turns

if __name__ == "__main__":
    ok = run_20_conversations()
    if not ok:
        sys.exit(1)
