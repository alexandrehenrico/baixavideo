from flask import Flask, render_template, request, jsonify, send_file, after_this_request, Response
import yt_dlp
import os
import time
import json
import io
import logging
import glob
import urllib.request
from auth_resolver import VisionXAuthResolver

app = Flask(__name__)

# Config logging
logging.basicConfig(level=logging.DEBUG)

# Ensure downloads folder exists
DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# FFmpeg location - auto-detect
FFMPEG_WIN = r'C:\Users\Alexandre Henrique\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0.1-full_build\bin'
if os.path.exists(FFMPEG_WIN):
    FFMPEG_PATH = FFMPEG_WIN
else:
    # Linux / Render / Docker - ffmpeg is in PATH
    FFMPEG_PATH = '/usr/bin'

# Store progress data for each client
progress_data = {}

# Initialize Robust Auth Resolver
resolver = VisionXAuthResolver(app.logger)

def get_ydl_opts(extra_opts=None):
    base_opts = {
        'ffmpeg_location': FFMPEG_PATH,
        'quiet': False, # Allow diagnostic logs
    }
    
    # Injeta lógica de autenticação e bypass de rede
    full_opts = resolver.get_dynamic_opts(base_opts)
    
    if extra_opts:
        full_opts.update(extra_opts)
    return full_opts

@app.route('/')
def home():
    return render_template('index.html')

# Simple in-memory cache
trending_cache = {
    'data': None,
    'timestamp': 0
}

@app.route('/trending', methods=['GET'])
def get_trending():
    global trending_cache
    current_time = time.time()
    
    # Return cached data if fresh (less than 1 hour old)
    if trending_cache['data'] and (current_time - trending_cache['timestamp'] < 3600):
        return jsonify({'results': trending_cache['data']})

    try:
        # Fetch trending/popular videos.
        # We search for a generic term or use a playlist if desired, 
        # but 'ytsearch20:trending' is a good heuristic.
        # Using 'extract_flat' is CRITICAL for speed.
        ydl_opts = get_ydl_opts({
            'quiet': True,
            'extract_flat': 'in_playlist', # Get metadata without deep extraction
            'default_search': 'ytsearch20', 
            'noplaylist': True,
            'ignoreerrors': True,
        })
        
        # Searching for "music" or generic term as landing page content
        # ideally we'd use a specific feed URL, but search is safer across regions
        query = "trending music gaming" 
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch20:{query}", download=False)
            results = _parse_results(info)
            
            # Update cache
            trending_cache['data'] = results
            trending_cache['timestamp'] = current_time
            
            return jsonify({'results': results})
    except Exception as e:
        app.logger.error(f"Error fetching trending: {e}")
        return jsonify({'results': []})

def _parse_results(info):
    results = []
    if 'entries' in info:
        for entry in info['entries']:
            if not entry: continue
            
            title = entry.get('title')
            video_id = entry.get('id')
            thumbnail = entry.get('thumbnail') 
            if not thumbnail and video_id:
                thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                
            video_url = entry.get('url') or entry.get('webpage_url')
            if video_id and not video_url:
                 video_url = f"https://www.youtube.com/watch?v={video_id}"

            if video_url:
                results.append({
                    'id': video_id,
                    'title': title,
                    'thumbnail': thumbnail,
                    'duration': entry.get('duration'),
                    'uploader': entry.get('uploader'),
                    'url': video_url,
                    'view_count': entry.get('view_count')
                })
    return results


@app.route('/search', methods=['GET'])
def search_video():
    query = request.args.get('q')
    if not query:
        return jsonify({'error': 'Termo de busca não fornecido'}), 400

    try:
        # Optimized search for speed
        ydl_opts = get_ydl_opts({
            'quiet': True,
            'extract_flat': 'in_playlist', # KEY for speed
            'default_search': 'ytsearch20',
            'noplaylist': True,
            'ignoreerrors': True,
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(query, download=False)
            except Exception as e:
                app.logger.error(f"Search failed for query '{query}': {e}")
                return jsonify({'error': 'Erro ao buscar vídeos. Tente novamente.'}), 500
            
        results = process_results(info)
        return jsonify({'results': results})

    except Exception as e:
        app.logger.error(f"Erro na busca: {e}")
        return jsonify({'error': str(e)}), 500

def process_results(info):
    results = []
    entries = []
    
    if 'entries' in info:
        entries = info['entries']
    elif 'id' in info or 'title' in info:
        # specific video result
        entries = [info]
        
    for entry in entries:
        if not entry: continue
        
        # With extract_flat, we get basic info.
        video_id = entry.get('id')
        title = entry.get('title')
        # For thumbnails, flat extraction might not give full list, but usually gives a URL or we can construct it
        thumbnail = entry.get('thumbnail') 
        if not thumbnail and video_id:
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            
        video_url = entry.get('url') or entry.get('webpage_url')
        if video_id and not video_url:
                video_url = f"https://www.youtube.com/watch?v={video_id}"

        if video_url:
            results.append({
                'id': video_id,
                'title': title,
                'thumbnail': thumbnail,
                'duration': entry.get('duration'),
                'uploader': entry.get('uploader'),
                'url': video_url,
                'view_count': entry.get('view_count')
            })
    return results



# Global cancellation flags
cancel_flags = set()

@app.route('/cancel', methods=['POST'])
def cancel_download():
    data = request.get_json()
    client_id = data.get('client_id')
    if client_id:
        cancel_flags.add(client_id)
        return jsonify({'status': 'cancelled'})
    return jsonify({'error': 'Client ID required'}), 400

@app.route('/download', methods=['POST'])
def download_video():
    data = request.get_json()
    url = data.get('url')
    client_id = data.get('client_id')
    fmt_option = data.get('format', 'bestvideo+bestaudio/best')

    if not url:
        return jsonify({'error': 'URL não fornecida'}), 400

    filename = None
    try:
        def progress_hook(d):
            if client_id and client_id in cancel_flags:
                raise Exception("CANCEL_DOWNLOAD")

            if d['status'] == 'downloading':
                p_str = d.get('_percent_str', '').strip()
                size_str = d.get('_total_bytes_str') or d.get('_total_bytes_estimate_str') or 'Unknown size'
                speed_str = d.get('_speed_str', 'N/A')
                eta_str = d.get('_eta_str', 'N/A')
                
                msg = f"[download] {p_str} of {size_str} ETA {eta_str} at {speed_str}"
                
                if client_id:
                    progress_data[client_id] = msg

            elif d['status'] == 'finished':
                if client_id:
                    progress_data[client_id] = f"[download] 100% - Processando arquivo..."

        ydl_opts = get_ydl_opts({
            'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'progress_hooks': [progress_hook],
        })

        target_format = fmt_option

        if fmt_option == 'thumbnail':
            # Download thumbnail as a proper image file
            # First, extract info to get video details and thumbnail URL
            ydl_opts_info = get_ydl_opts({
                'quiet': True,
                'noplaylist': True,
            })
            with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
                info = ydl.extract_info(url, download=False)
            
            video_id = info.get('id', 'thumbnail')
            title = info.get('title', 'thumbnail').replace('/', '_').replace('\\', '_')
            
            # Get the highest quality thumbnail URL
            thumb_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
            
            # Download the image
            thumb_filename = os.path.join(DOWNLOAD_FOLDER, f"{title}.jpg")
            
            if client_id:
                progress_data[client_id] = "[download] Baixando capa do vídeo..."
            
            try:
                urllib.request.urlretrieve(thumb_url, thumb_filename)
                # Check if we got a valid image (maxresdefault might 404)
                if os.path.getsize(thumb_filename) < 1000:
                    os.remove(thumb_filename)
                    # Fallback to hqdefault
                    thumb_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                    urllib.request.urlretrieve(thumb_url, thumb_filename)
            except Exception:
                # Fallback
                thumb_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
                urllib.request.urlretrieve(thumb_url, thumb_filename)
            
            filename = thumb_filename
            
            if client_id:
                progress_data[client_id] = "[download] 100% - Capa baixada!"
            
        elif fmt_option in ['mp3', 'm4a', 'wav']:
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': fmt_option,
                'preferredquality': '192',
            }]
            target_format = fmt_option
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
                pre, ext = os.path.splitext(filename)
                filename = f"{pre}.{target_format}"
            
        else:
            # Default: best video + audio
            ydl_opts['format'] = fmt_option
            ydl_opts['merge_output_format'] = 'mp4'
            target_format = 'mp4'

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                filename = ydl.prepare_filename(info)
            
        if not filename or not os.path.exists(filename):
            app.logger.error(f"Filename not found: {filename}")
            return jsonify({'error': 'Arquivo não encontrado após download'}), 500

        download_name = os.path.basename(filename)

        # Determine correct mimetype
        ext_lower = os.path.splitext(filename)[1].lower()
        mime_map = {
            '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png',
            '.webp': 'image/webp', '.mp3': 'audio/mpeg', '.m4a': 'audio/mp4',
            '.wav': 'audio/wav', '.mp4': 'video/mp4',
        }
        mimetype = mime_map.get(ext_lower, 'application/octet-stream')

        # Use after_this_request to delete the file after sending
        @after_this_request
        def remove_file(response):
            try:
                if filename and os.path.exists(filename):
                    os.remove(filename)
                    if client_id in progress_data:
                        progress_data[client_id] = "Envio concluído!"
            except Exception as e:
                app.logger.error(f"Erro ao remover arquivo: {e}")
            return response

        return send_file(
            filename,
            as_attachment=True,
            download_name=download_name,
            mimetype=mimetype
        )

    except Exception as e:
        if "CANCEL_DOWNLOAD" in str(e):
            if client_id:
                progress_data[client_id] = "Download cancelado pelo usuário."
            return jsonify({'error': 'Download cancelado.'}), 499
        app.logger.error(f"Erro no download: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/progress/<client_id>')
def progress(client_id):
    def generate():
        last_message = ""
        start_time = time.time()
        while time.time() - start_time < 600:
            if client_id in progress_data:
                data = progress_data[client_id]
                if data != last_message:
                    yield f"data: {json.dumps({'message': data})}\n\n"
                    last_message = data
                
                if "Envio concluído!" in data or "Erro" in data:
                    break
            else:
                 pass
            time.sleep(0.5)
            
        if client_id in progress_data:
            del progress_data[client_id]

    return Response(generate(), mimetype='text/event-stream')

if __name__ == '__main__':
    if os.path.exists(DOWNLOAD_FOLDER):
        for f in os.listdir(DOWNLOAD_FOLDER):
            try:
                fp = os.path.join(DOWNLOAD_FOLDER, f)
                if os.path.isfile(fp):
                    os.remove(fp)
            except:
                pass
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, threaded=True, host='0.0.0.0', port=port)
