import whisper
import requests
import subprocess
import time
import sys

# Cấu hình
WHISPER_MODEL = "base"
TARGET_LANG = "vi"
FONT_SIZE = 24

def translate_text(text, target="vi", retry=3):
    """Dịch text với retry khi bị lỗi"""
    if not text or text.strip() == "":
        return text
    
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target,
        "dt": "t",
        "q": text[:3000]
    }
    
    for attempt in range(retry):
        try:
            resp = requests.get(url, params=params, timeout=60)
            if resp.status_code == 200:
                data = resp.json()
                result = "".join([item[0] for item in data[0] if item[0]])
                return result
            elif resp.status_code == 429:
                print(f"  Google chặn, đợi {5*(attempt+1)} giây...")
                time.sleep(5 * (attempt + 1))
            else:
                print(f"  Lỗi HTTP {resp.status_code}")
        except Exception as e:
            print(f"  Lỗi: {e}, thử lại {attempt+1}/{retry}")
            time.sleep(3)
    
    print(f"  Dịch thất bại, giữ nguyên: {text[:50]}...")
    return text

def format_time(seconds):
    """Chuyển seconds sang định dạng SRT"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

def main():
    print("=" * 40)
    print("DICH PHIM - PHU DE TIENG VIET")
    print("=" * 40)
    
    # Kiểm tra file input
    import os
    if not os.path.exists("input.mp4"):
        print("Loi: Khong tim thay input.mp4")
        sys.exit(1)
    
    # Bước 1: Nhận dạng
    print("\n[1/3] Dang nhan dang giong noi...")
    model = whisper.load_model(WHISPER_MODEL)
    result = model.transcribe("input.mp4")
    segments = result["segments"]
    print(f"  Tim thay {len(segments)} doan")
    
    # Bước 2: Dịch từng đoạn
    print("\n[2/3] Dang dich sang tieng Viet...")
    translated = []
    total = len(segments)
    
    for i, seg in enumerate(segments):
        original = seg["text"].strip()
        print(f"  Dang dich {i+1}/{total}: {original[:50]}...")
        
        viet = translate_text(original, TARGET_LANG)
        translated.append({
            "index": i + 1,
            "start": seg["start"],
            "end": seg["end"],
            "original": original,
            "text": viet
        })
        
        # Delay để tránh bị Google chặn
        time.sleep(0.3)
    
    # Bước 3: Tạo file SRT
    print("\n[3/3] Dang tao file phu de...")
    srt_lines = []
    for sub in translated:
        srt_lines.append(str(sub["index"]))
        srt_lines.append(f"{format_time(sub['start'])} --> {format_time(sub['end'])}")
        srt_lines.append(sub["text"])
        srt_lines.append("")
    
    with open("subtitle.srt", "w", encoding="utf-8") as f:
        f.write("\n".join(srt_lines))
    
    # Bước 4: Ghép phụ đề
    print("\n[4/4] Dang ghep phu de vao video...")
    style = f"FontName=Arial,FontSize={FONT_SIZE},PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,Alignment=2,MarginV=30"
    cmd = [
        "ffmpeg", "-i", "input.mp4",
        "-vf", f"subtitles=subtitle.srt:force_style='{style}'",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "copy", "-y", "output_dich.mp4"
    ]
    subprocess.run(cmd, check=True)
    
    print("\n" + "=" * 40)
    print("HOAN THANH!")
    print("  output_dich.mp4 - video da co phu de Viet")
    print("  subtitle.srt - file phu de rieng")
    print("=" * 40)

if __name__ == "__main__":
    main()
