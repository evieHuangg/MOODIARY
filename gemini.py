import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.0-flash-lite")

def generate_encouragement(user_input):
    prompt = (
        f"請根據下列內容給出一段簡短（不超過 50 字）的鼓勵話語，溫暖且正向。\n\n"
        f"內容：\n{user_input}\n\n"
        f"鼓勵語："
    )
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print("Gemini API error:", e)
        return "加油喔，你不是一個人！"