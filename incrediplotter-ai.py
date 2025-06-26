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

# --- Configuration ---
MODEL_TYPE = "base.en"  # Options: "tiny", "base", "small", "medium", "large"
SAMPLE_RATE = 16000  # Whisper internal sample rate is 16kHz
FILENAME = "temp_recording.wav"

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

def get_phrase_from_user():
    print("Starting Whisper...")

    # 1. Load the Whisper model
    try:
        print(f"Loading Whisper model '{MODEL_TYPE}'...")
        # This will download the model on the first run
        model = whisper.load_model(MODEL_TYPE)
        print("Whisper model loaded successfully.")
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        print("Please ensure you have a working internet connection for the first run.")
        return

    # A list to store audio frames
    recorded_frames = []

    def audio_callback(indata, frames, time_info, status):
        """This function is called for each audio block from the microphone."""
        if status:
            print(f"Audio callback status: {status}")
        recorded_frames.append(indata.copy())

    # 2. Set up and start the audio stream
    got_phrase = False
    try:
        # The 'with' statement ensures the stream is properly closed
        with sd.InputStream(samplerate=SAMPLE_RATE,
                            channels=1,
                            dtype='float32',
                            callback=audio_callback):
            print("\n" + "="*40)
            input("Press ENTER to start recording...")
            print("🔴 Recording... Press ENTER to stop.")

            # The recording happens in the background via the callback
            # The main thread waits here for the user to press Enter again
            input() # This second input() call is what stops the recording

        print("⏹️ Recording stopped.")

        # 3. Process the recorded audio
        if not recorded_frames:
            print("No audio recorded. Exiting.")
            return

        print("Processing audio...")
        # Concatenate all the recorded frames into a single NumPy array
        recording = np.concatenate(recorded_frames, axis=0)

        # Save the recording to a WAV file (optional, but good for debugging)
        write(FILENAME, SAMPLE_RATE, recording)
        print(f"Recording saved to {FILENAME}")

        # 4. Transcribe the audio
        print("Transcribing audio... This may take a moment.")
        result = model.transcribe(FILENAME)
        transcribed_text = result["text"]
        got_phrase = True

        # 5. Print the result
        print("\n" + "="*40)
        print("Whisper heard:")
        print(f"-> {transcribed_text.strip()}")
        print("="*40 + "\n")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
        print("Please ensure your microphone is connected and configured correctly.")

    if not got_phrase:
        print("Terminating early.")
        return ""
    
    what_to_draw = remove_specific_words(transcribed_text.strip(), ["draw", "a"]).replace('.', '')
    return what_to_draw



# see https://ai.google.dev/gemini-api/docs/image-generation#python
def generate_drawing_png(phrase_to_draw):
    env_var_name = "GEMINI_KEY"
    api_key = os.getenv(env_var_name)
    if api_key is None:
        raise ValueError(env_var_name + " environment variable not set")

    client = genai.Client(api_key=api_key)

    contents = ('Please generate an image of a '
                'A monochrome unshaded simple thin line art of a'
                + phrase_to_draw +
                'with a white background')

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
            img_save_path = 'gemini-native-image.png'
            image.save(img_save_path)
    return img_save_path


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

def main():
    # what_to_draw = ''
    # while what_to_draw == '':
    #     what_to_draw = get_phrase_from_user()
    # print('will draw: "' + what_to_draw + '"')
    png_path = generate_drawing_png('apple')
    if png_path == '':
        print('png_path is empty. terminating.')
        return
    print("gemini's image is stored at " + png_path)
    img = Image.open(png_path)
    img.show()
    gcode_path = png_to_gcode(png_path)
    if gcode_path == '':
        print('gcode_path is empty. terminating.')
        return
    


if __name__ == "__main__":
    main()