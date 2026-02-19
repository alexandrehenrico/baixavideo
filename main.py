import yt_dlp

url = input("Cole a URL do vídeo: ")

ydl_opts = {
    'outtmpl': 'downloads/%(title)s.%(ext)s'
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    ydl.download([url])
