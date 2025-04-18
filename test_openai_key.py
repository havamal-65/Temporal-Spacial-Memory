import openai
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key

try:
    models = openai.models.list()
    print("OpenAI API key is valid. Models:")
    for model in models.data:
        print("-", model.id)
except Exception as e:
    print("OpenAI API key test failed:", e) 