import whisper
import requests
import subprocess
import time
import sys

def translate_text(text, target="vi"):
    if not text:
        return text
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": text
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        return "".join([item[0] for item in data[0] if item[0]])
    except:
        return text

def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

print("Dang nhan dang giong noi...")
model = whisper.load_model("base")
result = model.transcribe("input.mp4")

print("Dang dich...")
srt_lines = []
for i, seg in enumerate(result["segments"]):
    start = seg["start"]
    end = seg["end"]
    original = seg["text"].strip()
    translated = translate_text(original, "vi")
    srt_lines.append(str(i + 1))
    srt_lines.append(f"{format_time(start)} --> {format_time(end)}")
    srt_lines.append(translated)
    srt_lines.append("")
    if (i + 1) % 10 == 0:
        print(f"Da dich {i+1}/{len(result['segments'])}")

with open("subtitle.srt", "w", encoding="utf-8") as f:
    f.write("\n".join(srt_lines))
print("Da tao file subtitle.srt")

# Ghep phu de vao video
print("Dang ghep phu de...")
cmd = [
    "ffmpeg", "-i", "input.mp4",
    "-vf", "subtitles=subtitle.srt:force_style='FontName=Arial,FontSize=22,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Alignment=2,MarginV=30'",
    "-c:v", "libx264", "-preset", "fast", "-crf", "23",
    "-c:a", "copy", "-y", "output_dich.mp4"
]
subprocess.run(cmd, check=True)
print("Da tao file output_dich.mp4")
