import pvporcupine
from pvrecorder import PvRecorder
import os

porcupine = pvporcupine.create(access_key=os.getenv("PICOVOICE_KEY"), keywords=["computer"])
recoder = PvRecorder(device_index=-1, frame_length=porcupine.frame_length)

try:
    recoder.start()
    print("READY.")
    while True:
        keyword_index = porcupine.process(recoder.read())
        if keyword_index >= 0:
            print(f"Detected keyword")


except KeyboardInterrupt:
    recoder.stop()
finally:
    porcupine.delete()
    recoder.delete()
