# web_app/web_app.py - Updated discover endpoint
import os
import json
import subprocess
import time
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DISCOVERY_DIR = BASE_DIR / 'youtube_discovery'
DOWNLOAD_SCRIPT = BASE_DIR / 'ytdownload' / 'working_downloader_fixed.py'
UPLOAD_SCRIPT = BASE_DIR / 'ytupload' / 'yt_uploader_auto.py'
UPLOADED_LOG = BASE_DIR / 'ytupload' / 'uploaded_videos.log'

@app.route('/')
def index():
    return render_template('index.html')

# web_app/web_app.py - Updated discover endpoint with better config
@app.route('/api/discover', methods=['POST'])
def discover():
    """Run YouTube discovery with given search terms"""
    try:
        data = request.get_json()
        search_terms = data.get('search_terms', ['python programming'])
        max_results = data.get('max_results', 10)
        
        # Get API key from environment
        api_key = os.environ.get('YOUTUBE_API_KEY', '')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'YOUTUBE_API_KEY environment variable not set'})
        
        # Create a .env file in the discovery directory
        env_file = DISCOVERY_DIR / '.env'
        with open(env_file, 'w') as f:
            f.write(f"YOUTUBE_API_KEY={api_key}\n")
            f.write(f"SEARCH_TERMS={','.join(search_terms)}\n")
            f.write(f"MAX_RESULTS_PER_TERM={max_results}\n")
            f.write(f"OUTPUT_DIR=youtube_discovery_results\n")
        
        # Also create a config.py override if needed
        config_file = DISCOVERY_DIR / 'config.py'
        with open(config_file, 'r') as f:
            config_content = f.read()
        
        print(f"Running discovery with terms: {search_terms}")
        print(f"API Key present: {bool(api_key)}")
        
        # Run the discovery script
        result = subprocess.run(
            ['python', str(DISCOVERY_DIR / 'main.py')],
            cwd=str(DISCOVERY_DIR),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, 'YOUTUBE_API_KEY': api_key}
        )
        
        print(f"Discovery stdout: {result.stdout}")
        print(f"Discovery stderr: {result.stderr}")
        
        # Look for the results file
        results_dir = DISCOVERY_DIR / 'youtube_discovery_results' / 'json'
        results_file = results_dir / 'analysis_report.json'
        
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            return jsonify({
                'success': True,
                'videos': report.get('top_videos', []),
                'stats': report.get('statistics', {}),
                'message': f"Found {len(report.get('top_videos', []))} videos"
            })
        else:
            return jsonify({
                'success': False, 
                'error': f'No results found. Script output: {result.stdout[:500]}'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Discovery timed out after 5 minutes'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})






@app.route('/api/download', methods=['POST'])
def download():
    """Download a video using yt-dlp"""
    try:
        data = request.get_json()
        video_url = data.get('url')
        video_title = data.get('title', 'video')
        output_folder = data.get('output_folder', '/tmp/downloads')
        
        # Create output folder
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # Check if yt-dlp is installed
        check_ytdlp = subprocess.run(['which', 'yt-dlp'], capture_output=True)
        if check_ytdlp.returncode != 0:
            # Install yt-dlp
            subprocess.run(['pip', 'install', 'yt-dlp'], capture_output=True)
        
        # Download command
        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '-o', f'{output_folder}/%(title)s.%(ext)s',
            '--no-playlist',
            '--quiet',
            video_url
        ]
        
        print(f"Downloading: {video_url}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            # Find the downloaded file
            downloaded_files = list(Path(output_folder).glob('*.mp4'))
            if downloaded_files:
                latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
                return jsonify({
                    'success': True, 
                    'message': f'Downloaded to {latest_file.name}',
                    'file': str(latest_file)
                })
            else:
                return jsonify({'success': True, 'message': 'Download completed'})
        else:
            return jsonify({'success': False, 'error': result.stderr})
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Download timed out'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})







@app.route('/api/upload', methods=['POST'])
def upload():
    """Upload a video to YouTube"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        title = data.get('title', '')
        privacy = data.get('privacy_status', 'public')
        
        cmd = [
            'python', str(UPLOAD_SCRIPT),
            '--video', video_path,
            '--title', title,
            '--privacy', privacy
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        if result.returncode == 0:
            return jsonify({'success': True, 'output': result.stdout})
        else:
            return jsonify({'success': False, 'error': result.stderr})
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/history', methods=['GET'])
def history():
    """Get upload history"""
    history = []
    
    if UPLOADED_LOG.exists():
        with open(UPLOADED_LOG, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line:
                    parts = line.strip().split('|')
                    history.append({
                        'filename': parts[0],
                        'video_id': parts[1],
                        'upload_date': parts[2] if len(parts) > 2 else 'unknown',
                        'url': f"https://youtube.com/watch?v={parts[1]}"
                    })
    
    return jsonify({'success': True, 'history': history})

@app.route('/api/list-files', methods=['POST'])
def list_files():
    """List files in a directory"""
    try:
        data = request.get_json()
        folder = data.get('folder', '/tmp/downloads')
        
        path = Path(folder)
        files = []
        
        if path.exists():
            for f in path.glob('*.mp4'):
                files.append({
                    'name': f.name,
                    'size': f.stat().st_size,
                    'size_mb': round(f.stat().st_size / (1024 * 1024), 2),
                    'path': str(f)
                })
        
        return jsonify({'success': True, 'files': files})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/upload-folder', methods=['POST'])
def upload_folder():
    """Upload all videos from a folder"""
    try:
        data = request.get_json()
        folder = data.get('folder', '/tmp/downloads')
        privacy = data.get('privacy_status', 'public')
        
        path = Path(folder)
        videos = list(path.glob('*.mp4'))
        
        uploaded = 0
        for video in videos:
            cmd = [
                'python', str(UPLOAD_SCRIPT),
                '--video', str(video),
                '--privacy', privacy
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            if result.returncode == 0:
                uploaded += 1
        
        return jsonify({'success': True, 'uploaded': uploaded, 'total': len(videos)})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)