import whisper
import requests
import subprocess
import json
import time

CONFIG = {
    'model': 'base',
    'target': 'vi',
    'font_size_ratio': 0.045,
    'margin_ratio': 0.05,
    'max_chars': 45
}

def translate_text(text, target='vi'):
    """Dịch text, in lỗi ra màn hình"""
    if not text or not text.strip():
        return text
    
    print(f"  Đang dịch: {text[:50]}...")
    
    # Thử LibreTranslate
    try:
        url = "https://libretranslate.com/translate"
        payload = {"q": text, "source": "auto", "target": target, "format": "text"}
        r = requests.post(url, json=payload, timeout=30)
        if r.status_code == 200:
            result = r.json().get("translatedText", text)
            print(f"    LibreTranslate OK: {result[:40]}...")
            return result
        else:
            print(f"    LibreTranslate lỗi {r.status_code}")
    except Exception as e:
        print(f"    LibreTranslate exception: {e}")
    
    # Thử Google Translate
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {'client': 'gtx', 'sl': 'auto', 'tl': target, 'dt': 't', 'q': text}
        r = requests.get(url, params=params, timeout=30)
        if r.status_code == 200:
            result = ''.join([x[0] for x in r.json()[0] if x[0]]).strip()
            print(f"    Google OK: {result[:40]}...")
            return result
        else:
            print(f"    Google lỗi {r.status_code}")
    except Exception as e:
        print(f"    Google exception: {e}")
    
    print(f"    DỊCH THẤT BẠI, giữ nguyên: {text[:40]}")
    return text

def format_time(t):
    h = int(t//3600)
    m = int((t%3600)//60)
    s = int(t%60)
    ms = int((t%1)*1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def soft_wrap(text, max_len=45):
    if len(text) <= max_len:
        return text
    cut = text.rfind(' ', 0, max_len)
    if cut == -1:
        cut = max_len
    return text[:cut] + '\\N' + text[cut:].strip()

def get_video_size(video_path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return data['streams'][0]['width'], data['streams'][0]['height']

def create_ass(subtitles, video_w, video_h, output='subtitle.ass'):
    font_size = max(16, int(video_h * CONFIG['font_size_ratio']))
    margin_v = int(video_h * CONFIG['margin_ratio'])
    
    header = f"""[Script Info]
Title: Subtitle
ScriptType: v4.00+
WrapStyle: 2
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Sub,Helvetica,{font_size},&H00FFFFFF,&H00000000,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,1.5,0.5,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    lines = []
    for sub in subtitles:
        start = sub['start']
        end = sub['end']
        start_str = f"0:{int(start//3600)}:{int((start%3600)//60):02d}:{int(start%60):02d}.{int((start%1)*100):02d}"
        end_str = f"0:{int(end//3600)}:{int((end%3600)//60):02d}:{int(end%60):02d}.{int((end%1)*100):02d}"
        text = soft_wrap(sub['text'], CONFIG['max_chars'])
        lines.append(f"Dialogue: 0,{start_str},{end_str},Sub,,0,0,0,,{text}")
    
    with open(output, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write('\n'.join(lines))
    return output

def burn_subtitle(video, ass_file, output):
    cmd = ['ffmpeg', '-i', video, '-vf', f"ass={ass_file}", '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-c:a', 'copy', '-y', output]
    subprocess.run(cmd, check=True)

print("=" * 50)
print("DICH PHIM - CO LOG CHI TIET")
print("=" * 50)

# Bước 1: Lấy kích thước video
w, h = get_video_size("input.mp4")
print(f"\n[1/4] Video: {w}x{h}px")

# Bước 2: Nhận dạng
print("\n[2/4] Nhan dang giong noi...")
model = whisper.load_model(CONFIG['model'])
result = model.transcribe("input.mp4")
segments = result['segments']
print(f"  Tim thay {len(segments)} luot thoai")

# Bước 3: Dịch (có log chi tiết)
print("\n[3/4] Dang dich tung luot (xem log ben duoi)...")
translated = []
for i, seg in enumerate(segments):
    original = seg['text'].strip()
    print(f"\n--- Luot {i+1}/{len(segments)} ---")
    viet = translate_text(original, CONFIG['target'])
    translated.append({'start': seg['start'], 'end': seg['end'], 'text': viet})
    time.sleep(0.3)

# Bước 4: Tạo phụ đề và ghép
print("\n[4/4] Tao phu de va ghep video...")
ass_file = create_ass(translated, w, h, 'subtitle.ass')
burn_subtitle('input.mp4', ass_file, 'output_dich.mp4')

# Xuất SRT
with open('subtitle.srt', 'w', encoding='utf-8') as f:
    for i, sub in enumerate(translated):
        f.write(f"{i+1}\n{format_time(sub['start'])} --> {format_time(sub['end'])}\n{sub['text']}\n\n")

print("\n" + "=" * 50)
print("HOAN THANH! Kiem tra log phia tren de biet loi dich")
print("=" * 50)
