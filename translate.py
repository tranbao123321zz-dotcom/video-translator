# translate.py - Phiên bản tối ưu với phụ đề chạy theo từng câu, căn chỉnh khung hình

import whisper
import requests
import subprocess
import json
import re

# ================= CẤU HÌNH =================
CONFIG = {
    'whisper_model': 'base',      # tiny, base, small, medium
    'target_lang': 'vi',
    'max_line_width': 42,          # Số ký tự tối đa trên 1 dòng
    'max_lines': 2,                # Số dòng tối đa hiển thị cùng lúc
    'font_size': 24,
    'font_name': 'Arial',
    'font_color': '&H00FFFFFF',    # Trắng
    'outline_color': '&H00000000', # Viền đen
    'alignment': 2,                # 2 = giữa, dưới cùng
    'margin_v': 30,
    'position': 'bottom'           # bottom, top
}

# ================= HÀM DỊCH =================
def translate_text(text, target='vi'):
    """Dịch text giữ nguyên cấu trúc câu"""
    if not text or text.strip() == '':
        return text
    
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        'client': 'gtx',
        'sl': 'auto',
        'tl': target,
        'dt': 't',
        'q': text[:5000]
    }
    try:
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()
        translated = ''.join([item[0] for item in data[0] if item[0]])
        return translated.strip()
    except Exception as e:
        print(f"Lỗi dịch: {e}")
        return text

# ================= CẮT DÒNG THÔNG MINH =================
def wrap_text(text, max_width=42):
    """Cắt dòng theo từ, không cắt giữa chữ"""
    words = text.split()
    lines = []
    current_line = []
    current_length = 0
    
    for word in words:
        if current_length + len(word) + 1 <= max_width:
            current_line.append(word)
            current_length += len(word) + 1
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
            current_length = len(word) + 1
    
    if current_line:
        lines.append(' '.join(current_line))
    
    # Giới hạn số dòng
    if len(lines) > CONFIG['max_lines']:
        lines = lines[:CONFIG['max_lines']]
        lines[-1] = lines[-1][:-3] + '...'
    
    return '\\N'.join(lines)  # \N là xuống dòng trong ASS

# ================= GHÉP CÂU THEO NGỮ CẢNH =================
def merge_short_segments(segments, min_duration=0.8, max_duration=5.0):
    """Gộp các đoạn ngắn thành câu hoàn chỉnh"""
    merged = []
    current = None
    
    for seg in segments:
        text = seg['text'].strip()
        duration = seg['end'] - seg['start']
        
        # Nếu đoạn quá ngắn hoặc chưa kết thúc câu
        if not current:
            current = {
                'start': seg['start'],
                'end': seg['end'],
                'text': text
            }
        else:
            # Gộp nếu đoạn ngắn hoặc chưa có dấu câu kết thúc
            if duration < min_duration or (text and text[-1] not in '.!?。！？'):
                current['end'] = seg['end']
                current['text'] += ' ' + text
            else:
                merged.append(current)
                current = {
                    'start': seg['start'],
                    'end': seg['end'],
                    'text': text
                }
    
    if current:
        merged.append(current)
    
    # Cắt bớt đoạn quá dài
    for seg in merged:
        if len(seg['text']) > 200:
            seg['text'] = seg['text'][:197] + '...'
        seg['duration'] = seg['end'] - seg['start']
    
    return merged

# ================= TẠO FILE SRT =================
def create_srt(segments, output_path='subtitle.srt'):
    """Tạo file SRT với timing chính xác từng câu"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, seg in enumerate(segments):
            start = seg['start']
            end = seg['end']
            text = seg['text']
            
            # Định dạng thời gian
            start_str = f"{int(start//3600):02d}:{int(start//60)%60:02d}:{int(start%60):02d},{int((start%1)*1000):03d}"
            end_str = f"{int(end//3600):02d}:{int(end//60)%60:02d}:{int(end%60):02d},{int((end%1)*1000):03d}"
            
            f.write(f"{i+1}\n")
            f.write(f"{start_str} --> {end_str}\n")
            f.write(f"{text}\n\n")
    
    print(f"Đã tạo SRT với {len(segments)} dòng")
    return output_path

# ================= TẠO FILE ASS (ĐẸP HƠN) =================
def create_ass(segments, output_path='subtitle.ass', video_width=1920, video_height=1080):
    """Tạo file ASS với định dạng đẹp, hỗ trợ định vị khung hình"""
    
    # Xác định vị trí Y
    if CONFIG['position'] == 'top':
        position_y = 40
        alignment = 8  # Trên cùng giữa
    else:
        position_y = video_height - CONFIG['margin_v']
        alignment = CONFIG['alignment']
    
    # Header ASS
    ass_header = f"""[Script Info]
Title: Dịch tự động
ScriptType: v4.00+
WrapStyle: 0
PlayResX: {video_width}
PlayResY: {video_height}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{CONFIG['font_name']},{CONFIG['font_size']},{CONFIG['font_color']},&H000000FF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,2,1,{alignment},10,10,{CONFIG['margin_v']},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    # Ghi từng dòng
    ass_lines = []
    for i, seg in enumerate(segments):
        start = seg['start']
        end = seg['end']
        text = wrap_text(seg['text'], CONFIG['max_line_width'])
        
        start_str = f"0:{int(start//3600):01d}:{int(start//60)%60:02d}:{int(start%60):02d}.{int((start%1)*100):02d}"
        end_str = f"0:{int(end//3600):01d}:{int(end//60)%60:02d}:{int(end%60):02d}.{int((end%1)*100):02d}"
        
        ass_lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")
    
    # Ghi file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(ass_header)
        f.write('\n'.join(ass_lines))
    
    print(f"Đã tạo ASS với {len(segments)} dòng")
    return output_path

# ================= LẤY KÍCH THƯỚC VIDEO =================
def get_video_dimensions(video_path):
    """Lấy width và height của video"""
    cmd = [
        'ffprobe', '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'json', video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    data = json.loads(result.stdout)
    width = data['streams'][0]['width']
    height = data['streams'][0]['height']
    return width, height

# ================= GHÉP PHỤ ĐỀ VÀO VIDEO =================
def burn_subtitle(video_path, subtitle_path, output_path):
    """Ghép phụ đề vào video với chất lượng cao"""
    
    # Chọn filter dựa trên đuôi file
    if subtitle_path.endswith('.ass'):
        vf = f"ass={subtitle_path}"
    else:
        vf = f"subtitles={subtitle_path}:force_style='FontName={CONFIG['font_name']},FontSize={CONFIG['font_size']},PrimaryColour={CONFIG['font_color']},OutlineColour={CONFIG['outline_color']},Alignment={CONFIG['alignment']},MarginV={CONFIG['margin_v']}'"
    
    cmd = [
        'ffmpeg', '-i', video_path,
        '-vf', vf,
        '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
        '-c:a', 'copy',
        '-y', output_path
    ]
    
    subprocess.run(cmd, check=True)
    print(f"Đã ghép phụ đề: {output_path}")

# ================= MAIN =================
def main():
    print("=" * 50)
    print("DỊCH PHIM - PHỤ ĐỀ THEO TỪNG CÂU")
    print("=" * 50)
    
    # Bước 1: Nhận dạng giọng nói
    print("\n[1/5] Nhận dạng giọng nói...")
    model = whisper.load_model(CONFIG['whisper_model'])
    result = model.transcribe("input.mp4", word_timestamps=False)
    
    raw_segments = []
    for seg in result['segments']:
        raw_segments.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': seg['text'].strip()
        })
    print(f"  Nhận dạng: {len(raw_segments)} đoạn")
    
    # Bước 2: Ghép các đoạn ngắn
    print("\n[2/5] Ghép câu theo ngữ cảnh...")
    merged_segments = merge_short_segments(raw_segments)
    print(f"  Sau khi ghép: {len(merged_segments)} câu")
    
    # Bước 3: Dịch
    print("\n[3/5] Đang dịch sang tiếng Việt...")
    for i, seg in enumerate(merged_segments):
        seg['text'] = translate_text(seg['text'], CONFIG['target_lang'])
        if (i + 1) % 20 == 0:
            print(f"  Đã dịch: {i+1}/{len(merged_segments)}")
    print(f"  Hoàn thành dịch {len(merged_segments)} câu")
    
    # Bước 4: Lấy kích thước video
    print("\n[4/5] Lấy thông tin video...")
    width, height = get_video_dimensions("input.mp4")
    print(f"  Video: {width}x{height}")
    
    # Bước 5: Tạo file phụ đề và ghép
    print("\n[5/5] Tạo phụ đề và ghép vào video...")
    
    # Tạo file ASS (đẹp hơn SRT)
    ass_file = create_ass(merged_segments, 'subtitle.ass', width, height)
    
    # Tạo file SRT (dự phòng)
    srt_file = create_srt(merged_segments, 'subtitle.srt')
    
    # Ghép vào video
    burn_subtitle("input.mp4", ass_file, "output_dich.mp4")
    
    print("\n" + "=" * 50)
    print("HOÀN THÀNH!")
    print(f"  File MP4: output_dich.mp4")
    print(f"  File SRT: subtitle.srt")
    print(f"  File ASS: subtitle.ass")
    print("=" * 50)

if __name__ == "__main__":
    main()
