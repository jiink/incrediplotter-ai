# see https://ai.google.dev/gemini-api/docs/image-generation#python

from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64
import os

env_var_name = "GEMINI_KEY"
api_key = os.getenv(env_var_name)
if api_key is None:
  raise ValueError(env_var_name + " environment variable not set")

client = genai.Client(api_key=api_key)

thing_i_want = 'cat'

contents = ('Please generate an image of a '
            'A monochrome unshaded simple thin line art of a'
            + thing_i_want +
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
    image.save('gemini-native-image.png')
    image.show()
