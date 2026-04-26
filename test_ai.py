from openai import OpenAI

# Point the client to your local LM Studio server
# The API key doesn't matter for local connections, but the library requires one to be set
client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

# --- THE BRAIN ---
# This tells Gemma exactly who you are and what the rules are
system_prompt = """You are an expert financial categorizer. I run a fabrication, 3D printing, and electronics business called Godsey Fabrications. 
Analyze the following receipt text and categorize it into one of three buckets:
1. 'Definitely Business' (e.g., filament, microcontrollers, server hardware, PCB orders)
2. 'Maybe Business' (e.g., meals, gas, general tech, split orders)
3. 'Definitely Personal' (e.g., groceries, streaming services, video games)

Output ONLY a clean JSON object with two keys: "category" and "justification". Do not output any conversational text or markdown formatting blocks."""

# --- THE TEST DATA ---
# A classic "Amazon Problem" receipt
sample_receipt = """
Date: Wed, 22 Apr 2026
Subject: Your Amazon.ca order confirmation
Snippet: Thank you for shopping with us. Your order of 2x Spools ASA Filament Black 1.75mm, 1x ESP32 Development Board 3-Pack, and 1x Bag of Kicking Horse Coffee has shipped. Total: $112.45.
"""

print("🧠 Sending receipt to local AI for analysis...\n")

try:
    completion = client.chat.completions.create(
        model="local-model", # LM Studio automatically routes this to whatever model is loaded
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": sample_receipt}
        ],
        temperature=0.1 # Keep this low so the AI stays strictly analytical and doesn't get creative
    )

    # Print the AI's response
    print(completion.choices[0].message.content)

except Exception as e:
    print(f"❌ Connection Error. Is your LM Studio server running? Error details: {e}")