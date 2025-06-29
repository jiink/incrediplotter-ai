import serial
import time

def send_command(port_name: str, command: str, baud_rate: int = 9600):
    """
    Sends a command string over the specified COM port.

    Args:
        port_name (str): The name of the COM port (e.g., 'COM4').
        command (str): The command string to send.
        baud_rate (int): The baud rate for the serial communication.
    """
    try:
        # Open the serial port
        # 'timeout=1' ensures that read/write operations will not block indefinitely.
        with serial.Serial(port_name, baud_rate, timeout=1) as ser:
            print(f"--- Connected to {port_name} at {baud_rate} baud ---")
            print(f"Sending command: '{command}'")

            # Encode the command string to bytes (UTF-8 is a common encoding for serial)
            # Add a newline character at the end as is common for many serial protocols
            command_bytes = (command + '\n').encode('utf-8')
            ser.write(command_bytes)
            print("Command sent successfully.")
            # Give a small delay to ensure the data is fully transmitted before closing
            time.sleep(0.1)

    except serial.SerialException as e:
        print(f"Error: Could not open or communicate with port {port_name}. {e}")
        print("Please ensure the port is available and not in use by another application.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def show_bg_color(port_name: str, hex_color: str):
    """
    Constructs and sends a command to set the background color.

    Args:
        port_name (str): The name of the COM port (e.g., 'COM4').
        hex_color (str): A 6-digit hexadecimal color code (e.g., 'FF0000' for red).
                         The function will prepend '0x' if not present, but expects
                         a valid 6-digit hex string.
    """
    # Ensure the hex color is properly formatted (e.g., '00FF00' or '0x00FF00')
    if not hex_color.startswith('0x'):
        hex_color = hex_color.upper() # Standardize to uppercase
    else:
        hex_color = hex_color[2:].upper() # Remove '0x' and uppercase

    if not all(c in '0123456789ABCDEF' for c in hex_color) or len(hex_color) != 6:
        print(f"Invalid hex color code: {hex_color}. Please use a 6-digit hex code (e.g., '00FF00').")
        return

    command = f"SHOW_BG_COLOR {hex_color}"
    send_command(port_name, command)

def show_text(port_name: str, text_content: str):
    """
    Constructs and sends a command to display text.

    Args:
        port_name (str): The name of the COM port (e.g., 'COM4').
        text_content (str): The text string to display.
    """
    if not text_content.strip():
        print("Text content cannot be empty. Please provide some text to display.")
        return

    # Escape any special characters if necessary, though for simple text, it might not be needed.
    # For this example, we'll assume basic text and send it as is.
    command = f"SHOW_TEXT {text_content.strip()}"
    send_command(port_name, command)

# --- Example Usage ---
if __name__ == "__main__":
    # IMPORTANT: Replace 'COM4' with the actual name of your virtual COM port.
    # On Linux, it might be something like '/dev/ttyUSB0' or '/dev/ttyS0'.
    # On macOS, it might be '/dev/cu.usbserial-XXXX'.
    # Ensure you have pyserial installed: pip install pyserial
    VIRTUAL_COM_PORT = 'COM4' # Change this to your actual port!

    print("--- Testing SHOW_BG_COLOR command ---")
    show_text(VIRTUAL_COM_PORT, ":T")
    show_bg_color(VIRTUAL_COM_PORT, "00FF00") # Green
    time.sleep(1) # Wait a bit before sending the next command

    show_bg_color(VIRTUAL_COM_PORT, "FF0000") # Red
    time.sleep(1)

    show_bg_color(VIRTUAL_COM_PORT, "0000FF") # Blue
    time.sleep(1)

    print("\n--- Testing SHOW_TEXT command ---")
    show_text(VIRTUAL_COM_PORT, "Hello, Virtual Port!")
    time.sleep(1)

    show_text(VIRTUAL_COM_PORT, "This is a test message from Python.")
    time.sleep(1)

    show_text(VIRTUAL_COM_PORT, "COM4 communication is fun!")
    time.sleep(1)

    print("\n--- Testing an invalid color code ---")
    show_bg_color(VIRTUAL_COM_PORT, "ABC") # Invalid hex code

    print("\n--- Testing empty text ---")
    show_text(VIRTUAL_COM_PORT, "   ") # Empty text

    print("\nAll commands attempted.")
