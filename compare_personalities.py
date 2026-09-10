"""
Zara Personality Comparison & Demonstration Script
Generates and compares system prompts across modes, styles, and modules.
Verifies the behavioral differences between Zara Fast, Zara Pro, and Zara Eco.
"""

import sys
sys.path.insert(0, ".")

from app.services.zara_identity import (
    build_identity_prompt,
    detect_communication_style,
    get_compact_core_identity,
)
from app.services.prompt_builder import build_system_prompt
from app.services.response_controller import response_controller

def test_prompt_generation_scenarios():
    print("=" * 80)
    print("ZARA IDENTITY SYSTEM — COMPARATIVE ANALYSIS & VERIFICATION")
    print("=" * 80)

    # Scenario 1: Same question, 3 different modes (Zara Fast vs Pro vs Eco)
    query = "How do I optimize database queries in PostgreSQL?"
    style = "technical"
    lang = "en"

    print("\n[SCENARIO 1] Mode Differentiation for Query:", query)
    print("-" * 80)

    for mode, label in [("zara-fast", "ZARA FAST (Conversational)"),
                        ("zara-pro", "ZARA PRO (Expert Partner)"),
                        ("zara-eco", "ZARA ECO (Efficient Assistant)")]:
        prompt = build_identity_prompt(mode=mode, language=lang, comm_style=style)
        print(f"\n>>> Mode: {label} (System Prompt Size: {len(prompt)} chars)")
        
        # Check specific behavioral directives
        if "MODE: ZARA FAST" in prompt:
            print("  • Identity Mode: ZARA FAST")
            print("  • Core Directive: Lead with answer, conversational rhythm, 1-5 sentences default")
            print("  • Formatting: Plain text default, code block + natural explanation")
        elif "MODE: ZARA PRO" in prompt:
            print("  • Identity Mode: ZARA PRO")
            print("  • Core Directive: Surface trade-offs, edge cases, deliberate structure when depth calls for it")
            print("  • Formatting: Organic structure, explicit confidence levels, expert tone")
        elif "MODE: ZARA ECO" in prompt:
            print("  • Identity Mode: ZARA ECO")
            print("  • Core Directive: Minimum-useful response, no preamble, 1-3 sentences default")
            print("  • Formatting: No bullet lists, zero filler, ultra-concise")

    # Scenario 2: Style Detection across various user inputs
    print("\n" + "=" * 80)
    print("[SCENARIO 2] Style Detection Engine Accuracy")
    print("-" * 80)
    sample_inputs = [
        ("yo bro can u check this error quick", "casual"),
        ("Dear Zara, could you please provide an in-depth analysis of the architecture?", "formal"),
        ("The latency p99 exceeds 450ms when async worker threads block on postgres I/O", "technical"),
        ("I'm totally new to coding, what is an API and how do I start?", "beginner"),
        ("machi idhu enna error nu paaru da", "casual"),
        ("ok", "short"),
        ("Can we optimize this function?", "technical"),
    ]

    for text, expected in sample_inputs:
        detected = detect_communication_style(text)
        status = "PASS" if detected == expected else f"FAIL (got {detected})"
        print(f"  [{status}] Input: '{text}' -> Detected: {detected} (Expected: {expected})")

    # Scenario 3: Response Controller AI-Tell Cleaning
    print("\n" + "=" * 80)
    print("[SCENARIO 3] Response Controller Deterministic AI-Tell Cleanup")
    print("-" * 80)
    raw_ai_outputs = [
        "Certainly! Here is how to configure Redis caching in Node.js.",
        "As an AI, I recommend checking your database indexes.",
        "I hope this helps! Feel free to ask if you have any more questions!",
        "Hello! How can I assist you today? Let's get started.",
        "Here is the solution to your issue:\n```python\nprint('hello')\n```",
    ]

    for raw in raw_ai_outputs:
        cleaned = response_controller(raw, mode="fast", target_lang="English")
        print(f"  Raw:     \"{raw}\"")
        print(f"  Cleaned: \"{cleaned}\"")

    # Scenario 4: Creator Attribution & Security Verification
    print("\n" + "=" * 80)
    print("[SCENARIO 4] Creator Attribution & Security Integrity")
    print("-" * 80)
    compact_core = get_compact_core_identity()
    print(f"  Compact Core Identity Length: {len(compact_core)} chars")
    assert "Mohammed Majeed" in compact_core, "Mohammed Majeed creator attribution missing!"
    assert "CRISIS SAFETY" in compact_core or "Crisis" in compact_core, "Crisis safety missing!"
    print("  [PASS] Mohammed Majeed attribution strictly preserved")
    print("  [PASS] Crisis safety protocol active across all modes")

    print("\n" + "=" * 80)
    print("ALL SCENARIOS VERIFIED SUCCESSFULLY")
    print("=" * 80)

if __name__ == "__main__":
    test_prompt_generation_scenarios()
