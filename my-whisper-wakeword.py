import whisper
import sounddevice as sd
import numpy as np
import torch
import os

# --- Configuration ---
MODEL_TYPE = "base.en"  # Using an English-only model is faster
WAKE_WORD = "computer"
SAMPLE_RATE = 16000
CHUNK_SECONDS = 5       # Record audio in chunks of 5 seconds
FILENAME = "temp_recording.wav"

# Check if a GPU is available and set the device
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {DEVICE}")

def main():
    """
    Main function to run the Whisper wake word demo.
    """
    print("Starting Whisper wake word demo...")

    # 1. Load the Whisper model
    try:
        print(f"Loading Whisper model '{MODEL_TYPE}'...")
        # fp16=False is recommended for CPU-only usage
        model = whisper.load_model(MODEL_TYPE, device=DEVICE)
        if DEVICE == "cpu":
            print("Note: Running on CPU. Performance will be slower.")
            # If on CPU, you might need to disable fp16 if you get errors
            # model = whisper.load_model(MODEL_TYPE, device=DEVICE, fp16=False)
        print("Whisper model loaded successfully.")
    except Exception as e:
        print(f"Error loading Whisper model: {e}")
        return

    # Calculate the number of frames per chunk
    chunk_frames = CHUNK_SECONDS * SAMPLE_RATE

    while True:
        try:
            print(f"\nListening for '{WAKE_WORD}'...")

            # 2. Record audio for the specified chunk duration
            recording = sd.rec(int(chunk_frames), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
            sd.wait()  # Wait for the recording to finish

            # Convert to a 1D NumPy array
            audio_data = recording.flatten()

            # 3. Transcribe the recorded audio chunk
            # Use a smaller portion of the audio for faster transcription if needed, but for 5s it's fine
            print("Transcribing audio chunk...")
            result = model.transcribe(audio_data, fp16=torch.cuda.is_available())
            transcribed_text = result['text'].lower().strip()

            print(f"Heard: '{transcribed_text}'")

            # 4. Check for the wake word
            if WAKE_WORD in transcribed_text:
                print(f"✅ Wake word detected!")

                # Extract the command after the wake word
                command_start_index = transcribed_text.find(WAKE_WORD) + len(WAKE_WORD)
                command = transcribed_text[command_start_index:].strip()

                if command:
                    print(f"   Your command is: '{command}'")
                    # Here you would add logic to handle the command
                    # For this demo, we'll just print it.
                else:
                    print("   Wake word detected, but no command followed.")

        except KeyboardInterrupt:
            print("\nStopping demo.")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}")
            break

if __name__ == "__main__":
    main()
