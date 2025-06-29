import whisper
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import time
import re
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import os
import subprocess
import requests
import random
import string
from tiktok_voice import tts, Voice
import threading
from playsound import playsound
import pyttsx3
import traceback

# --- Configuration ---
MODEL_TYPE = "base.en"  # Options: "tiny", "base", "small", "medium", "large"
SAMPLE_RATE = 16000  # Whisper internal sample rate is 16kHz
FILENAME = "temp_recording.wav"
MOONRAKER_URL = "http://localhost"

def remove_specific_words(text_string, words_to_remove):
    """
    Removes specified words from a given string, ensuring whole word matching
    and case-insensitivity using regular expressions.

    Args:
        text_string (str): The input string from which words need to be removed.
        words_to_remove (list): A list of words (strings) to be removed.

    Returns:
        str: The modified string with the specified words removed.
    """
    modified_string = text_string

    for word in words_to_remove:
        # Create a regular expression pattern for the word.
        # \b ensures a whole word match (word boundary).
        # re.IGNORECASE makes the match case-insensitive.
        pattern = r'\b' + re.escape(word) + r'\b'
        modified_string = re.sub(pattern, "", modified_string, flags=re.IGNORECASE)

    # Clean up any extra spaces that might result from removal (e.g., double spaces, leading/trailing spaces)
    modified_string = " ".join(modified_string.split())

    return modified_string


def init_whisper():
    try:
        print(f"Loading Whisper model '{MODEL_TYPE}'...")
        # This will download the model on the first run
        model = whisper.load_model(MODEL_TYPE)
        print("Whisper model loaded successfully.")
        return model
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        print("Please ensure you have a working internet connection for the first run.")
        return None


def get_phrase_from_user(model):
    # A list to store audio frames
    recorded_frames = []
    def audio_callback(indata, frames, time_info, status):
        """This function is called for each audio block from the microphone."""
        if status:
            print(f"Audio callback status: {status}")
        recorded_frames.append(indata.copy())

    # 2. Set up and start the audio stream
    got_phrase = False
    valid_drawing_phrase = False
    transcribed_text = ""
    while not valid_drawing_phrase:
        recorded_frames = []
        transcribed_text = ""
        try:
            print("\n" + "="*40)
            playsound("ready.mp3")
            user_input = input("Press Q to quit, or ENTER to start recording...")
            if user_input.strip().lower() == 'q':
                return "QUIT"
            # The 'with' statement ensures the stream is properly closed
            with sd.InputStream(samplerate=SAMPLE_RATE,
                                channels=1,
                                dtype='float32',
                                callback=audio_callback):
                print("🔴 Recording... Press ENTER to stop.")

                # The recording happens in the background via the callback
                # The main thread waits here for the user to press Enter again
                input() # This second input() call is what stops the recording

            print("⏹️ Recording stopped.")

            # 3. Process the recorded audio
            if not recorded_frames:
                print("No audio recorded.")
                continue

            print("Processing audio...")
            # Concatenate all the recorded frames into a single NumPy array
            recording = np.concatenate(recorded_frames, axis=0)

            # Save the recording to a WAV file (optional, but good for debugging)
            write(FILENAME, SAMPLE_RATE, recording)
            print(f"Recording saved to {FILENAME}")

            # 4. Transcribe the audio
            print("Transcribing audio...")
            result = model.transcribe(FILENAME)
            transcribed_text = result["text"].strip()
            got_phrase = True

            # 5. Print the result
            print("\n" + "="*40)
            print("Whisper heard:")
            print(f"-> {transcribed_text}")
            print("="*40 + "\n")

        except Exception as e:
            traceback.print_exc()
            print(f"\nAn error occurred: {e}")
            print("Please ensure your microphone is connected and configured correctly.")
            return ""
        
        if not got_phrase:
            print("Didn't get a phrase.")
        else:
            valid_drawing_phrase = transcribed_text.lower().startswith("draw ")
            if not valid_drawing_phrase:
                print(f'Not a valid drawing phrase: "{transcribed_text}"')
                playsound("nicetry.mp3")    
    what_to_draw = remove_specific_words(transcribed_text, ["draw", "a", "an"]).replace('.', '')
    return what_to_draw


def ai_comment_on_subject(subject):
    env_var_name = "GEMINI_KEY"
    api_key = os.getenv(env_var_name)
    if api_key is None:
        raise ValueError(env_var_name + " environment variable not set")

    client = genai.Client(api_key=api_key)

    contents = ('A user is requesting the the following subject be drawn. '
                'Make a snarky comment to the user about this; dont be afraid to be a bit of a jerk. '
                f'The subject is "{subject}"')

    response = client.models.generate_content(
        model="gemini-2.0-flash-lite",
        contents=contents,
        config=types.GenerateContentConfig(
        response_modalities=['TEXT']
        )
    )
    text_response = ''
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            text_response += part.text
    text_response = text_response.strip().replace("*", "")
    if text_response:
        tts(text_response, Voice.US_FEMALE_1, "output.mp3", play_sound=True)


# see https://ai.google.dev/gemini-api/docs/image-generation#python
def generate_drawing_png(phrase_to_draw):
    env_var_name = "GEMINI_KEY"
    api_key = os.getenv(env_var_name)
    if api_key is None:
        raise ValueError(env_var_name + " environment variable not set")

    client = genai.Client(api_key=api_key)

    contents = ('Please generate an image of '
                'a monochrome unshaded simple thin line art of a'
                + phrase_to_draw +
                'with a white background. ')

    response = client.models.generate_content(
        model="gemini-2.0-flash-preview-image-generation",
        contents=contents,
        config=types.GenerateContentConfig(
        response_modalities=['TEXT', 'IMAGE']
        )
    )
    for part in response.candidates[0].content.parts:
        if part.text is not None:
            print(part.text)
        elif part.inline_data is not None:
            image = Image.open(BytesIO((part.inline_data.data)))
            first_word = phrase_to_draw.strip().split()[0]
            rand_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
            img_save_path = f"{first_word}-{rand_str}.png"
            image.save(img_save_path)
    return img_save_path

# SEE C:\Users\jacob\.vpype.toml FOR GCODE CONFIGURATION!!!!
def png_to_gcode(png_path):
    img = Image.open(png_path)
    # Convert to grayscale, apply threshold, then save as 1-bit (black and white) BMP without dithering
    threshold = 128
    gray = img.convert('L')
    bw = gray.point(lambda x: 255 if x > threshold else 0, mode='1')
    bmp_path = os.path.splitext(png_path)[0] + ".bmp"
    bw.save(bmp_path, format="BMP")
    print("Image also saved as 2-color (black and white, thresholded) BMP at " + bmp_path)

    autotrace_input = bmp_path
    autotrace_output = os.path.splitext(png_path)[0] + ".svg"
    line_cmd = f'"C:\\Program Files\\AutoTrace\\autotrace.exe" -centerline -background-color FFFFFF -color-count 2 -output-file "{autotrace_output}" -output-format svg "{autotrace_input}"'
    result = subprocess.run(line_cmd, shell=True)
    if result.returncode != 0:
        print("AutoTrace command failed with return code", result.returncode)
        print("Terminating early.")
        quit()

    print("AutoTrace command executed successfully.")
    # Add xmlns to the <svg> tag if missing
    with open(autotrace_output, "r", encoding="utf-8") as f:
        svg_lines = f.readlines()
    for i, line in enumerate(svg_lines):
        if line.strip().startswith("<svg") and "xmlns=" not in line:
            idx = line.find('<svg')
            if idx != -1:
                tag_end = idx + 4
                new_line = line[:tag_end] + ' xmlns="http://www.w3.org/2000/svg"' + line[tag_end:]
                svg_lines[i] = new_line
                with open(autotrace_output, "w", encoding="utf-8") as f:
                    f.writelines(svg_lines)
                print("Added xmlns attribute to <svg> tag.")
            break
    output_name = os.path.splitext(autotrace_output)[0] + ".gcode"
    svg_to_gcode_cmd = f'vpype read "{autotrace_output}" linemerge --tolerance 0.1mm linesort layout --fit-to-margins 5mm 160x160mm gwrite --profile klipper_pen "{output_name}"'
    svg_to_gcode_result = subprocess.run(svg_to_gcode_cmd, shell=True)
    if svg_to_gcode_result.returncode != 0:
        print("vpype command failed with return code", result.returncode)
        return ''
    return output_name


def moonraker_upload_gcode(file_path):
    """Uploads a G-code file to Moonraker."""
    if not os.path.exists(file_path):
        print(f"Error: G-code file not found at {file_path}")
        return None

    file_name = os.path.basename(file_path)
    url = f"{MOONRAKER_URL}/server/files/upload"
    print(f"Uploading {file_name} to Moonraker...")

    try:
        with open(file_path, "rb") as f:
            files = {'file': (file_name, f, 'application/octet-stream')}
            response = requests.post(url, files=files)
            response.raise_for_status()  # Raise an exception for bad status codes
            print("File uploaded successfully.")
            return file_name
    except requests.exceptions.RequestException as e:
        print(f"Error uploading file: {e}")
        return None


def moonraker_start_print(file_name):
    """Starts a print from the uploaded G-code file."""
    if not file_name:
        print("Cannot start print, no file was uploaded.")
        return

    url = f"{MOONRAKER_URL}/printer/print/start?filename={file_name}"
    print(f"Requesting to start print of {file_name}...")

    try:
        response = requests.post(url)
        response.raise_for_status()
        print("Print started successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error starting print: {e}")


def send_and_start_plotting(gcode_path):
    if not os.path.exists(gcode_path):
        print(f"G-code file does not exist: {gcode_path}")
        return 1
    uploaded_filename = moonraker_upload_gcode(gcode_path)
    if uploaded_filename:
        moonraker_start_print(uploaded_filename)
    else:
        return 2
    return 0

old_tts_engine = None

def old_tts_say(message):
    global old_tts_engine
    if old_tts_engine is None:
        old_tts_engine = pyttsx3.init()
    old_tts_engine.setProperty('rate', 300)
    old_tts_engine.say(message)
    old_tts_engine.runAndWait()
    

def main():
    whisper_model = init_whisper()
    if whisper_model == None:
        print("Whisper init fail")
        return 1
    
    try:
        done = False
        while not done:
            what_to_draw = ''
            while what_to_draw == '':
                what_to_draw = get_phrase_from_user(whisper_model)
            if what_to_draw == 'QUIT':
                print("Quit requested")
                done = True
            print('will draw: "' + what_to_draw + '"')
            tts_thread = threading.Thread(
                target=ai_comment_on_subject,
                args=(what_to_draw,)
            )
            tts_thread.start()
            png_path = generate_drawing_png(what_to_draw)
            if png_path == '':
                print('png_path is empty. terminating.')
                return 1
            print("gemini's image is stored at " + png_path)
            img = Image.open(png_path)
            #img.show()
            gcode_path = png_to_gcode(png_path)
            if gcode_path == '':
                print('gcode_path is empty. terminating.')
                return 1
            gcode_size_bytes = os.path.getsize(gcode_path)
            if gcode_size_bytes > 4000000:
                print(f'The G-code is huge at {gcode_size_bytes/1000000:.2f} MB. Not gonna print that one.')
                return 1
            err = send_and_start_plotting(gcode_path)
            if err != 0:
                print(f"send_and_start_printing error {err}")
            print("Next loop.")
        print("Exiting.")
    except Exception as e:
        print(f"{e}")
        traceback.print_exc()
        old_tts_say(f'Crash with error: {e}')


if __name__ == "__main__":
    main()
