import whisper
import requests
import subprocess
import re
import time

CONFIG = {
    'model': 'base',
    'target': 'vi',
    'font_size': 28,
    'margin_v': 50,
    'min_segment_len': 1.0,      # Đoạn dưới 1s sẽ bị gộp
    'max_line_chars': 40
}

def translate_text(text, target='vi'):
    if not text or not text.strip():
        return text
    url = "https://libretranslate.com/translate"
    try:
        r = requests.post(url, json={"q": text, "source": "auto", "target": target, "format": "text"}, timeout=60)
        if r.status_code == 200:
            return r.json().get("translatedText", text)
    except:
        pass
    # Fallback Google
    try:
        url = "https://translate.googleapis.com/translate_a/single"
        params = {'client': 'gtx', 'sl': 'auto', 'tl': target, 'dt': 't', 'q': text[:2000]}
        r = requests.get(url, params=params, timeout=30)
        return ''.join([x[0] for x in r.json()[0] if x[0]]).strip()
    except:
        return text

def merge_segments(segments):
    """Ghép các đoạn ngắn thành câu hoàn chỉnh"""
    if not segments:
        return []
    
    merged = []
    current = segments[0].copy()
    
    for seg in segments[1:]:
        gap = seg['start'] - current['end']
        last_char = current['text'][-1] if current['text'] else ''
        is_end_of_sentence = last_char in '.!?。！？'
        
        # Ghép nếu: khoảng cách nhỏ HOẶC chưa kết thúc câu
        if gap < 1.0 or not is_end_of_sentence:
            current['end'] = seg['end']
            current['text'] += ' ' + seg['text']
        else:
            merged.append(current)
            current = seg.copy()
    
    merged.append(current)
    
    # Làm sạch text
    for seg in merged:
        seg['text'] = re.sub(r'\s+', ' ', seg['text'].strip())
        # Xóa các cụm vô nghĩa
        seg['text'] = re.sub(r'\b\w\b\s+', '', seg['text'])  # Xóa chữ đơn lẻ
        seg['text'] = re.sub(r'\s+', ' ', seg['text'])
    
    return merged

def format_time(t):
    h = int(t//3600)
    m = int((t%3600)//60)
    s = int(t%60)
    ms = int((t%1)*1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def wrap_text(text, max_len=40):
    """Cắt dòng nhưng không cắt giữa câu hoàn chỉnh"""
    if len(text) <= max_len:
        return text
    
    # Tìm vị trí cắt tốt nhất (dấu phẩy, dấu cách)
    cut_pos = max_len
    for sep in [' ', ',', ';']:
        pos = text.rfind(sep, 0, max_len)
        if pos > max_len // 2:
            cut_pos = pos
            break
    
    line1 = text[:cut_pos].strip()
    line2 = text[cut_pos:].strip()
    
    if len(line2) > max_len:
        line2 = line2[:max_len-3] + '...'
    
    return line1 + '\\N' + line2 if line2 else line1

print("=" * 50)
print("DICH PHIM - GHEP CAU THONG MINH")
print("=" * 50)

# Bước 1: Nhận dạng
print("\n[1/4] Nhan dang giong noi...")
model = whisper.load_model(CONFIG['model'])
result = model.transcribe("input.mp4")
raw = [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip()} for s in result['segments']]
print(f"  Raw: {len(raw)} doan")

# Bước 2: Ghép câu
print("\n[2/4] Ghep cac doan ngan thanh cau...")
merged = merge_segments(raw)
print(f"  Sau ghep: {len(merged)} cau")

# In thử vài câu đầu
for i, seg in enumerate(merged[:5]):
    print(f"  Câu {i+1}: {seg['text'][:60]}...")

# Bước 3: Dịch
print("\n[3/4] Dang dich sang tieng Viet...")
for i, seg in enumerate(merged):
    if seg['text']:
        seg['text'] = translate_text(seg['text'], CONFIG['target'])
        if (i+1) % 10 == 0:
            print(f"  Da dich {i+1}/{len(merged)}")
    time.sleep(0.2)

# Bước 4: Tạo SRT
print("\n[4/4] Tao file phu de...")
with open('subtitle.srt', 'w', encoding='utf-8') as f:
    for i, seg in enumerate(merged):
        if not seg['text']:
            continue
        text = wrap_text(seg['text'], CONFIG['max_line_chars'])
        f.write(f"{i+1}\n")
        f.write(f"{format_time(seg['start'])} --> {format_time(seg['end'])}\n")
        f.write(f"{text}\n\n")

# Bước 5: Ghép video
style = f"FontName=Arial,FontSize={CONFIG['font_size']},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Alignment=2,MarginV={CONFIG['margin_v']}"
cmd = ['ffmpeg', '-i', 'input.mp4', '-vf', f"subtitles=subtitle.srt:force_style='{style}'", '-c:v', 'libx264', '-preset', 'fast', '-crf', '23', '-c:a', 'copy', '-y', 'output_dich.mp4']
subprocess.run(cmd, check=True)

print("\n" + "=" * 50)
print("HOAN THANH!")
print("output_dich.mp4 - Phu de da duoc ghep thanh cau")
print("=" * 50)
