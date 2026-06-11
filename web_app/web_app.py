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

@app.route('/api/discover', methods=['POST'])
def discover():
    """Run YouTube discovery with given search terms"""
    try:
        data = request.get_json()
        search_terms = data.get('search_terms', ['python programming'])
        max_results = data.get('max_results', 10)
        
        # Create a temporary config file with the search terms
        temp_config = DISCOVERY_DIR / 'temp_config.env'
        config_content = f"""
YOUTUBE_API_KEY={os.environ.get('YOUTUBE_API_KEY', '')}
SEARCH_TERMS={','.join(search_terms)}
MAX_RESULTS_PER_TERM={max_results}
OUTPUT_DIR=youtube_discovery_results
"""
        with open(temp_config, 'w') as f:
            f.write(config_content)
        
        # Run the discovery script
        print(f"Running discovery with terms: {search_terms}")
        result = subprocess.run(
            ['python', str(DISCOVERY_DIR / 'main.py')],
            cwd=str(DISCOVERY_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        print(f"Discovery stdout: {result.stdout}")
        print(f"Discovery stderr: {result.stderr}")
        
        # Look for the results file
        results_dir = DISCOVERY_DIR / 'youtube_discovery_results' / 'json'
        results_file = results_dir / 'analysis_report.json'
        
        # Also try to find any JSON file
        if not results_file.exists():
            json_files = list(results_dir.glob('*.json'))
            if json_files:
                results_file = json_files[0]
        
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            # Also get the URLs file
            urls_dir = DISCOVERY_DIR / 'youtube_discovery_results' / 'urls'
            url_files = list(urls_dir.glob('video_urls_*.txt'))
            urls_file = str(url_files[-1]) if url_files else ''
            
            return jsonify({
                'success': True,
                'videos': report.get('top_videos', []),
                'stats': report.get('statistics', {}),
                'results_file': urls_file,
                'message': f"Found {len(report.get('top_videos', []))} videos"
            })
        else:
            # Check if there's any output at all
            output_dir = DISCOVERY_DIR / 'youtube_discovery_results'
            if output_dir.exists():
                all_files = list(output_dir.rglob('*'))
                return jsonify({
                    'success': False, 
                    'error': 'No analysis_report.json found',
                    'debug': {
                        'output_dir_exists': True,
                        'files_found': [str(f.relative_to(output_dir)) for f in all_files[:10]],
                        'stdout': result.stdout[:500],
                        'stderr': result.stderr[:500]
                    }
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': 'Discovery ran but no output folder was created',
                    'debug': {
                        'stdout': result.stdout[:500],
                        'stderr': result.stderr[:500]
                    }
                })
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Discovery timed out after 5 minutes'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download', methods=['POST'])
def download():
    """Download a video"""
    try:
        data = request.get_json()
        video_url = data.get('url')
        output_folder = data.get('output_folder', '/tmp/downloads')
        
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
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