# youtube_search.py
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
from datetime import datetime
import time
import os
from pathlib import Path
from config import Config

class YouTubeSearcher:
    def __init__(self, output_folder='youtube_discovery_results'):
        self.youtube = build('youtube', 'v3', developerKey=Config.API_KEY)
        self.all_videos = []
        self.output_folder = output_folder
        self.create_output_folder()
    
    def create_output_folder(self):
        """Create the output folder if it doesn't exist"""
        Path(self.output_folder).mkdir(parents=True, exist_ok=True)
        print(f"📁 Output folder: {self.output_folder}/")
        
        # Create subfolders
        subfolders = ['csv', 'json', 'txt', 'html', 'playlists', 'templates', 'descriptions']
        for subfolder in subfolders:
            Path(f"{self.output_folder}/{subfolder}").mkdir(parents=True, exist_ok=True)
    
    def search_videos(self, query, max_results=Config.MAX_RESULTS):
        """Search YouTube videos based on query"""
        try:
            request = self.youtube.search().list(
                q=query,
                part='snippet',
                type='video',
                maxResults=max_results,
                order='relevance',
                relevanceLanguage='en',
                videoDuration='medium'
            )
            response = request.execute()
            
            # Get video details (duration, views, etc.)
            video_ids = [item['id']['videoId'] for item in response['items']]
            detailed_videos = self.get_video_details(video_ids)
            
            return detailed_videos
            
        except HttpError as e:
            print(f"An error occurred: {e}")
            return []
    
    def get_video_details(self, video_ids):
        """Get detailed information about videos including FULL descriptions"""
        try:
            request = self.youtube.videos().list(
                part='snippet,contentDetails,statistics',
                id=','.join(video_ids)
            )
            response = request.execute()
            
            videos = []
            for item in response['items']:
                # Convert ISO 8601 duration to seconds
                duration = self.parse_duration(item['contentDetails']['duration'])
                
                # Get FULL description (not truncated)
                full_description = item['snippet'].get('description', '')
                
                # Get thumbnails
                thumbnails = item['snippet'].get('thumbnails', {})
                
                # Apply duration filters
                if Config.MIN_DURATION <= duration <= Config.MAX_DURATION:
                    videos.append({
                        'video_id': item['id'],
                        'title': item['snippet']['title'],
                        'description': full_description,  # FULL description here!
                        'description_preview': full_description[:200] + '...' if len(full_description) > 200 else full_description,
                        'channel_title': item['snippet']['channelTitle'],
                        'channel_id': item['snippet']['channelId'],
                        'published_at': item['snippet']['publishedAt'],
                        'duration_seconds': duration,
                        'view_count': int(item['statistics'].get('viewCount', 0)),
                        'like_count': int(item['statistics'].get('likeCount', 0)),
                        'comment_count': int(item['statistics'].get('commentCount', 0)),
                        'url': f"https://youtube.com/watch?v={item['id']}",
                        'thumbnail_default': thumbnails.get('default', {}).get('url', ''),
                        'thumbnail_medium': thumbnails.get('medium', {}).get('url', ''),
                        'thumbnail_high': thumbnails.get('high', {}).get('url', ''),
                        'tags': item['snippet'].get('tags', []),
                        'category_id': item['snippet'].get('categoryId', '')
                    })
            
            return videos
            
        except HttpError as e:
            print(f"Error getting video details: {e}")
            return []
    
    def parse_duration(self, duration):
        """Convert ISO 8601 duration to seconds"""
        import re
        pattern = r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?'
        match = re.match(pattern, duration)
        
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        
        return hours * 3600 + minutes * 60 + seconds
    
    def search_multiple_terms(self, terms=None):
        """Search for multiple terms and combine results"""
        if terms is None:
            terms = Config.SEARCH_TERMS
        
        for term in terms:
            print(f"Searching for: {term}")
            videos = self.search_videos(term)
            for video in videos:
                video['search_term'] = term
            
            self.all_videos.extend(videos)
            time.sleep(1)
        
        return self.all_videos
    
    def export_to_csv(self, filename='youtube_results.csv'):
        """Export results to CSV in the csv subfolder"""
        if self.all_videos:
            filepath = f"{self.output_folder}/csv/{filename}"
            df = pd.DataFrame(self.all_videos)
            df.to_csv(filepath, index=False, encoding='utf-8')
            print(f"Exported {len(self.all_videos)} videos to {filepath}")
            return df
        return None
    
    def export_full_descriptions(self, timestamp):
        """Export full descriptions to JSON and TXT files in descriptions folder"""
        
        descriptions_folder = Path(self.output_folder) / 'descriptions'
        descriptions_folder.mkdir(parents=True, exist_ok=True)
        
        descriptions_data = []
        
        for video in self.all_videos:
            descriptions_data.append({
                'video_id': video.get('video_id', ''),
                'title': video.get('title', ''),
                'channel': video.get('channel_title', ''),
                'url': video.get('url', ''),
                'view_count': video.get('view_count', 0),
                'like_count': video.get('like_count', 0),
                'comment_count': video.get('comment_count', 0),
                'published_at': video.get('published_at', ''),
                'duration_seconds': video.get('duration_seconds', 0),
                'full_description': video.get('description', ''),
                'description_length': len(video.get('description', '')),
                'tags': video.get('tags', []),
                'search_term': video.get('search_term', '')
            })
        
        # Save as JSON in json subfolder
        json_file = descriptions_folder / f"full_descriptions_{timestamp}.json"
        import json
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(descriptions_data, f, indent=2, ensure_ascii=False)
        
        # Save as readable text in txt subfolder
        txt_file = descriptions_folder / f"full_descriptions_{timestamp}.txt"
        with open(txt_file, 'w', encoding='utf-8') as f:
            for video in descriptions_data:
                f.write("=" * 80 + "\n")
                f.write(f"TITLE: {video['title']}\n")
                f.write(f"CHANNEL: {video['channel']}\n")
                f.write(f"URL: {video['url']}\n")
                f.write(f"VIEWS: {video['view_count']:,}\n")
                f.write(f"LIKES: {video['like_count']:,}\n")
                f.write(f"TAGS: {', '.join(video.get('tags', [])[:10])}\n")
                f.write("-" * 80 + "\n")
                f.write("DESCRIPTION:\n")
                f.write(video['full_description'] + "\n")
                f.write("\n" + "=" * 80 + "\n\n")
        
        print(f"   ✅ Full descriptions saved to: {descriptions_folder}/")
        return json_file
    
    def get_video_description_by_url(self, video_url):
        """Get description for a single video by URL"""
        
        # Extract video ID from URL
        video_id = video_url.split('v=')[-1].split('&')[0]
        
        # Use the existing get_video_details method
        videos = self.get_video_details([video_id])
        
        if videos:
            return {
                'title': videos[0]['title'],
                'description': videos[0]['description'],
                'channel': videos[0]['channel_title'],
                'url': videos[0]['url'],
                'view_count': videos[0]['view_count'],
                'like_count': videos[0]['like_count']
            }
        return None
    
    def get_statistics(self):
        """Get statistics about the search results"""
        if not self.all_videos:
            return {}
        
        df = pd.DataFrame(self.all_videos)
        stats = {
            'total_videos': len(df),
            'unique_channels': df['channel_title'].nunique(),
            'total_views': df['view_count'].sum(),
            'average_views': df['view_count'].mean(),
            'average_duration': df['duration_seconds'].mean() / 60,
            'avg_description_length': df['description'].str.len().mean(),
            'top_channels': df.groupby('channel_title')['view_count'].sum().nlargest(5).to_dict(),
            'videos_by_term': df['search_term'].value_counts().to_dict()
        }
        return stats