# translate.py - Giữ nguyên từng đoạn thoại, chỉ dịch, không gộp lung tung

import whisper
import requests
import subprocess
import re

CONFIG = {
    'model': 'base',
    'target': 'vi',
    'font_size': 28,
    'margin_v': 50,
    'max_chars': 42
}

def translate_text(text, target='vi'):
    if not text or not text.strip():
        return text
    # LibreTranslate
    try:
        r = requests.post("https://libretranslate.com/translate", json={"q": text, "source": "auto", "target": target}, timeout=30)
        if r.status_code == 200:
            return r.json().get("translatedText", text)
    except:
        pass
    # Google fallback
    try:
        params = {'client': 'gtx', 'sl': 'auto', 'tl': target, 'dt': 't', 'q': text}
        r = requests.get("https://translate.googleapis.com/translate_a/single", params=params, timeout=30)
        return ''.join([x[0] for x in r.json()[0] if x[0]])
    except:
        return text

def format_time(t):
    h, m = int(t//3600), int((t%3600)//60)
    s, ms = int(t%60), int((t%1)*1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wrap_line(text, max_len=42):
    if len(text) <= max_len:
        return text
    cut = text.rfind(' ', 0, max_len)
    if cut == -1:
        cut = max_len
    return text[:cut] + '\\N' + text[cut:].strip()

print("=" * 50)
print("DICH PHIM - GIU NGUYEN TUNG LUOT THOAI")
print("=" * 50)

# Bước 1: Nhận dạng (Whisper tự cắt theo thoại)
print("\n[1/3] Nhan dang giong noi...")
model = whisper.load_model(CONFIG['model'])
result = model.transcribe("input.mp4", word_timestamps=False)
segments = result['segments']
print(f"  Tim thay {len(segments)} luot thoai")

# In thử 5 luot thoai dau
print("\n  Cac luot thoai goc:")
for seg in segments[:5]:
    print(f"    [{seg['start']:.1f}s] {seg['text'][:60]}")

# Bước 2: Dịch từng luot thoai (khong gop)
print("\n[2/3] Dang dich tung luot thoai...")
translated = []
for i, seg in enumerate(segments):
    original = seg['text'].strip()
    viet = translate_text(original, CONFIG['target'])
    translated.append({
        'start': seg['start'],
        'end': seg['end'],
        'text': viet
    })
    print(f"  [{i+1}/{len(segments)}] {original[:40]} -> {viet[:40]}")
    # Khong delay de tranh bi chan, nhung danh hoi cham

# Bước 3: Tao file SRT
print("\n[3/3] Tao file phu de SRT...")
with open('subtitle.srt', 'w', encoding='utf-8') as f:
    for i, sub in enumerate(translated):
        if not sub['text']:
            continue
        text = wrap_line(sub['text'], CONFIG['max_chars'])
        f.write(f"{i+1}\n")
        f.write(f"{format_time(sub['start'])} --> {format_time(sub['end'])}\n")
        f.write(f"{text}\n\n")

# Bước 4: Ghep vao video
style = f"FontName=Arial,FontSize={CONFIG['font_size']},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Alignment=2,MarginV={CONFIG['margin_v']}"
cmd = ['ffmpeg', '-i', 'input.mp4', '-vf', f"subtitles=subtitle.srt:force_style='{style}'", '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'copy', '-y', 'output_dich.mp4']
subprocess.run(cmd, check=True)

print("\n" + "=" * 50)
print("HOAN THANH!")
print(f"  {len(translated)} luot thoai duoc giu nguyen")
print("  output_dich.mp4 - phu de theo tung luot noi")
print("=" * 50)
