import sys
import os
import google.generativeai as genai

apikey=""

# Use Gemini native code
sysmsg="You are a helpful assistant"

model='gemini-2.5-flash-lite'
gencfg=genai.GenerationConfig(temperature=0.31)

genai.configure(api_key=apikey)
model = genai.GenerativeModel(
    model_name=model,
    system_instruction=sysmsg,
    generation_config=gencfg)
chat=model.start_chat()

completion=chat.send_message("Why is the sky blue?")

# STOP is the regular finish reason when no errors
stop=completion.candidates[0].finish_reason.name.lower()
print(stop)
if stop!="stop":
    AIError=True
    response=None
else:
    response=completion.text
