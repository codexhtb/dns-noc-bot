import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv("/opt/noc-ai/app/.env")

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[
        {
            "role": "user",
            "content": "Ты кто?"
        }
    ]
)

print(response.choices[0].message.content)
