from openai import OpenAI

# Initialize the client with Mistral's API base URL and your API key
client = OpenAI(
    base_url="https://api.mistral.ai/v1/",  # Mistral's API base URL
    api_key="your-mistral-api-key"          # Replace with your Mistral API key
)

def call_mistral(prompt):
    try:
        response = client.chat.completions.create(
            model="mistral-tiny",  # Replace with the model you want to use
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

if __name__ == "__main__":
    import sys
    user_input = sys.stdin.read().strip()
    if user_input:
        result = call_mistral(user_input)
        print(result)
    else:
        print("No input provided.")

