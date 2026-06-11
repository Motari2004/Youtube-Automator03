# web_app/web_app.py
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Configuration
DISCOVERY_DIR = Path(__file__).parent.parent / 'youtube_discovery'
DOWNLOAD_SCRIPT = Path(__file__).parent.parent / 'ytdownload' / 'working_downloader_fixed.py'
UPLOAD_SCRIPT = Path(__file__).parent.parent / 'ytupload' / 'yt_uploader_auto.py'
UPLOADED_LOG = Path(__file__).parent.parent / 'ytupload' / 'uploaded_videos.log'

@app.route('/')
def index():
    """Serve the main page"""
    return render_template('index.html')

@app.route('/api/discover', methods=['POST'])
def discover():
    """Run YouTube discovery with given search terms"""
    try:
        data = request.get_json()
        search_terms = data.get('search_terms', ['python programming'])
        max_results = data.get('max_results', 10)
        
        # Run the discovery script
        result = subprocess.run(
            ['python', str(DISCOVERY_DIR / 'main.py')],
            cwd=str(DISCOVERY_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Read the results
        results_file = DISCOVERY_DIR / 'youtube_discovery_results' / 'json' / 'analysis_report.json'
        
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            return jsonify({
                'success': True,
                'videos': report.get('top_videos', []),
                'stats': report.get('statistics', {})
            })
        else:
            return jsonify({'success': False, 'error': 'No results found'})
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Discovery timed out'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download', methods=['POST'])
def download():
    """Download a video"""
    try:
        data = request.get_json()
        video_url = data.get('url')
        output_folder = data.get('output_folder', '/tmp/downloads')
        
        # Create output folder
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # Run yt-dlp directly
        cmd = [
            'yt-dlp',
            '-f', 'best',
            '-o', f'{output_folder}/%(title)s.%(ext)s',
            '--no-playlist',
            video_url
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0:
            return jsonify({'success': True, 'output': result.stdout})
        else:
            return jsonify({'success': False, 'error': result.stderr})
            
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
        
        # Run upload script
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