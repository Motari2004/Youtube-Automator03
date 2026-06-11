# web_app/web_app.py
import os
import json
import subprocess
import sys
import re
import time
import shutil
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DISCOVERY_DIR = BASE_DIR / 'youtube_discovery'
UPLOAD_SCRIPT = BASE_DIR / 'ytupload' / 'yt_uploader_auto.py'
UPLOADED_LOG = BASE_DIR / 'ytupload' / 'uploaded_videos.log'

# For local development vs Render
if os.environ.get('RENDER'):
    DOWNLOAD_DIR = Path('/opt/render/project/src/downloads')
else:
    DOWNLOAD_DIR = BASE_DIR / 'downloads'

DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        print("✅ yt-dlp is installed")
        return True
    except:
        print("📦 Installing yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'])
        return True

def get_download_folder():
    """Get the download folder path"""
    return DOWNLOAD_DIR

def check_disk_space(folder):
    """Check available disk space in folder"""
    try:
        stat = shutil.disk_usage(folder)
        free_gb = stat.free / (1024**3)
        return f"{free_gb:.2f} GB free"
    except:
        return "Unknown"

def list_downloaded_files():
    """List all downloaded video files"""
    files = []
    for f in DOWNLOAD_DIR.glob('*.mp4'):
        files.append({
            'name': f.name,
            'size_mb': round(f.stat().st_size / (1024 * 1024), 2),
            'path': str(f),
            'modified': datetime.fromtimestamp(f.stat().st_mtime).isoformat()
        })
    return files

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
        
        api_key = os.environ.get('YOUTUBE_API_KEY', '')
        
        if not api_key:
            return jsonify({'success': False, 'error': 'YOUTUBE_API_KEY environment variable not set'})
        
        # Create .env file in discovery directory
        env_file = DISCOVERY_DIR / '.env'
        with open(env_file, 'w') as f:
            f.write(f"YOUTUBE_API_KEY={api_key}\n")
            f.write(f"SEARCH_TERMS={','.join(search_terms)}\n")
            f.write(f"MAX_RESULTS_PER_TERM={max_results}\n")
            f.write(f"OUTPUT_DIR=youtube_discovery_results\n")
        
        print(f"Running discovery with terms: {search_terms}")
        
        result = subprocess.run(
            ['python', str(DISCOVERY_DIR / 'main.py')],
            cwd=str(DISCOVERY_DIR),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, 'YOUTUBE_API_KEY': api_key}
        )
        
        print(f"Discovery return code: {result.returncode}")
        
        results_file = DISCOVERY_DIR / 'youtube_discovery_results' / 'json' / 'analysis_report.json'
        
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            # Also get the URLs file
            urls_dir = DISCOVERY_DIR / 'youtube_discovery_results' / 'urls'
            url_files = list(urls_dir.glob('top_*_urls_*.txt'))
            urls_file = str(url_files[-1]) if url_files else ''
            
            return jsonify({
                'success': True,
                'videos': report.get('top_videos', []),
                'stats': report.get('statistics', {}),
                'urls_file': urls_file,
                'message': f"Found {len(report.get('top_videos', []))} videos"
            })
        else:
            return jsonify({
                'success': False, 
                'error': f'No results found. Script output: {result.stdout[:300]}'
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
        
        if not video_url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        print(f"📥 Downloading: {video_url}")
        print(f"📁 Output folder: {DOWNLOAD_DIR}")
        print(f"💾 Available space: {check_disk_space(DOWNLOAD_DIR)}")
        
        # Ensure yt-dlp is installed
        check_ytdlp()
        
        # Try format 22 (mp4) first
        cmd = [
            'yt-dlp',
            '-f', '22',
            '-o', f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
            '--no-playlist',
            video_url
        ]
        
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        # If format 22 fails, try best format
        if result.returncode != 0:
            print("Format 22 failed, trying best format...")
            cmd = [
                'yt-dlp',
                '-f', 'best',
                '-o', f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
                '--no-playlist',
                video_url
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
        
        # Check for downloaded files
        downloaded_files = list(DOWNLOAD_DIR.glob('*.mp4'))
        
        if result.returncode == 0 and downloaded_files:
            # Find the most recently downloaded file
            latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
            file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
            
            print(f"✅ Download complete: {latest_file.name} ({file_size} MB)")
            
            return jsonify({
                'success': True,
                'message': f'✅ Downloaded: {latest_file.name} ({file_size} MB)',
                'file': str(latest_file),
                'filename': latest_file.name,
                'size_mb': file_size
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr[:500] if result.stderr else 'Download failed'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/download-all', methods=['POST'])
def download_all():
    """Download all videos from discovery results"""
    try:
        data = request.get_json()
        discovery_file = data.get('discovery_file')
        max_downloads = data.get('max_downloads')
        
        if not discovery_file:
            # Try to find the latest discovery file
            urls_dir = DISCOVERY_DIR / 'youtube_discovery_results' / 'urls'
            url_files = list(urls_dir.glob('top_*_urls_*.txt'))
            if url_files:
                discovery_file = str(max(url_files))
            else:
                return jsonify({'success': False, 'error': 'No discovery file found'})
        
        print(f"📖 Reading discovery file: {discovery_file}")
        
        # Extract URLs from file
        urls = []
        with open(discovery_file, 'r', encoding='utf-8') as f:
            for line in f:
                if '|' in line and 'youtube.com' in line:
                    parts = line.strip().split('|')
                    if len(parts) >= 2:
                        urls.append({
                            'title': parts[0],
                            'url': parts[1]
                        })
        
        if not urls:
            return jsonify({'success': False, 'error': 'No URLs found in discovery file'})
        
        # Limit downloads if specified
        if max_downloads and max_downloads < len(urls):
            urls = urls[:max_downloads]
        
        print(f"🚀 Starting download of {len(urls)} videos")
        
        # Ensure yt-dlp is installed
        check_ytdlp()
        
        downloaded = []
        failed = []
        
        for i, video in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] {video['title'][:60]}...")
            
            cmd = [
                'yt-dlp',
                '-f', 'best',
                '-o', f'{DOWNLOAD_DIR}/%(title)s.%(ext)s',
                '--no-playlist',
                video['url']
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                downloaded.append(video['title'])
                print(f"   ✅ Downloaded")
            else:
                failed.append(video['title'])
                print(f"   ❌ Failed: {result.stderr[:100]}")
        
        return jsonify({
            'success': True,
            'downloaded_count': len(downloaded),
            'failed_count': len(failed),
            'downloaded': downloaded,
            'failed': failed,
            'download_folder': str(DOWNLOAD_DIR)
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/list-downloads', methods=['GET'])
def list_downloads():
    """List all downloaded videos"""
    try:
        files = list_downloaded_files()
        return jsonify({
            'success': True,
            'files': files,
            'download_folder': str(DOWNLOAD_DIR),
            'disk_space': check_disk_space(DOWNLOAD_DIR)
        })
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
        
        if not video_path or not Path(video_path).exists():
            return jsonify({'success': False, 'error': 'Video file not found'})
        
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"🚀 Starting server on port {port}")
    print(f"📁 Download directory: {DOWNLOAD_DIR}")
    print(f"💾 Disk space: {check_disk_space(DOWNLOAD_DIR)}")
    app.run(host='0.0.0.0', port=port, debug=False)