# SEE C:\jacob\.vpype.toml FOR GCODE CONFIGURATION!!!!

from PIL import Image
import os
import subprocess
png_path = 'cactus,-6z0m7.png'
print("gemini's image is stored at " + png_path)
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
line_cmd = f'"C:\\Program Files\\AutoTrace\\autotrace.exe" -background-color FFFFFF -color-count 2 -output-file "{autotrace_output}" -output-format svg "{autotrace_input}"'
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


svg_to_gcode_cmd = f'vpype read "{autotrace_output}" linemerge --tolerance 0.1mm linesort layout --fit-to-margins 5mm 160x160mm gwrite --profile klipper_pen output.gcode'
svg_to_gcode_result = subprocess.run(svg_to_gcode_cmd, shell=True)
if svg_to_gcode_result.returncode != 0:
    print("vpype command failed with return code", result.returncode)
    print("Terminating early.")
    quit()

