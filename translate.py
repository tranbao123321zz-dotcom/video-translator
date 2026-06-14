# translate.py - Phiên bản dịch theo từng câu thoại, phông chữ đẹp, căn chỉnh mọi video

import whisper
import requests
import subprocess
import re
import json

# ================= CẤU HÌNH PHỤ ĐỀ DỄ NHÌN =================
CONFIG = {
    'whisper_model': 'base',
    'target_lang': 'vi',
    'font_name': 'SF Pro Text',      # Font đẹp trên iPhone/Mac
    'font_size': 28,                  # To, dễ đọc
    'font_color': '&H00FFFFFF',       # Trắng
    'border_color': '&H00000000',     # Viền đen
    'bg_color': '&H80000000',         # Nền đen trong suốt
    'margin_v': 50,                   # Cách lề dưới
    'alignment': 2,                   # Giữa, dưới cùng
    'outline': 2,                     # Độ dày viền
    'shadow': 1,                      # Đổ bóng nhẹ
    'max_chars_per_line': 38,         # Tối đa ký tự mỗi dòng
    'merge_gap': 0.5                  # Ghép khoảng cách <0.5s
}

# ================= DỊCH GIỮ NGUYÊN CẤU TRÚC =================
def translate_line(text, target='vi'):
    """Dịch 1 câu đơn lẻ, giữ nguyên thì"""
    if not text or not text.strip():
        return text
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        'client': 'gtx',
        'sl': 'auto',
        'tl': target,
        'dt': 't',
        'q': text
    }
    try:
        r = requests.get(url, params=params, timeout=15)
        return ''.join([x[0] for x in r.json()[0] if x[0]]).strip()
    except:
        return text

# ================= CẮT DÒNG THÔNG MINH =================
def smart_wrap(text, max_len=38):
    """Cắt dòng theo từ, không cắt giữa chữ"""
    if len(text) <= max_len:
        return text
    
    words = text.split(' ')
    lines = []
    current = []
    current_len = 0
    
    for w in words:
        if current_len + len(w) + 1 <= max_len:
            current.append(w)
            current_len += len(w) + 1
        else:
            if current:
                lines.append(' '.join(current))
            current = [w]
            current_len = len(w) + 1
    if current:
        lines.append(' '.join(current))
    
    # Giới hạn 2 dòng
    if len(lines) > 2:
        lines = lines[:2]
        if len(lines[1]) > 30:
            lines[1] = lines[1][:27] + '...'
    
    return '\\N'.join(lines)  # \N = xuống dòng trong ASS

# ================= GHÉP CÁC ĐOẠN NGẮN THÀNH CÂU =================
def merge_segments(segments, gap=0.5):
    """Ghép các đoạn ngắn liên tiếp thành câu hoàn chỉnh"""
    if not segments:
        return []
    
    merged = []
    current = segments[0].copy()
    
    for seg in segments[1:]:
        # Ghép nếu khoảng cách nhỏ và không có dấu kết thúc câu
        time_gap = seg['start'] - current['end']
        text = seg['text'].strip()
        last_char = current['text'][-1] if current['text'] else ''
        
        if time_gap < gap and last_char not in '.!?。！？':
            current['end'] = seg['end']
            current['text'] += ' ' + text
        else:
            merged.append(current)
            current = seg.copy()
    
    merged.append(current)
    
    # Làm sạch text
    for seg in merged:
        seg['text'] = re.sub(r'\s+', ' ', seg['text'].strip())
    
    return merged

# ================= TẠO FILE ASS (PHỤ ĐỀ ĐẸP) =================
def create_ass(subtitles, video_width=1920, video_height=1080, output='subtitle.ass'):
    """Tạo file ASS với định dạng phụ đề hiện đại"""
    
    # Style đẹp
    style = f"""Style: Sub,{CONFIG['font_name']},{CONFIG['font_size']},{CONFIG['font_color']},{CONFIG['bg_color']},{CONFIG['border_color']},{CONFIG['border_color']},0,0,0,0,100,100,0,0,1,{CONFIG['outline']},{CONFIG['shadow']},{CONFIG['alignment']},10,10,{CONFIG['margin_v']},1"""
    
    header = f"""[Script Info]
Title: Dịch tự động
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
{style}

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    lines = []
    for i, sub in enumerate(subtitles):
        # Định dạng thời gian ASS
        start = sub['start']
        end = sub['end']
        start_str = f"0:{int(start//3600)}:{int(start//60)%60:02d}:{int(start%60):02d}.{int((start%1)*100):02d}"
        end_str = f"0:{int(end//3600)}:{int(end//60)%60:02d}:{int(end%60):02d}.{int((end%1)*100):02d}"
        
        # Cắt dòng
        text = smart_wrap(sub['text'], CONFIG['max_chars_per_line'])
        
        lines.append(f"Dialogue: 0,{start_str},{end_str},Sub,,0,0,0,,{text}")
    
    with open(output, 'w', encoding='utf-8') as f:
        f.write(header)
        f.write('\n'.join(lines))
    
    return output

# ================= TẠO FILE SRT DỰ PHÒNG =================
def create_srt(subtitles, output='subtitle.srt'):
    """Tạo file SRT đơn giản"""
    def fmt(t):
        h = int(t//3600)
        m = int((t%3600)//60)
        s = int(t%60)
        ms = int((t%1)*1000)
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
    
    with open(output, 'w', encoding='utf-8') as f:
        for i, sub in enumerate(subtitles):
            f.write(f"{i+1}\n")
            f.write(f"{fmt(sub['start'])} --> {fmt(sub['end'])}\n")
            f.write(f"{sub['text']}\n\n")
    return output

# ================= GHÉP VÀO VIDEO =================
def burn_subtitle(video, ass_file, output):
    """Ghép phụ đề ASS vào video với chất lượng cao"""
    cmd = [
        'ffmpeg', '-i', video,
        '-vf', f"ass={ass_file}",
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'copy',
        '-movflags', '+faststart',
        '-y', output
    ]
    subprocess.run(cmd, check=True)

# ================= MAIN =================
def main():
    print("\n" + "=" * 50)
    print("  DỊCH PHIM - PHỤ ĐỀ THEO THOẠI")
    print("  Font đẹp, dễ đọc trên mọi thiết bị")
    print("=" * 50 + "\n")
    
    # Bước 1: Nhận dạng giọng nói từng câu
    print("[1/4] Nhận dạng giọng nói (theo từng câu)...")
    model = whisper.load_model(CONFIG['whisper_model'])
    result = model.transcribe("input.mp4", language=None)
    raw = [{'start': s['start'], 'end': s['end'], 'text': s['text'].strip()} for s in result['segments']]
    print(f"  → {len(raw)} đoạn thô")
    
    # Bước 2: Ghép thành câu hoàn chỉnh
    print("[2/4] Ghép các đoạn ngắn thành câu...")
    merged = merge_segments(raw, CONFIG['merge_gap'])
    print(f"  → {len(merged)} câu")
    
    # Bước 3: Dịch từng câu
    print("[3/4] Dịch sang tiếng Việt (từng câu)...")
    for i, seg in enumerate(merged):
        print(f"  → Đang dịch {i+1}/{len(merged)}...", end='\r')
        seg['text'] = translate_line(seg['text'], CONFIG['target_lang'])
    print(f"\n  → Hoàn thành dịch {len(merged)} câu")
    
    # Bước 4: Tạo phụ đề đẹp
    print("[4/4] Tạo phụ đề đẹp và ghép vào video...")
    
    # Lấy kích thước video
    probe = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries', 'stream=width,height', '-of', 'json', 'input.mp4'], capture_output=True, text=True)
    dims = json.loads(probe.stdout)
    w, h = dims['streams'][0]['width'], dims['streams'][0]['height']
    
    # Tạo file ASS
    ass_file = create_ass(merged, w, h, 'subtitle.ass')
    create_srt(merged, 'subtitle.srt')  # Dự phòng
    
    # Ghép
    burn_subtitle('input.mp4', ass_file, 'output_dich.mp4')
    
    print("\n" + "=" * 50)
    print("  ✅ HOÀN THÀNH!")
    print("  📁 output_dich.mp4 - Video đã có phụ đề")
    print("  📄 subtitle.srt - File phụ đề riêng")
    print("=" * 50 + "\n")

if __name__ == "__main__":
    main()
