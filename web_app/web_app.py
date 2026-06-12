# web_app/web_app.py
import os
import json
import subprocess
import sys
import shutil
import pickle
import re
from pathlib import Path
from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = Path(__file__).parent.parent
DISCOVERY_DIR = BASE_DIR / 'youtube_discovery'
UPLOAD_SCRIPT = BASE_DIR / 'ytupload' / 'yt_uploader_auto.py'
UPLOADED_LOG = BASE_DIR / 'ytupload' / 'uploaded_videos.log'

# Google Drive API scope
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive.file']

# Download directory - temporary local storage
TEMP_DIR = Path('/tmp/downloads')
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Persistent Drive folder ID (optional, set in environment)
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', None)



def get_drive_service():
    """Authenticate and return Google Drive service"""
    creds = None
    token_file = Path('/tmp/drive_token.pickle')
    
    # Check for existing token
    if token_file.exists():
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
        except:
            pass
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except:
                creds = None
        
        if not creds:
            # Look for client_secrets file
            secrets_file = Path('/app/ytupload/client_secrets.json')
            if not secrets_file.exists():
                secrets_file = BASE_DIR / 'ytupload' / 'client_secrets.json'
            
            if secrets_file.exists():
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        str(secrets_file), DRIVE_SCOPES)
                    creds = flow.run_local_server(port=8080)
                    
                    # Save credentials
                    with open(token_file, 'wb') as token:
                        pickle.dump(creds, token)
                except Exception as e:
                    print(f"❌ Drive auth error: {e}")
                    return None
            else:
                print("❌ client_secrets.json not found for Drive API")
                return None
    
    return build('drive', 'v3', credentials=creds)


def upload_to_drive(file_path, folder_id=None):
    """Upload a file to Google Drive"""
    try:
        drive_service = get_drive_service()
        
        if not drive_service:
            return None
        
        file_metadata = {
            'name': Path(file_path).name,
        }
        
        if folder_id or DRIVE_FOLDER_ID:
            file_metadata['parents'] = [folder_id or DRIVE_FOLDER_ID]
        
        media = MediaFileUpload(file_path, resumable=True)
        
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, name'
        ).execute()
        
        print(f"✅ Uploaded to Drive: {file.get('webViewLink')}")
        return file
        
    except Exception as e:
        print(f"❌ Drive upload error: {e}")
        return None


def create_drive_folder(folder_name):
    """Create a folder in Google Drive"""
    try:
        drive_service = get_drive_service()
        
        if not drive_service:
            return None
        
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        
        folder = drive_service.files().create(body=file_metadata, fields='id, webViewLink').execute()
        print(f"✅ Created Drive folder: {folder_name} (ID: {folder.get('id')})")
        return folder.get('id')
        
    except Exception as e:
        print(f"❌ Failed to create folder: {e}")
        return None


def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ yt-dlp is installed")
            return True
    except:
        pass
    
    print("📦 Installing yt-dlp...")
    subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'], capture_output=True)
    return True


def check_disk_space(folder):
    """Check available disk space in folder"""
    try:
        stat = shutil.disk_usage(folder)
        free_gb = stat.free / (1024**3)
        return f"{free_gb:.2f} GB free"
    except:
        return "Unknown"


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
        
        # Run discovery script
        result = subprocess.run(
            [sys.executable, str(DISCOVERY_DIR / 'main.py')],
            cwd=str(DISCOVERY_DIR),
            capture_output=True,
            text=True,
            timeout=300,
            env={**os.environ, 'YOUTUBE_API_KEY': api_key}
        )
        
        print(f"Discovery return code: {result.returncode}")
        
        # Look for results file
        results_file = DISCOVERY_DIR / 'youtube_discovery_results' / 'json' / 'analysis_report.json'
        
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
                'error': 'No results found. Please check your API key and try again.'
            })
            
    except subprocess.TimeoutExpired:
        return jsonify({'success': False, 'error': 'Discovery timed out after 5 minutes'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})







@app.route('/api/download', methods=['POST'])
def download():
    """Download video using yt-dlp with cookies from secrets"""
    try:
        data = request.get_json()
        video_url = data.get('url')
        
        if not video_url:
            return jsonify({'success': False, 'error': 'No URL provided'})
        
        output_folder = '/opt/render/project/src/downloads'
        Path(output_folder).mkdir(parents=True, exist_ok=True)
        
        # Secret file location on Render
        cookies_path = '/etc/secrets/cookies.txt'
        
        # Check if cookies exist
        if os.path.exists(cookies_path):
            print(f"✅ Using cookies from {cookies_path}")
            cookies_arg = ['--cookies', cookies_path]
        else:
            print("⚠️ No cookies file found")
            cookies_arg = []
        
        # Update yt-dlp
        subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'], 
                      capture_output=True)
        
        # Download command with cookies
        cmd = [
            'yt-dlp',
            '-f', 'best[ext=mp4]/best',
            '-o', f'{output_folder}/%(title)s.%(ext)s',
            '--no-playlist',
            '--restrict-filenames',
            '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            '--extractor-args', 'youtube:player_client=android',
            '--sleep-requests', '5',
            '--retries', '10',
        ] + cookies_arg + [video_url]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        # Check for downloaded files
        downloaded_files = list(Path(output_folder).glob('*.mp4'))
        
        if result.returncode == 0 and downloaded_files:
            latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
            file_size = round(latest_file.stat().st_size / (1024 * 1024), 2)
            
            # Upload to Google Drive
            drive_file = upload_to_drive(str(latest_file))
            latest_file.unlink()
            
            if drive_file:
                return jsonify({
                    'success': True,
                    'message': '✅ Downloaded and uploaded to Drive',
                    'drive_link': drive_file.get('webViewLink'),
                    'filename': drive_file.get('name'),
                    'size_mb': file_size
                })
        
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
                '-f', 'best[ext=mp4]/best',
                '-o', f'{TEMP_DIR}/%(title)s.%(ext)s',
                '--no-playlist',
                '--restrict-filenames',
                video['url']
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                downloaded_files = list(TEMP_DIR.glob('*.mp4'))
                if downloaded_files:
                    latest_file = max(downloaded_files, key=lambda f: f.stat().st_mtime)
                    drive_file = upload_to_drive(str(latest_file))
                    latest_file.unlink()
                    
                    if drive_file:
                        downloaded.append({
                            'title': video['title'],
                            'drive_link': drive_file.get('webViewLink')
                        })
                        print(f"   ✅ Downloaded and uploaded to Drive")
                    else:
                        failed.append(video['title'])
                        print(f"   ❌ Upload to Drive failed")
                else:
                    failed.append(video['title'])
                    print(f"   ❌ Download failed")
            else:
                failed.append(video['title'])
                print(f"   ❌ Download failed")
        
        return jsonify({
            'success': True,
            'downloaded_count': len(downloaded),
            'failed_count': len(failed),
            'downloaded': downloaded,
            'failed': failed
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/create-drive-folder', methods=['POST'])
def create_drive_folder_endpoint():
    """Create a folder in Google Drive"""
    try:
        data = request.get_json()
        folder_name = data.get('folder_name', 'YouTube Downloads')
        
        folder_id = create_drive_folder(folder_name)
        
        if folder_id:
            return jsonify({
                'success': True,
                'folder_id': folder_id,
                'folder_name': folder_name,
                'message': f'Folder "{folder_name}" created in Google Drive'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to create Drive folder. Check authentication.'
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/list-drive-files', methods=['GET'])
def list_drive_files():
    """List files in Google Drive"""
    try:
        drive_service = get_drive_service()
        
        if not drive_service:
            return jsonify({'success': False, 'error': 'Drive service not available'})
        
        # List video files from Drive
        results = drive_service.files().list(
            q="mimeType contains 'video/' or name contains '.mp4'",
            fields="files(id, name, size, webViewLink, createdTime, mimeType)",
            orderBy="createdTime desc",
            pageSize=50
        ).execute()
        
        files = results.get('files', [])
        
        # Format file sizes
        for file in files:
            if 'size' in file:
                size_bytes = int(file['size'])
                size_mb = round(size_bytes / (1024 * 1024), 2)
                file['size_mb'] = size_mb
        
        return jsonify({
            'success': True,
            'files': files,
            'count': len(files),
            'message': f'Found {len(files)} videos in Drive'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@app.route('/api/list-downloads', methods=['GET'])
def list_downloads():
    """Alias for list-drive-files"""
    return list_drive_files()


@app.route('/api/upload', methods=['POST'])
def upload():
    """Upload a video to YouTube from Drive or local path"""
    try:
        data = request.get_json()
        video_path = data.get('video_path')
        title = data.get('title', '')
        privacy = data.get('privacy_status', 'public')
        
        if not video_path:
            return jsonify({'success': False, 'error': 'No video path provided'})
        
        temp_file = None
        
        # If it's a Drive file ID
        if video_path.startswith('drive://'):
            file_id = video_path.replace('drive://', '')
            drive_service = get_drive_service()
            
            if drive_service:
                # Download from Drive to temp
                request_file = drive_service.files().get_media(fileId=file_id)
                temp_file = TEMP_DIR / f'temp_{file_id}.mp4'
                
                with open(temp_file, 'wb') as f:
                    f.write(request_file.execute())
                
                video_path = str(temp_file)
            else:
                return jsonify({'success': False, 'error': 'Drive service not available'})
        
        if not os.path.exists(video_path):
            return jsonify({'success': False, 'error': f'Video file not found: {video_path}'})
        
        cmd = [
            sys.executable, str(UPLOAD_SCRIPT),
            '--video', video_path,
            '--title', title,
            '--privacy', privacy
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        
        # Clean up temp file if created
        if temp_file and temp_file.exists():
            temp_file.unlink()
        
        if result.returncode == 0:
            # Try to extract video ID from output
            video_id = None
            for line in result.stdout.split('\n'):
                if 'Video ID:' in line:
                    video_id = line.split('Video ID:')[-1].strip()
                    break
            
            return jsonify({
                'success': True,
                'output': result.stdout,
                'video_id': video_id,
                'watch_url': f'https://youtube.com/watch?v={video_id}' if video_id else None
            })
        else:
            return jsonify({
                'success': False,
                'error': result.stderr
            })
            
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


@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'drive_available': get_drive_service() is not None
    })


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 60)
    print("🚀 YouTube Automation Server Starting...")
    print("=" * 60)
    print(f"📡 Port: {port}")
    print(f"📁 Temp folder: {TEMP_DIR}")
    print(f"💾 Disk space: {check_disk_space(TEMP_DIR)}")
    print(f"☁️ Google Drive: {'Enabled' if get_drive_service() else 'Disabled'}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)