# web_app.py - Flask server to connect discovery, download, and frontend
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import subprocess
import os
import json
import re
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
CORS(app)

# Paths to your existing scripts
DISCOVERY_DIR = r'C:\Users\PC\Desktop\youtube_discovery'
DOWNLOAD_SCRIPT = r'C:\Users\PC\Desktop\ytdownload\working_downloader_fixed.py'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/discover', methods=['POST'])
def discover():
    """Run the discovery tool"""
    data = request.json
    search_terms = data.get('search_terms', [])
    max_results = data.get('max_results', 10)
    
    # Create a temporary config file
    config_content = f"""
YOUTUBE_API_KEY={os.getenv('YOUTUBE_API_KEY', '')}
SEARCH_TERMS={','.join(search_terms)}
MAX_RESULTS_PER_TERM={max_results}
OUTPUT_DIR=youtube_discovery_results
"""
    
    # Save temp config
    temp_config = Path(DISCOVERY_DIR) / 'temp_config.env'
    with open(temp_config, 'w') as f:
        f.write(config_content)
    
    try:
        # Run the discovery script
        result = subprocess.run(
            ['python', str(Path(DISCOVERY_DIR) / 'main.py')],
            cwd=DISCOVERY_DIR,
            capture_output=True,
            text=True,
            timeout=300
        )
        
        # Read the results
        results_file = Path(DISCOVERY_DIR) / 'youtube_discovery_results' / 'json' / 'analysis_report.json'
        
        if results_file.exists():
            with open(results_file, 'r', encoding='utf-8') as f:
                report = json.load(f)
            
            # Also read the URLs file
            urls_folder = Path(DISCOVERY_DIR) / 'youtube_discovery_results' / 'urls'
            url_files = list(urls_folder.glob('video_urls_*.txt'))
            results_file_name = str(url_files[-1]) if url_files else ''
            
            return jsonify({
                'success': True,
                'videos': report.get('top_videos', []),
                'stats': report.get('statistics', {}),
                'results_file': results_file_name
            })
        else:
            return jsonify({'success': False, 'error': 'No results file generated'})
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Discovery timed out after 5 minutes'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        # Clean up temp file
        if temp_config.exists():
            temp_config.unlink()

@app.route('/api/download', methods=['POST'])
def download_video():
    """Download a video using yt-dlp to Render's temp folder"""
    data = request.json
    video_url = data.get('url')
    video_title = data.get('title', 'video')
    
    # Use Render's temp folder or local temp
    output_folder = os.environ.get('RENDER_TMP_DIR', '/tmp/downloads')
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    try:
        # Use yt-dlp directly
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
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Download timed out'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/list-downloads', methods=['GET'])
def list_downloads():
    """List downloaded videos"""
    output_folder = os.environ.get('RENDER_TMP_DIR', '/tmp/downloads')
    folder = Path(output_folder)
    
    files = []
    if folder.exists():
        for f in folder.glob('*.mp4'):
            files.append({
                'name': f.name,
                'size_mb': round(f.stat().st_size / (1024 * 1024), 2),
                'path': str(f)
            })
    
    return jsonify({'success': True, 'files': files})

if __name__ == '__main__':
    # Create templates folder
    Path('templates').mkdir(exist_ok=True)
    app.run(debug=True, host='0.0.0.0', port=5000)