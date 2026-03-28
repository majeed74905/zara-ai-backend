import logging
from google import genai
from app.core.config import settings

logger = logging.getLogger("ZaraAI_TestAgent")

async def generate_tests(error_msg: str, applied_patch: str) -> str:
    logger.info("Test Agent generating regression barrier...")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    prompt = f"""
    You are the Test Module of an L5 Autonomous Engineering System.
    Write a multi-suite `pytest` script that serves as a regression barrier for this resolved bug.
    
    ERROR: {error_msg}
    IMPLEMENTED PATCH: {applied_patch}

    MANDATORY REQUIREMENTS:
    1. Write a direct unit test to test the exact edge case/failure footprint.
    2. Write an API boundary contract test simulating a FastAPI or external mock.
    3. Include parameterized testing to verify regressions won't reappear under mutated inputs.
    
    Only return raw valid Python code ready to be executed.
    """

    try:
         # Note: A real autonomous agent system executes this in an isolated docker container.
         response = await client.aio.models.generate_content(
             model='gemini-1.5-pro',
             contents=prompt
         )
         test_code = response.text.strip('```python').strip('```').strip()
         logger.info("Test case generated successfully.")
         
         # In a real deployed version, test file would be appended to tests/
         with open("test_auto_generated_regression.py", "w") as f:
             f.write(test_code)
             
         return test_code
    except Exception as e:
         logger.error(f"Test generation failed: {str(e)}")
         return ""
