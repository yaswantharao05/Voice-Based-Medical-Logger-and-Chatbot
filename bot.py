from tkinter import *
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import os
import json
import requests
import time
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()  # Load environment variables

# Set up API tokens and endpoints
API_TOKEN = os.getenv("API_TOKEN")
headers = {"Authorization": f"Bearer {API_TOKEN}"}
API_URL = "https://api-inference.huggingface.co/models/openai/whisper-large-v3"
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# GUI setup
root = Tk()
root.title("Chatbot")

BG_GRAY = "#ABB2B9"
BG_COLOR = "#212121"
TEXT_COLOR = "#FFFFFF"

FONT = "Helvetica 14"
FONT_BOLD = "Helvetica 13 bold"

# Recording and query variables
is_recording = False
fs = 44100
recorded_data = []
audio_folder = "recorded_audio"
if not os.path.exists(audio_folder):
    os.makedirs(audio_folder)

# Toggle button mode
query_mode = "Casual"  # Default mode
recorded = False
transcription_data = ""
prevous_casual_convo = ""


# Function to toggle query mode
def toggle_mode():
    global query_mode
    if recorded:
        if query_mode == "Casual":
            query_mode = "Medical"
            toggle_btn.config(text="Switch to\nCasual Mode")
            txt.insert(END, "\nBot -> Switched to Medical Mode.\n")
        else:
            query_mode = "Casual"
            toggle_btn.config(text="Switch to\nMedical Mode")
            txt.insert(END, "\nBot -> Switched to Casual Mode.\n")
    else:
        txt.insert(END, "\nBot -> First record patient data to switch to Medical Mode.\n")

# API function to process audio
def query(filename):
    with open(filename, "rb") as f:
        data = f.read()
    response = requests.post(API_URL, headers=headers, data=data)
    return json.loads(response.content.decode("utf-8"))

# Function to get response from GenAI for patient data
def get_gemini_response(input_text):
    prompt = [
        """
        Use the given input text to generate a JSON output with the following keys - known allergies, medications taking, past treatments, plaque index, gingival index, caries, missing teeth, gum condition, RBC count, haemoglobin level, iron level, diagnosis, treatment plan, additional notes.
        """
    ]
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], input_text])
    return response.text


# Start recording function
def start_recording():
    global is_recording, recorded_data
    is_recording = True
    recorded_data = []
    txt.insert(END, "\nBot -> Recording started...\n")
    record_audio()

# Stop recording function
def stop_recording():
    global is_recording, recorded, transcription_data
    if is_recording:
        recorded = True
        toggle_mode()
        is_recording = False
        audio_file_path = os.path.join(audio_folder, "recording.mp3")
        write(audio_file_path, fs, np.array(recorded_data))
        txt.insert(END, f"\nBot -> Audio saved at {audio_file_path}\n           Processing audio. Please wait!\n")

        transcription_data = query('E:\SLP project\Chatbot-GUI\Recording (6).mp3')
        input_text = transcription_data.get('text', 'Could not transcribe audio.')

        txt.insert(END, f"\nYou -> {input_text}\n\n")
        json_op = get_gemini_response(input_text)
        txt.insert(END, f"\nBot -> JSON Output:\n {json_op}\n")
    else:
        txt.insert(END, f"\nYou -> Please star Recording first.\n\n")
    

# Function to record audio in chunks
def record_audio():
    if is_recording:
        data = sd.rec(int(fs * 1), samplerate=fs, channels=2)
        sd.wait()
        recorded_data.extend(data)
        root.after(1, record_audio)

# Function to handle query based on mode
def handle_query(input_text):
    if query_mode == "Casual":
        return casual_responses(input_text)
    elif query_mode == "Medical":
        # Process the last recorded audio
        if 'text' in transcription_data:
            patient_data = transcription_data['text']
            response = get_medical_response(patient_data, input_text)
            return f"Medical Response:\n{response}"
        else:
            return "Sorry, no valid medical data was found."

# Function to generate casual responses
def casual_responses(user_input):
    global prevous_casual_convo
    prompt = [
        f"Use the given input text to answer like a human. Your previous conversation is: {prevous_casual_convo}"
    ]
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt[0], user_input])
    prevous_casual_convo = response.text    
    return response.text


def get_medical_response(patient_data, prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content([prompt, patient_data])
    return response.text

# Send function
def send():
    inp = e.get()
    user_input = e.get().strip().lower()
    if user_input:
        txt.insert(END, f"\nYou -> {inp}\n")
        response = handle_query(user_input)
        txt.insert(END, f"\nBot -> {response}\n")
    e.delete(0, END)

# GUI elements

Label(root, bg=BG_COLOR, fg=TEXT_COLOR, text="Patient Data Entry", font=FONT_BOLD, pady=10, width=20, height=1).grid(row=0, column=0, columnspan=3)

txt = Text(root, bg=BG_COLOR, fg=TEXT_COLOR, font=FONT, width=70, height=20)
txt.grid(row=1, column=0, columnspan=3, pady=5)
scrollbar = Scrollbar(txt)
scrollbar.place(relheight=1, relx=0.974)

e = Entry(root, bg="#2f2f2f", fg=TEXT_COLOR, font=FONT, width=60)
e.grid(row=2, column=0, padx=5, pady=10, columnspan=2, sticky="e")

send_btn = Button(root, text="    Send    ", font=FONT_BOLD, bg=BG_GRAY, command=send)
send_btn.grid(row=2, column=2, padx=5, pady=10, sticky="e")

toggle_btn = Button(root, text="Switch to Medical Mode", font=FONT_BOLD, bg=BG_GRAY, command=toggle_mode)
toggle_btn.grid(row=3, column=0, pady=10, sticky="w", padx=65)

record_btn = Button(root, text="Record", font=FONT_BOLD, bg=BG_GRAY, command=start_recording)
record_btn.grid(row=3, column=1, pady=10, sticky="w")

stop_btn = Button(root, text="Stop Recording", font=FONT_BOLD, bg=BG_GRAY, command=stop_recording)
stop_btn.grid(row=3, column=1, pady=10, sticky="w", padx=145, columnspan=2)

txt.insert(END, "\nBot -> Hi! How can I assist you today\n")

root.mainloop()
