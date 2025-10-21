from google import genai

client = genai.Client()  # uses GEMINI_API_KEY
resp = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Explain how AI works in one paragraph."
)
print(resp.text)