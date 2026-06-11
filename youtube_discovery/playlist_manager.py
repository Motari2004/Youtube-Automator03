# playlist_manager.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os
import json
import pandas as pd
from pathlib import Path

class PlaylistManager:
    def __init__(self, api_key, output_folder='youtube_discovery_results'):
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.output_folder = output_folder
        
        # Create subfolders
        self.playlists_folder = Path(output_folder) / 'playlists'
        self.html_folder = Path(output_folder) / 'html'
        self.playlists_folder.mkdir(parents=True, exist_ok=True)
        self.html_folder.mkdir(parents=True, exist_ok=True)
    
    def create_playlist_file(self, videos, playlist_name):
        """Create a file with video URLs for manual playlist creation"""
        playlist_data = {
            'name': playlist_name,
            'created_at': str(pd.Timestamp.now()),
            'videos': videos
        }
        
        # Sanitize filename
        safe_name = "".join(c for c in playlist_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = self.playlists_folder / f"{safe_name.replace(' ', '_')}_playlist.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(playlist_data, f, indent=2, ensure_ascii=False)
        
        # Also create a simple text file with URLs
        url_file = self.playlists_folder / f"{safe_name.replace(' ', '_')}_urls.txt"
        with open(url_file, 'w', encoding='utf-8') as f:
            for video in videos:
                f.write(f"{video.get('title', 'Unknown')}: {video.get('url', 'No URL')}\n")
        
        print(f"✅ Playlist files created: {filename} and {url_file}")
        return filename
    
    def generate_html_embed(self, videos, title="My Curated Playlist"):
        """Generate HTML page with embedded YouTube videos"""
        
        # Ensure videos have all required fields
        processed_videos = []
        for video in videos:
            # Handle missing fields with defaults
            processed_video = {
                'title': video.get('title', 'Untitled'),
                'channel_title': video.get('channel_title', 'Unknown Channel'),
                'url': video.get('url', '#'),
                'thumbnail': video.get('thumbnail', 'https://via.placeholder.com/480x360?text=No+Thumbnail'),
                'view_count': video.get('view_count', 0),
                'like_count': video.get('like_count', 0),
                'duration_seconds': video.get('duration_seconds', 600)  # Default 10 minutes
            }
            processed_videos.append(processed_video)
        
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <title>{title}</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        h1 {{ color: white; text-align: center; margin-bottom: 30px; }}
        .stats {{ text-align: center; color: white; margin-bottom: 30px; font-size: 18px; }}
        .video-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(350px, 1fr)); gap: 25px; }}
        .video-card {{ background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.2); transition: transform 0.3s ease; }}
        .video-card:hover {{ transform: translateY(-5px); }}
        .video-card img {{ width: 100%; height: 200px; object-fit: cover; }}
        .video-info {{ padding: 20px; }}
        .video-title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; color: #333; }}
        .video-channel {{ color: #666; font-size: 14px; margin-bottom: 8px; }}
        .video-stats {{ color: #999; font-size: 12px; margin-bottom: 8px; }}
        .video-duration {{ color: #ff0000; font-size: 12px; font-weight: bold; }}
        .watch-btn {{ display: inline-block; background: #ff0000; color: white; padding: 10px 20px; 
                     text-decoration: none; border-radius: 6px; margin-top: 10px; transition: background 0.3s; }}
        .watch-btn:hover {{ background: #cc0000; }}
        .footer {{ text-align: center; color: white; margin-top: 40px; padding: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🎓 {title}</h1>
        <div class="stats">
            📊 {len(processed_videos)} videos curated for you
        </div>
        <div class="video-grid">
"""
        
        for video in processed_videos[:50]:  # Limit to 50 videos
            # Format duration
            minutes = video['duration_seconds'] // 60
            seconds = video['duration_seconds'] % 60
            duration_str = f"{minutes}:{seconds:02d}"
            
            # Format view count
            view_count = video['view_count']
            if view_count >= 1000000:
                view_str = f"{view_count/1000000:.1f}M"
            elif view_count >= 1000:
                view_str = f"{view_count/1000:.1f}K"
            else:
                view_str = str(view_count)
            
            # Format like count
            like_count = video['like_count']
            if like_count >= 1000000:
                like_str = f"{like_count/1000000:.1f}M"
            elif like_count >= 1000:
                like_str = f"{like_count/1000:.1f}K"
            else:
                like_str = str(like_count)
            
            html_content += f"""
        <div class="video-card">
            <img src="{video['thumbnail']}" alt="{video['title']}">
            <div class="video-info">
                <div class="video-title">{video['title'][:100]}</div>
                <div class="video-channel">📺 {video['channel_title']}</div>
                <div class="video-stats">👁️ {view_str} views | 👍 {like_str} likes</div>
                <div class="video-duration">⏱️ Duration: {duration_str}</div>
                <a href="{video['url']}" target="_blank" class="watch-btn">▶ Watch on YouTube</a>
            </div>
        </div>
"""
        
        html_content += """
        </div>
        <div class="footer">
            <p>Curated with ❤️ using YouTube Data API | Generated on """ + str(pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')) + """</p>
            <p style="font-size: 12px;">⚠️ These videos are hosted on YouTube. Click "Watch on YouTube" to view them.</p>
        </div>
    </div>
</body>
</html>
"""
        
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        filename = self.html_folder / f"{safe_title.replace(' ', '_')}.html"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"✅ HTML playlist created: {filename}")
        return filename