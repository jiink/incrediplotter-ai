import whisper
import sounddevice as sd
from scipy.io.wavfile import write
import numpy as np
import time
import re

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

def main():
    print("Starting Whisper demo...")

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
        print("\n" + "="*40)
        input("Press ENTER to start recording...")
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
        return
    
    ################
    what_to_draw = remove_specific_words(transcribed_text.strip(), ["draw", "a"]).replace('.', '')
    print('will draw: "' + what_to_draw + '"')


if __name__ == "__main__":
    main()

