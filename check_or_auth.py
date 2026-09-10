import os
from dotenv import load_dotenv
load_dotenv('.env', override=True)
import requests

key = os.getenv('OPENROUTER_API_KEY')
print(f"Key prefix: {key[:12]}...")

# 1. Auth check
resp = requests.get(
    'https://openrouter.ai/api/v1/auth/key',
    headers={'Authorization': 'Bearer ' + key}
)
data = resp.json()
print(f"Auth status: {resp.status_code}")
if 'data' in data:
    d = data['data']
    print(f"  Label: {d.get('label', 'N/A')}")
    print(f"  Usage: {d.get('usage', 'N/A')}")
    print(f"  Free tier: {d.get('is_free_tier', 'N/A')}")

# 2. Actual generation test
print("\nTesting generation...")
from openai import OpenAI
client = OpenAI(
    api_key=key,
    base_url='https://openrouter.ai/api/v1'
)
try:
    resp = client.chat.completions.create(
        model='nex-agi/nex-n2.5-mini:free',
        messages=[{'role': 'user', 'content': 'Say hello in 3 words'}],
        max_tokens=20,
        extra_headers={'HTTP-Referer': 'https://zara.ai', 'X-Title': 'ZARA AI'},
        timeout=15,
    )
    print(f"SUCCESS: {resp.choices[0].message.content}")
except Exception as e:
    err = str(e)
    print(f"FAILED: {err[:200]}")
