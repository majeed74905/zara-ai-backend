from app.services.llm_router import llm_router
from app.api.ai import get_system_prompt

def test_router():
    print("Testing LLM Router...")
    
    # Test 1: Chat (Gemini)
    prompt = "Hello, who are you?"
    sys_prompt = get_system_prompt("chat", "chat")
    print("\n--- Test 1: Chat (Gemini) ---")
    try:
        res = llm_router.route_request("chat", "chat", prompt, sys_prompt)
        print("Response:", res[:100] + "...")
    except Exception as e:
        print("Error:", e)

    # Test 2: Tutor (DeepSeek -> Fallback Groq)
    print("\n--- Test 2: Tutor (DeepSeek) ---")
    sys_prompt = get_system_prompt("tutor", "explain")
    try:
        res = llm_router.route_request("tutor", "explain", "Explain quantum physics lightly", sys_prompt)
        print("Response:", res[:100] + "...")
    except Exception as e:
        print("Error:", e)

    # Test 3: Code (Groq)
    print("\n--- Test 3: Code Generate (Groq) ---")
    sys_prompt = get_system_prompt("code_architect", "generate")
    try:
        res = llm_router.route_request("code_architect", "generate", "Write a python hello world", sys_prompt)
        print("Response:", res[:100] + "...")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    test_router()
