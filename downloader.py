import yt_dlp
import time
import os

def download_media(url, user_id, media_type='video'):
    timestamp = int(time.time())
    
    # ভিডিও নাকি অডিও সেটির ফরম্যাট সেট করা
    if media_type == 'video':
        filename = f"video_{user_id}_{timestamp}.mp4"
        format_str = 'bestvideo[ext=mp4][filesize<50M]+bestaudio[ext=m4a]/best[ext=mp4][filesize<50M]/best'
    else:
        filename = f"audio_{user_id}_{timestamp}.mp3"
        format_str = 'bestaudio[ext=m4a]/bestaudio/best'

    ydl_opts = {
        'format': format_str,
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)'
        }
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
        if os.path.exists(filename):
            return filename
        return None
    except Exception as e:
        print(f"DL Error: {e}")
        return None
