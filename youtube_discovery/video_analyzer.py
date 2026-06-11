import pandas as pd
from collections import Counter
import re

class VideoAnalyzer:
    def __init__(self, videos_data):
        self.videos = videos_data
        self.df = pd.DataFrame(videos_data) if videos_data else None
    
    def analyze_keywords(self):
        """Extract common keywords from video titles and descriptions"""
        if self.df is None:
            return {}
        
        all_text = ' '.join(self.df['title'].tolist() + self.df['description'].tolist())
        
        # Common programming keywords to look for
        keywords = ['python', 'javascript', 'java', 'react', 'angular', 'vue', 
                   'nodejs', 'django', 'flask', 'tutorial', 'beginner', 'advanced',
                   'api', 'database', 'sql', 'machine learning', 'ai', 'data science',
                   'web development', 'mobile development', 'cloud', 'aws', 'docker']
        
        keyword_counts = {}
        for keyword in keywords:
            count = len(re.findall(rf'\b{keyword}\b', all_text, re.IGNORECASE))
            if count > 0:
                keyword_counts[keyword] = count
        
        return dict(sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:20])
    
    def find_top_performers(self, metric='view_count', n=10):
        """Find top performing videos by specified metric"""
        if self.df is None:
            return []
        
        return self.df.nlargest(n, metric)[['title', 'channel_title', 'url', metric]].to_dict('records')
    
    def find_engagement_rate(self):
        """Calculate engagement rate for videos"""
        if self.df is None:
            return []
        
        self.df['engagement_rate'] = ((self.df['like_count'] + self.df['comment_count']) / self.df['view_count']) * 100
        return self.df[['title', 'channel_title', 'engagement_rate']].nlargest(10, 'engagement_rate').to_dict('records')
    
    def find_best_practices(self):
        """Analyze patterns in successful videos"""
        if self.df is None:
            return {}
        
        # Analyze video duration sweet spot
        top_10_by_views = self.df.nlargest(10, 'view_count')
        avg_duration_top = top_10_by_views['duration_seconds'].mean() / 60
        
        # Analyze title length
        top_10_by_views['title_length'] = top_10_by_views['title'].str.len()
        avg_title_length = top_10_by_views['title_length'].mean()
        
        return {
            'optimal_duration_minutes': round(avg_duration_top, 2),
            'optimal_title_length': round(avg_title_length, 2),
            'best_posting_times': self.analyze_posting_times()
        }
    
    def analyze_posting_times(self):
        """Analyze when top videos were published"""
        if self.df is None:
            return {}
        
        self.df['publish_hour'] = pd.to_datetime(self.df['published_at']).dt.hour
        self.df['publish_day'] = pd.to_datetime(self.df['published_at']).dt.day_name()
        
        top_videos = self.df.nlargest(20, 'view_count')
        top_hours = top_videos['publish_hour'].value_counts().head(3).to_dict()
        top_days = top_videos['publish_day'].value_counts().head(3).to_dict()
        
        return {'best_hours': top_hours, 'best_days': top_days}