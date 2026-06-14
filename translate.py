# translate.py - 1 câu thoại = 1 dòng phụ đề, font căn chỉnh tự động theo video

import whisper
import requests
import subprocess
import json
import re

# ================= CẤU HÌNH =================
CONFIG = {
    'model': 'base',
    'target': 'vi',
    'font_name': 'Helvetica',
    'font_size_ratio': 0.045,      # 4.5% chiều cao video
    'margin_ratio': 0.05,          # 5% chiều cao video
    'max_chars': 45,
    'outline': 1.5,
    'shadow': 0.5
}

# ================= DỊCH =================
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

# ================= ĐỊNH DẠNG THỜI GIAN =================
def format_time(t):
    h = int(t // 3600)
    m = int((t % 3600) // 60)
    s = int(t % 60)
    ms = int((t % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# ================= CẮT DÒNG MỀM =================
def soft_wrap(text, max_len=45):
    """Cắt dòng nhưng ưu tiên giữ nguyên từ"""
    if len(text) <= max_len:
        return text
    
    # Tìm vị trí cắt tốt nhất
    cut = max_len
    for sep in [' ', ',', ';', '.']:
        pos = text.rfind(sep, 0, max_len)
        if pos > max_len * 0.4:
            cut = pos + 1
            break
    
    line1 = text[:cut].strip()
    line2 = text[cut:].strip()
    
    # Nếu dòng 2 vẫn dài, cắt tiếp
    if len(line2) > max_len:
        line2 = soft_wrap(line2, max_len)
    
    return line1 + '\\N' + line2

# ================= LẤY KÍCH THƯỚC VIDEO =================
def get_video_size(video_path):
    cmd = ['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', video_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    return data['streams'][0]['width'], data['streams'][0]['height']

# ================= TẠO FILE ASS (CHUẨN, ĐẸP) =================
def create_ass(subtitles, video_w, video_h, output='subtitle.ass'):
    """Tạo ASS với font chữ tỉ lệ theo video"""
    font_size = max(16, int(video_h * CONFIG['font_size_ratio']))
    margin_v = int(video_h * CONFIG['margin_ratio'])
    
    # Style chuyên nghiệp
    style = f"""Style: Sub,{CONFIG['font_name']},{font_size},&H00FFFFFF,&H00000000,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{CONFIG['outline']},{CONFIG['shadow']},2,10,10,{margin_v},1"""
    
    header = f"""[Script Info]
Title: Subtitle
ScriptType: v4.00+
WrapStyle: 2
PlayResX: {video_w}
PlayResY: {video_h}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    lines = []
    for sub in subtitles:
        start = sub['start']
        end = sub['end']
        
        # Định dạng ASS: 0:HH:MM:SS.cc
        start_str = f"0:{int(start//3600)}:{int((start%3600)//60):02d}:{int(start%60):02d}.{int((start%1)*100):02d}"
        end_str = f"0:{int(end//3600)}:{int((end%3600)//60):02d}:{int(end%60):02d}.{int((end%1)*100):02d}"
        
        text = soft_wrap(sub['text'], CONFIG['max_chars'])
        lines.append(f"Dialogue: 0,{start_str},{end_str},Sub,,0,0,0,,{text}")
    
    with open(output, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write('\n'.join(lines))
    
    print(f"  Font size: {font_size}px, Margin: {margin_v}px")
    return output

# ================= GHÉP VIDEO =================
def burn_subtitle(video, ass_file, output):
    cmd = ['ffmpeg', '-i', video, '-vf', f"ass={ass_file}", '-c:v', 'libx264', '-preset', 'fast', '-crf', '18', '-c:a', 'copy', '-movflags', '+faststart', '-y', output]
    subprocess.run(cmd, check=True)

# ================= MAIN =================
def main():
    print("\n" + "=" * 50)
    print("  DỊCH PHIM - 1 CÂU THOẠI = 1 PHỤ ĐỀ")
    print("  Font tự động căn theo video")
    print("=" * 50)
    
    # Bước 1: Lấy kích thước video
    print("\n[1/4] Đang đọc video...")
    w, h = get_video_size("input.mp4")
    print(f"  Video: {w}x{h}px")
    
    # Bước 2: Nhận dạng
    print("\n[2/4] Nhận dạng giọng nói...")
    model = whisper.load_model(CONFIG['model'])
    result = model.transcribe("input.mp4")
    segments = result['segments']
    print(f"  Tìm thấy {len(segments)} lượt thoại")
    
    # In mẫu
    print("\n  Mẫu thoại gốc:")
    for seg in segments[:3]:
        print(f"    [{seg['start']:.1f}s] {seg['text'][:50]}")
    
    # Bước 3: Dịch (giữ nguyên từng lượt)
    print("\n[3/4] Đang dịch từng lượt...")
    translated = []
    for i, seg in enumerate(segments):
        original = seg['text'].strip()
        viet = translate_text(original, CONFIG['target'])
        translated.append({'start': seg['start'], 'end': seg['end'], 'text': viet})
        print(f"  [{i+1}/{len(segments)}] {original[:35]} → {viet[:35]}")
    
    # Bước 4: Tạo ASS và ghép
    print("\n[4/4] Tạo phụ đề và ghép video...")
    ass_file = create_ass(translated, w, h, 'subtitle.ass')
    burn_subtitle('input.mp4', ass_file, 'output_dich.mp4')
    
    # Xuất SRT dự phòng
    with open('subtitle.srt', 'w', encoding='utf-8') as f:
        for i, sub in enumerate(translated):
            f.write(f"{i+1}\n{format_time(sub['start'])} --> {format_time(sub['end'])}\n{sub['text']}\n\n")
    
    print("\n" + "=" * 50)
    print("  ✅ HOÀN THÀNH!")
    print(f"  📁 output_dich.mp4 ({w}x{h})")
    print(f"  📄 subtitle.srt")
    print("  💡 Phụ đề: 1 câu thoại = 1 dòng, font tự động")
    print("=" * 50)

if __name__ == "__main__":
    main()
