from dotenv import load_dotenv
from openai import OpenAI
import os

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
print("API key loaded:", api_key is not None)
print("First 10 chars:", api_key[:10] if api_key else "None")

client = OpenAI(api_key=api_key)

response = client.responses.create(
    model="gpt-4o-mini",
    input="Reply ONLY with: Hello Shreyas!"
)

print("Response:")
print(response.output_text)