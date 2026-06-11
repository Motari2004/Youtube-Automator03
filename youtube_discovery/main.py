#!/usr/bin/env python3
from youtube_search import YouTubeSearcher
from video_analyzer import VideoAnalyzer
from playlist_manager import PlaylistManager
from config import Config
import json
from datetime import datetime
import numpy as np
import pandas as pd
from pathlib import Path

def convert_to_serializable(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, (np.integer, np.int64)):
        return int(obj)
    elif isinstance(obj, (np.floating, np.float64)):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, pd.Series):
        return obj.to_dict()
    elif isinstance(obj, pd.DataFrame):
        return obj.to_dict('records')
    return obj

















def save_video_urls(videos, output_folder='youtube_discovery_results'):
    """Save all video URLs to a file for downloading"""
    
    urls_folder = Path(output_folder) / 'urls'
    urls_folder.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    urls_file = urls_folder / f'video_urls_{timestamp}.txt'
    
    with open(urls_file, 'w', encoding='utf-8') as f:
        for video in videos:
            f.write(f"{video.get('title', 'Unknown')}|{video.get('url', '')}\n")
    
    print(f"   ✅ Video URLs saved to: {urls_file}")
    return urls_file

def save_top_video_urls(videos, top_n=10, output_folder='youtube_discovery_results'):
    """Save only top N video URLs by views"""
    
    urls_folder = Path(output_folder) / 'urls'
    urls_folder.mkdir(parents=True, exist_ok=True)
    
    # Sort by views
    sorted_videos = sorted(videos, key=lambda x: x.get('view_count', 0), reverse=True)
    top_videos = sorted_videos[:top_n]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    urls_file = urls_folder / f'top_{top_n}_urls_{timestamp}.txt'
    
    with open(urls_file, 'w', encoding='utf-8') as f:
        for video in top_videos:
            f.write(f"{video.get('title', 'Unknown')}|{video.get('url', '')}|{video.get('view_count', 0)}\n")
    
    print(f"   ✅ Top {top_n} video URLs saved to: {urls_file}")
    return urls_file
















def generate_markdown_report(videos, stats, best_practices, keywords, top_videos, timestamp, output_folder='youtube_discovery_results'):
    """Generate a markdown report with all findings"""
    
    # Create reports folder
    reports_folder = Path(output_folder) / 'reports'
    reports_folder.mkdir(parents=True, exist_ok=True)
    
    markdown_content = f"""# YouTube Video Discovery Report

**Generated on:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

This report contains an analysis of {stats['total_videos']} programming tutorial videos discovered across {stats['unique_channels']} unique channels.

### Key Metrics

- **Total Videos Analyzed:** {stats['total_videos']}
- **Unique Channels:** {stats['unique_channels']}
- **Total Views:** {stats['total_views']:,}
- **Average Views per Video:** {stats['average_views']:,.0f}
- **Average Video Duration:** {stats['average_duration']:.1f} minutes

## Top Performing Videos

| Rank | Title | Channel | Views | URL |
|------|-------|---------|-------|-----|
"""
    
    for i, video in enumerate(top_videos[:10], 1):
        title = video.get('title', 'Unknown')[:50]
        channel = video.get('channel_title', 'Unknown')
        views = video.get('view_count', 0)
        url = video.get('url', '#')
        markdown_content += f"| {i} | {title}... | {channel} | {views:,} | [Watch]({url}) |\n"
    
    markdown_content += f"""
## Best Practices Analysis

### Video Length
- **Optimal Duration:** {best_practices.get('optimal_duration_minutes', 'N/A')} minutes
- **Average Duration of Top Videos:** {stats['average_duration']:.1f} minutes

### Title Optimization
- **Optimal Title Length:** {best_practices.get('optimal_title_length', 'N/A')} characters

## Popular Keywords

| Keyword | Mentions |
|---------|----------|
"""
    
    for keyword, count in list(keywords.items())[:15]:
        markdown_content += f"| {keyword} | {count} |\n"
    
    markdown_content += f"""
## Channel Distribution

Top channels by total views:

"""
    
    if 'top_channels' in stats:
        for channel, views in list(stats['top_channels'].items())[:5]:
            markdown_content += f"- **{channel}:** {views:,} total views\n"
    
    markdown_content += f"""
## Search Term Performance

| Search Term | Videos Found |
|-------------|--------------|
"""
    
    if 'videos_by_term' in stats:
        for term, count in stats['videos_by_term'].items():
            markdown_content += f"| {term} | {count} |\n"
    
    markdown_content += f"""
## Recommendations

Based on the analysis of {stats['total_videos']} successful programming tutorial videos:

1. **Keep videos concise** - The optimal length is around {best_practices.get('optimal_duration_minutes', 10)} minutes
2. **Use keywords strategically** - Focus on high-performing keywords like: {', '.join(list(keywords.keys())[:5])}
3. **Title matters** - Keep titles around {best_practices.get('optimal_title_length', 60)} characters
4. **Engage your audience** - Top videos show strong engagement with interactive content

## Raw Data

The complete dataset is available in:
- `youtube_search_{timestamp}.csv` - All video data
- `analysis_report.json` - Complete analysis in JSON format

---
*Report generated by YouTube Video Discovery Tool*
"""
    
    # Save to reports folder
    report_path = reports_folder / 'analysis_report.md'
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
    
    print(f"   ✅ analysis_report.md saved to {report_path}")

def main():
    print("🎬 YouTube Video Discovery Tool")
    print("=" * 40)
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        return
    
    # Initialize searcher
    searcher = YouTubeSearcher()
    
    # Search for videos
    print(f"\n🔍 Searching for: {', '.join(Config.SEARCH_TERMS)}")
    print("-" * 40)
    
    videos = searcher.search_multiple_terms()
    
    if not videos:
        print("❌ No videos found. Please check your API key and search terms.")
        return
    
    print(f"\n✅ Found {len(videos)} videos")
    
    
    
    
    
    
    # Export raw results
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    df = searcher.export_to_csv(f"youtube_search_{timestamp}.csv")
    
    # Export full descriptions to JSON and TXT files
    print("\n📝 Exporting full video descriptions...")
    searcher.export_full_descriptions(timestamp)
    
    # ========== ADD THESE LINES ==========
    # Save video URLs for downloading
    print("\n🔗 Saving video URLs for download...")
    save_video_urls(videos, Config.OUTPUT_DIR)
    save_top_video_urls(videos, top_n=10, output_folder=Config.OUTPUT_DIR)
    # ========== END OF ADDED LINES ==========
    
    # Get statistics
    stats = searcher.get_statistics()
    
    
    
    
    
    print("\n📊 Statistics:")
    print(f"   Total videos: {stats['total_videos']}")
    print(f"   Unique channels: {stats['unique_channels']}")
    print(f"   Total views: {stats['total_views']:,}")
    print(f"   Average views: {stats['average_views']:,.0f}")
    print(f"   Average duration: {stats['average_duration']:.1f} minutes")
    
    # Analyze videos
    analyzer = VideoAnalyzer(videos)
    
    print("\n🔥 Top Performing Videos (by views):")
    top_videos = analyzer.find_top_performers('view_count', 10)
    
    # Ensure top_videos have all necessary fields
    for i, video in enumerate(top_videos[:5], 1):
        # Find the full video data to ensure we have all fields
        full_video = next((v for v in videos if v.get('url') == video.get('url')), None)
        if full_video:
            # Update the video with missing fields
            for key in ['duration_seconds', 'thumbnail', 'like_count', 'comment_count']:
                if key not in video and key in full_video:
                    video[key] = full_video[key]
        
        print(f"   {i}. {video['title'][:60]}...")
        print(f"      {video['url']} - {video['view_count']:,} views")
    
    print("\n📈 Most Engaged Videos (by engagement rate):")
    engaged_videos = analyzer.find_engagement_rate()
    for i, video in enumerate(engaged_videos[:5], 1):
        engagement = video.get('engagement_rate', 0)
        title = video.get('title', 'Unknown')[:50]
        print(f"   {i}. {title}... - {engagement:.2f}% engagement")
    
    print("\n💡 Best Practices Found:")
    best_practices = analyzer.find_best_practices()
    print(f"   Optimal video length: {best_practices.get('optimal_duration_minutes', 'N/A')} minutes")
    print(f"   Optimal title length: {best_practices.get('optimal_title_length', 'N/A')} characters")
    
    if 'best_posting_times' in best_practices:
        posting = best_practices['best_posting_times']
        if 'best_hours' in posting:
            print(f"   Best posting hours: {list(posting['best_hours'].keys())}")
        if 'best_days' in posting:
            print(f"   Best posting days: {list(posting['best_days'].keys())}")
    
    print("\n🔑 Popular Keywords in Top Videos:")
    keywords = analyzer.analyze_keywords()
    for keyword, count in list(keywords.items())[:10]:
        print(f"   • {keyword}: {count} mentions")
    
    # Create playlist files
    playlist_manager = PlaylistManager(Config.API_KEY, Config.OUTPUT_DIR)
    
    print("\n📝 Creating playlist files...")
    try:
        for term in Config.SEARCH_TERMS:
            term_videos = [v for v in videos if v.get('search_term') == term]
            if term_videos:
                # Sort by view count and take top 20
                sorted_videos = sorted(term_videos, key=lambda x: x.get('view_count', 0), reverse=True)
                playlist_manager.create_playlist_file(
                    sorted_videos[:20],  # Top 20 per term
                    f"{term} - Curated Tutorials"
                )
    except Exception as e:
        print(f"⚠️ Could not create playlist files: {e}")
    
    # Generate HTML playlist
    print("\n📄 Generating HTML playlist...")
    try:
        # Ensure top_videos has duration_seconds for HTML generation
        videos_with_duration = []
        for video in top_videos[:20]:
            if 'duration_seconds' not in video:
                # Find the full video data
                full_video = next((v for v in videos if v.get('url') == video.get('url')), None)
                if full_video:
                    video['duration_seconds'] = full_video.get('duration_seconds', 600)
                    video['thumbnail'] = full_video.get('thumbnail', '')
                    video['like_count'] = full_video.get('like_count', 0)
                else:
                    video['duration_seconds'] = 600  # Default 10 minutes
                    video['thumbnail'] = ''
                    video['like_count'] = 0
            videos_with_duration.append(video)
        
        playlist_manager.generate_html_embed(
            videos_with_duration,
            "Best Programming Tutorials - Curated Collection"
        )
    except Exception as e:
        print(f"⚠️ Could not generate HTML: {e}")
        import traceback
        traceback.print_exc()
    
    # Generate markdown report
    print("\n📝 Generating markdown report...")
    try:
        generate_markdown_report(videos, stats, best_practices, keywords, top_videos[:10], timestamp, Config.OUTPUT_DIR)
    except Exception as e:
        print(f"⚠️ Could not generate markdown report: {e}")
    
    # Save complete analysis report as JSON with proper serialization
    print("\n💾 Saving JSON report...")
    
    try:
        # Create json folder
        json_folder = Path(Config.OUTPUT_DIR) / 'json'
        json_folder.mkdir(parents=True, exist_ok=True)
        
        # Convert all numpy types to Python native types
        stats_clean = {}
        for key, value in stats.items():
            stats_clean[key] = convert_to_serializable(value)
        
        top_videos_clean = []
        for video in top_videos[:10]:
            clean_video = {}
            for k, v in video.items():
                clean_video[k] = convert_to_serializable(v)
            top_videos_clean.append(clean_video)
        
        best_practices_clean = {}
        for key, value in best_practices.items():
            best_practices_clean[key] = convert_to_serializable(value)
        
        keywords_clean = {}
        for key, value in keywords.items():
            keywords_clean[key] = convert_to_serializable(value)
        
        engaged_videos_clean = []
        for video in engaged_videos[:5]:
            clean_video = {}
            for k, v in video.items():
                clean_video[k] = convert_to_serializable(v)
            engaged_videos_clean.append(clean_video)
        
        report = {
            'search_terms': Config.SEARCH_TERMS,
            'timestamp': datetime.now().isoformat(),
            'statistics': stats_clean,
            'top_videos': top_videos_clean,
            'best_practices': best_practices_clean,
            'top_keywords': keywords_clean,
            'engagement_leaders': engaged_videos_clean
        }
        
        # Save to json folder
        json_path = json_folder / 'analysis_report.json'
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        print(f"   ✅ analysis_report.json saved to {json_path}")
        
    except Exception as e:
        print(f"⚠️ Could not save JSON report: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n✨ Done! Check the generated files:")
    print(f"   📊 {Config.OUTPUT_DIR}/csv/youtube_search_*.csv - Complete video data")
    print(f"   📁 {Config.OUTPUT_DIR}/playlists/*_playlist.json - Playlist data")
    print(f"   📄 {Config.OUTPUT_DIR}/playlists/*_urls.txt - Video URLs")
    print(f"   🌐 {Config.OUTPUT_DIR}/html/*.html - Interactive gallery")
    print(f"   📝 {Config.OUTPUT_DIR}/reports/analysis_report.md - Markdown report")
    print(f"   💾 {Config.OUTPUT_DIR}/json/analysis_report.json - JSON analysis")

if __name__ == "__main__":
    main()