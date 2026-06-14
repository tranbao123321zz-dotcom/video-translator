import whisper
import requests
import subprocess
import re
import json
import time

CONFIG = {
    'model': 'base',
    'target': 'vi',
    'font_size': 28,
    'max_chars': 38,
    'margin_v': 50
}

def translate_text(text, target='vi'):
    """Dịch bằng LibreTranslate - free, không chặn"""
    if not text or not text.strip():
        return text
    
    url = "https://libretranslate.com/translate"
    payload = {
        "q": text,
        "source": "auto",
        "target": target,
        "format": "text"
    }
    try:
        r = requests.post(url, json=payload, timeout=60)
        if r.status_code == 200:
            return r.json().get("translatedText", text)
        else:
            print(f"  LibreTranslate lỗi {r.status_code}, thử Google...")
            return translate_google(text, target)
    except Exception as e:
        print(f"  LibreTranslate lỗi: {e}, thử Google...")
        return translate_google(text, target)

def translate_google(text, target='vi'):
    """Dịch bằng Google Translate (dự phòng)"""
    if not text:
        return text
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        'client': 'gtx',
        'sl': 'auto',
        'tl': target,
        'dt': 't',
        'q': text[:2000]
    }
    try:
        r = requests.get(url, params=params, timeout=30)
        return ''.join([x[0] for x in r.json()[0] if x[0]]).strip()
    except:
        return text

def format_time(t):
    h = int(t//3600)
    m = int((t%3600)//60)
    s = int(t%60)
    ms = int((t%1)*1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wrap_text(text, max_len=38):
    if len(text) <= max_len:
        return text
    words = text.split(' ')
    lines = []
    cur = []
    cur_len = 0
    for w in words:
        if cur_len + len(w) + 1 <= max_len:
            cur.append(w)
            cur_len += len(w) + 1
        else:
            if cur:
                lines.append(' '.join(cur))
            cur = [w]
            cur_len = len(w) + 1
    if cur:
        lines.append(' '.join(cur))
    if len(lines) > 2:
        lines = lines[:2]
        if len(lines[1]) > 30:
            lines[1] = lines[1][:27] + '...'
    return '\\N'.join(lines)

print("=" * 50)
print("DICH PHIM - PHU DE TIENG VIET")
print("=" * 50)

# Bước 1: Nhận dạng
print("\n[1/4] Nhan dang giong noi...")
model = whisper.load_model(CONFIG['model'])
result = model.transcribe("input.mp4")
segments = result['segments']
print(f"  Tim thay {len(segments)} doan")

# Bước 2: Dịch từng đoạn
print("\n[2/4] Dang dich (co the cham nhung se hoan thanh)...")
translated = []
total = len(segments)

for i, seg in enumerate(segments):
    original = seg['text'].strip()
    print(f"  [{i+1}/{total}] Dang dich: {original[:40]}...")
    
    viet = translate_text(original, 'vi')
    translated.append({
        'start': seg['start'],
        'end': seg['end'],
        'text': viet
    })
    time.sleep(0.2)  # Tranh rate limit

# Bước 3: Tạo file SRT
print("\n[3/4] Tao file phu de SRT...")
with open('subtitle.srt', 'w', encoding='utf-8') as f:
    for i, sub in enumerate(translated):
        f.write(f"{i+1}\n")
        f.write(f"{format_time(sub['start'])} --> {format_time(sub['end'])}\n")
        f.write(f"{sub['text']}\n\n")

# Bước 4: Ghép video
print("\n[4/4] Ghep phu de vao video...")
style = f"FontName=Arial,FontSize={CONFIG['font_size']},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Alignment=2,MarginV={CONFIG['margin_v']}"
cmd = [
    'ffmpeg', '-i', 'input.mp4',
    '-vf', f"subtitles=subtitle.srt:force_style='{style}'",
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
    '-c:a', 'copy', '-y', 'output_dich.mp4'
]
subprocess.run(cmd, check=True)

print("\n" + "=" * 50)
print("HOAN THANH!")
print("File output_dich.mp4 da co phu de tieng Viet")
print("=" * 50)
