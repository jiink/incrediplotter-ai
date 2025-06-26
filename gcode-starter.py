import requests
import os

# --- Configuration ---
MOONRAKER_URL = "http://localhost"  # Or your printer's IP address
GCODE_FILE_PATH = "apple.gcode" # Replace with the actual path to your G-code file

# --- Script ---

def upload_gcode(file_path):
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

def start_print(file_name):
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

if __name__ == "__main__":
    uploaded_filename = upload_gcode(GCODE_FILE_PATH)
    if uploaded_filename:
        start_print(uploaded_filename)
