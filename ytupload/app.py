# yt_uploader_auto.py
import os
import pickle
import time
import json
import re
from pathlib import Path
from datetime import datetime
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

class YouTubeUploader:
    def __init__(self, credentials_file='client_secrets.json'):
        self.credentials_file = credentials_file
        self.youtube = None
        self.uploaded_log = 'uploaded_videos.log'
        self.uploaded_files = set()  # Track uploaded filenames
        self.discovery_descriptions = []
        self.load_uploaded_history()  # Load existing uploaded videos
        self.load_discovery_descriptions()
        self.authenticate()
    
    def load_uploaded_history(self):
        """Load previously uploaded videos from log file"""
        self.uploaded_files = set()
        
        if os.path.exists(self.uploaded_log):
            try:
                # Try UTF-8 first
                with open(self.uploaded_log, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if '|' in line:
                            filename = line.split('|')[0]
                            self.uploaded_files.add(filename)
            except UnicodeDecodeError:
                # Fall back to latin-1 if UTF-8 fails
                with open(self.uploaded_log, 'r', encoding='latin-1') as f:
                    for line in f:
                        line = line.strip()
                        if '|' in line:
                            filename = line.split('|')[0]
                            self.uploaded_files.add(filename)
            except Exception as e:
                print(f"⚠️ Could not read log file: {e}")
                # Create a new log file if corrupted
                self.uploaded_files = set()
            
            print(f"📋 Loaded {len(self.uploaded_files)} previously uploaded video(s)")
        else:
            print("📋 No previous upload history found. Will track new uploads.")
    
    def show_pending_videos(self, folder_path):
        """Display which videos are pending upload"""
        folder = Path(folder_path)
        if not folder.exists():
            return
        
        videos = list(folder.glob('*.mp4')) + list(folder.glob('*.MP4')) + list(folder.glob('*.mov'))
        
        pending = [v for v in videos if v.name not in self.uploaded_files]
        uploaded = [v for v in videos if v.name in self.uploaded_files]
        
        print("\n" + "=" * 60)
        print("📊 UPLOAD STATUS")
        print("=" * 60)
        print(f"✅ Already uploaded: {len(uploaded)}")
        for v in uploaded:
            print(f"   - {v.name}")
        
        print(f"\n⏳ Pending upload: {len(pending)}")
        for v in pending:
            print(f"   - {v.name}")
        print("=" * 60)
        
        return pending
    
    def load_discovery_descriptions(self):
        """Load real descriptions from discovery tool results and match by filename"""
        
        # Path to your discovery descriptions file
        discovery_file = Path(r'C:\Users\PC\Desktop\youtube_discovery\youtube_discovery_results\descriptions\full_descriptions_20260611_195018.txt')
        
        if not discovery_file.exists():
            print(f"⚠️ Discovery descriptions not found at: {discovery_file}")
            return
        
        print(f"📖 Loading discovery descriptions from: {discovery_file}")
        
        try:
            with open(discovery_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            with open(discovery_file, 'r', encoding='latin-1') as f:
                content = f.read()
        
        # Parse the text file to extract video descriptions
        blocks = re.split(r'={80,}', content)
        
        for block in blocks:
            if 'TITLE:' in block and 'DESCRIPTION:' in block:
                video_data = {}
                
                # Extract TITLE
                title_match = re.search(r'TITLE:\s*(.+?)(?=\n)', block)
                if title_match:
                    video_data['title'] = title_match.group(1).strip()
                
                # Extract CHANNEL
                channel_match = re.search(r'CHANNEL:\s*(.+?)(?=\n)', block)
                if channel_match:
                    video_data['channel'] = channel_match.group(1).strip()
                
                # Extract URL
                url_match = re.search(r'URL:\s*(.+?)(?=\n)', block)
                if url_match:
                    video_data['url'] = url_match.group(1).strip()
                
                # Extract VIEWS
                views_match = re.search(r'VIEWS:\s*([\d,]+)', block)
                if views_match:
                    video_data['views'] = int(views_match.group(1).replace(',', ''))
                
                # Extract TAGS
                tags_match = re.search(r'TAGS:\s*(.+?)(?=\n-{80,}|\nDESCRIPTION:)', block, re.DOTALL)
                if tags_match:
                    tags_text = tags_match.group(1).strip()
                    video_data['tags'] = [t.strip() for t in tags_text.split(',') if t.strip()]
                
                # Extract DESCRIPTION
                desc_match = re.search(r'DESCRIPTION:\s*\n(.*?)(?=\n={80,}|\Z)', block, re.DOTALL)
                if desc_match:
                    video_data['description'] = desc_match.group(1).strip()
                    video_data['description'] = video_data['description'].replace('DESCRIPTION:', '').strip()
                
                if video_data.get('description'):
                    video_data['filename_match'] = self.create_filename_match(video_data['title'])
                    self.discovery_descriptions.append(video_data)
        
        print(f"✅ Loaded {len(self.discovery_descriptions)} real descriptions from discovery")
    
    def create_filename_match(self, title):
        """Create a normalized version of title for filename matching"""
        normalized = title.lower()
        normalized = re.sub(r'[^\w\s]', '', normalized)
        return normalized[:50]
    
    def find_matching_description(self, video_filename):
        """Find the description that matches the video filename"""
        
        video_filename_lower = video_filename.lower().replace('.mp4', '').replace('.mov', '')
        
        print(f"\n🔍 Looking for description matching: {video_filename_lower[:60]}...")
        
        for desc in self.discovery_descriptions:
            title_keywords = desc.get('title', '').lower()[:60]
            
            if title_keywords in video_filename_lower or video_filename_lower in title_keywords:
                print(f"   ✅ Found match: {desc.get('channel', 'Unknown')}")
                return desc
        
        print(f"   ⚠️ No matching description found")
        return None
    
    def get_description_for_video(self, video_path):
        """Get the matching description for a video file"""
        filename = Path(video_path).stem
        matching_desc = self.find_matching_description(filename)
        
        if matching_desc:
            return matching_desc.get('description', '')
        return None
    
    def authenticate(self):
        """Authenticate with YouTube API for upload permissions"""
        SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
        credentials = None
        
        if os.path.exists('token_upload.pickle'):
            try:
                with open('token_upload.pickle', 'rb') as token:
                    credentials = pickle.load(token)
                    print("✅ Loaded saved credentials")
            except:
                pass
        
        if not credentials or not credentials.valid:
            if credentials and credentials.expired and credentials.refresh_token:
                print("🔄 Refreshing expired credentials...")
                credentials.refresh(Request())
            else:
                print("🔐 Starting OAuth authentication...")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, SCOPES)
                credentials = flow.run_local_server(port=8080)
            
            with open('token_upload.pickle', 'wb') as token:
                pickle.dump(credentials, token)
            print("💾 Credentials saved")
        
        self.youtube = build('youtube', 'v3', credentials=credentials)
        print("✅ YouTube authentication successful!")
    
    def is_already_uploaded(self, filename):
        """Check if video was already uploaded (persists across script restarts)"""
        return filename in self.uploaded_files
    
    def mark_as_uploaded(self, filename, video_id):
        """Mark video as uploaded and save to log file"""
        # Add to memory
        self.uploaded_files.add(filename)
        
        # Append to log file with proper encoding
        with open(self.uploaded_log, 'a', encoding='utf-8') as f:
            f.write(f"{filename}|{video_id}|{datetime.now().isoformat()}\n")
        
        print(f"   📝 Added to upload history: {filename}")
    
    def upload_video(self, video_path, title=None, description=None, 
                     tags=None, privacy_status='public'):
        """Upload video to YouTube with its matching description"""
        
        if not os.path.exists(video_path):
            print(f"❌ File not found: {video_path}")
            return False
        
        filename = os.path.basename(video_path)
        
        # Check if already uploaded (from log file)
        if self.is_already_uploaded(filename):
            print(f"⏭️ SKIPPED: {filename} (already uploaded)")
            return True
        
        # Auto-generate title from filename if not provided
        if not title:
            title = Path(filename).stem.replace('_', ' ').replace('-', ' ')
        
        # Get matching description from discovery
        if not description:
            description = self.get_description_for_video(video_path)
            if not description:
                print(f"\n   ⚠️ No matching description found. Using fallback.")
                description = f"Check out this tutorial: {title}\n\nSubscribe for more content!"
        
        # Extract tags from title
        if not tags:
            tags = self.extract_hashtags(title)
        
        file_size = os.path.getsize(video_path) / (1024 * 1024)
        print(f"\n📹 UPLOADING: {filename}")
        print(f"📊 Size: {file_size:.2f} MB")
        print(f"📝 Title: {title}")
        print(f"📄 Description length: {len(description)} characters")
        print(f"🏷️ Tags: {', '.join(tags)}")
        
        body = {
            'snippet': {
                'title': title[:100],
                'description': description[:5000],
                'tags': tags[:15],
                'categoryId': '22'
            },
            'status': {
                'privacyStatus': privacy_status,
                'selfDeclaredMadeForKids': False
            }
        }
        
        media = MediaFileUpload(video_path, chunksize=10*1024*1024, resumable=True)
        
        try:
            upload_request = self.youtube.videos().insert(
                part='snippet,status',
                body=body,
                media_body=media
            )
            
            response = None
            while response is None:
                status, response = upload_request.next_chunk()
                if status:
                    progress = int(status.progress() * 100)
                    print(f"\r   Upload Progress: {progress}%", end='', flush=True)
            
            print(f"\n\n✅ Uploaded successfully!")
            print(f"   Video ID: {response['id']}")
            print(f"   Watch: https://youtube.com/watch?v={response['id']}")
            
            self.mark_as_uploaded(filename, response['id'])
            return response['id']
            
        except Exception as e:
            print(f"\n❌ Upload Error: {e}")
            return False
    
    def extract_hashtags(self, title):
        """Extract relevant hashtags from video title"""
        hashtags = []
        keywords = {
            'python': 'Python',
            'javascript': 'JavaScript',
            'web development': 'WebDev',
            'data science': 'DataScience',
            'machine learning': 'MachineLearning',
            'ai': 'AI',
            'tutorial': 'Tutorial',
            'beginner': 'Beginner'
        }
        
        title_lower = title.lower()
        for keyword, tag in keywords.items():
            if keyword in title_lower:
                hashtags.append(tag)
        
        if not hashtags:
            hashtags = ['Tutorial', 'Coding', 'LearnToCode']
        
        return hashtags[:5]
    
    def upload_folder(self, folder_path, privacy_status='public'):
        """Upload ONLY NEW videos in folder (skip already uploaded)"""
        folder = Path(folder_path)
        
        if not folder.exists():
            print(f"❌ Folder not found: {folder_path}")
            return
        
        # Find video files
        videos = list(folder.glob('*.mp4')) + list(folder.glob('*.MP4')) + list(folder.glob('*.mov'))
        
        if not videos:
            print(f"❌ No video files found in {folder_path}")
            return
        
        # Show status before uploading
        pending = [v for v in videos if v.name not in self.uploaded_files]
        
        print(f"\n📹 Found {len(videos)} video(s) in {folder_path}")
        print(f"   ✅ Already uploaded: {len(videos) - len(pending)}")
        print(f"   ⏳ New videos to upload: {len(pending)}")
        
        if not pending:
            print("\n✨ All videos have been uploaded already!")
            return
        
        print("-" * 50)
        
        for i, video in enumerate(pending, 1):
            print(f"\n[{i}/{len(pending)}] Processing: {video.name}")
            self.upload_video(str(video), privacy_status=privacy_status)
        
        print(f"\n✅ Upload complete! {len(pending)} new video(s) uploaded")

def main():
    print("🎬 YouTube Uploader - Auto-Skip Already Uploaded Videos")
    print("=" * 60)
    
    # Set your videos folder path
    videos_folder = r"C:\Users\PC\Desktop\ytupload\videos"
    
    # Create folder if it doesn't exist
    Path(videos_folder).mkdir(parents=True, exist_ok=True)
    print(f"📁 Videos folder: {videos_folder}")
    
    # Check credentials
    if not os.path.exists('client_secrets.json'):
        print("\n❌ client_secrets.json not found!")
        print("   Place your Google OAuth credentials file in this folder")
        return
    
    # Initialize uploader
    uploader = YouTubeUploader()
    
    while True:
        print("\n" + "=" * 60)
        print("📋 Options:")
        print("1. Upload NEW videos from folder (auto-skip uploaded)")
        print("2. Upload a single video file")
        print("3. Show upload history")
        print("4. Exit")
        
        choice = input("\nSelect option (1-4): ").strip()
        
        if choice == '1':
            privacy = input("Privacy (public/private/unlisted) [public]: ").strip().lower()
            if privacy not in ['public', 'private', 'unlisted']:
                privacy = 'public'
            uploader.upload_folder(videos_folder, privacy)
        
        elif choice == '2':
            video_path = input("📹 Enter video file path: ").strip().strip('"')
            if os.path.exists(video_path):
                privacy = input("Privacy (public/private/unlisted) [public]: ").strip().lower()
                if privacy not in ['public', 'private', 'unlisted']:
                    privacy = 'public'
                title = input("📝 Video title (Enter for auto from filename): ").strip()
                uploader.upload_video(
                    video_path=video_path,
                    title=title if title else None,
                    privacy_status=privacy
                )
            else:
                print("❌ File not found!")
        
        elif choice == '3':
            print("\n📋 UPLOAD HISTORY")
            print("=" * 60)
            if uploader.uploaded_files:
                for i, filename in enumerate(sorted(uploader.uploaded_files), 1):
                    print(f"   {i}. {filename}")
            else:
                print("   No videos uploaded yet")
            print("=" * 60)
        
        elif choice == '4':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()