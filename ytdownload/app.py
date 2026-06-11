# render_downloader.py
import subprocess
import sys
import os
import re
from pathlib import Path

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

def get_render_temp_folder():
    """Get Render's temporary folder path"""
    # Render uses /tmp for temporary storage
    temp_folder = os.environ.get('RENDER_TMP_DIR', '/tmp')
    # Also check common temp locations
    if not os.path.exists(temp_folder):
        temp_folder = '/tmp'
    return temp_folder

def extract_urls_from_discovery(discovery_file):
    """Extract YouTube URLs from discovery results file"""
    urls = []
    
    if not os.path.exists(discovery_file):
        print(f"❌ Discovery file not found: {discovery_file}")
        return urls
    
    print(f"📖 Reading discovery file: {discovery_file}")
    
    with open(discovery_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all URLs in the file
    url_pattern = r'URL:\s*(https?://youtube\.com/watch\?v=[^\s\n]+)'
    matches = re.findall(url_pattern, content)
    
    # Also get titles for reference
    title_pattern = r'TITLE:\s*(.+?)(?=\n)'
    titles = re.findall(title_pattern, content)
    
    for i, url in enumerate(matches):
        title = titles[i] if i < len(titles) else "Unknown"
        urls.append({
            'url': url,
            'title': title,
            'channel': None  # Could extract channel too if needed
        })
    
    print(f"✅ Found {len(urls)} video URLs in discovery file")
    return urls

def download_video_to_temp(video_url, output_folder=None):
    """Download video to Render's temp folder"""
    
    if output_folder is None:
        output_folder = get_render_temp_folder()
    
    # Create output folder if it doesn't exist
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    print(f"\n📥 Downloading: {video_url}")
    print(f"📁 Saving to: {output_folder}/")
    print(f"💾 Available space: {check_disk_space(output_folder)}")
    print("-" * 50)
    
    # Try format 22 (mp4) first
    cmd = [
        'yt-dlp',
        '-f', '22',
        '-o', f'{output_folder}/%(title)s.%(ext)s',
        '--no-playlist',
        video_url
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ Download complete!")
        return True
    
    # Try best format as fallback
    print("\n🔄 Trying best format...")
    cmd = [
        'yt-dlp',
        '-f', 'best',
        '-o', f'{output_folder}/%(title)s.%(ext)s',
        '--no-playlist',
        video_url
    ]
    
    result = subprocess.run(cmd)
    return result.returncode == 0

def download_all_from_discovery(discovery_file, max_downloads=None, output_folder=None):
    """Download all videos from discovery results"""
    
    if output_folder is None:
        output_folder = get_render_temp_folder()
    
    # Extract URLs from discovery file
    videos = extract_urls_from_discovery(discovery_file)
    
    if not videos:
        print("❌ No videos found in discovery file")
        return
    
    # Limit downloads if specified
    if max_downloads and max_downloads < len(videos):
        videos = videos[:max_downloads]
        print(f"📊 Limiting to first {max_downloads} videos")
    
    print(f"\n🚀 Starting download of {len(videos)} videos to {output_folder}")
    print("=" * 50)
    
    success_count = 0
    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] {video['title'][:60]}...")
        if download_video_to_temp(video['url'], output_folder):
            success_count += 1
    
    print(f"\n📊 Download complete: {success_count}/{len(videos)} successful")
    
    # List downloaded files
    list_downloaded_files(output_folder)
    
    return success_count

def list_downloaded_files(folder):
    """List all downloaded video files"""
    folder_path = Path(folder)
    files = list(folder_path.glob('*.mp4')) + list(folder_path.glob('*.MP4'))
    
    if files:
        print(f"\n📁 Downloaded files in {folder}:")
        for f in files:
            size_mb = f.stat().st_size / (1024 * 1024)
            print(f"   - {f.name} ({size_mb:.1f} MB)")
    else:
        print(f"\n📁 No video files found in {folder}")

def check_disk_space(folder):
    """Check available disk space in folder"""
    try:
        import shutil
        stat = shutil.disk_usage(folder)
        free_gb = stat.free / (1024**3)
        return f"{free_gb:.2f} GB free"
    except:
        return "Unknown"

def main():
    print("🎬 Render YouTube Downloader")
    print("=" * 50)
    
    # Get Render's temp folder
    temp_folder = get_render_temp_folder()
    print(f"📁 Render temp folder: {temp_folder}")
    print(f"💾 Disk space: {check_disk_space(temp_folder)}")
    
    # Path to discovery results
    discovery_file = r'C:\Users\PC\Desktop\youtube_discovery\youtube_discovery_results\descriptions\full_descriptions_20260611_195018.txt'
    
    # For Render deployment, use relative path
    if not os.path.exists(discovery_file):
        # Try relative path for Render
        discovery_file = 'youtube_discovery_results/descriptions/full_descriptions_20260611_195018.txt'
    
    while True:
        print("\n" + "=" * 50)
        print("📋 Options:")
        print("1. Download ALL videos from discovery results")
        print("2. Download specific number of videos (top N)")
        print("3. Download single video by URL")
        print("4. Show downloaded files")
        print("5. Exit")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            confirm = input(f"\nDownload ALL videos to {temp_folder}? (y/n): ")
            if confirm.lower() == 'y':
                check_ytdlp()
                download_all_from_discovery(discovery_file, output_folder=temp_folder)
        
        elif choice == '2':
            try:
                num = int(input("How many videos to download (top N): "))
                confirm = input(f"\nDownload top {num} videos to {temp_folder}? (y/n): ")
                if confirm.lower() == 'y':
                    check_ytdlp()
                    download_all_from_discovery(discovery_file, max_downloads=num, output_folder=temp_folder)
            except ValueError:
                print("❌ Please enter a valid number")
        
        elif choice == '3':
            video_url = input("Enter YouTube URL: ").strip()
            if video_url:
                confirm = input(f"\nIs this YOUR video? (y/n): ")
                if confirm.lower() == 'y':
                    check_ytdlp()
                    download_video_to_temp(video_url, temp_folder)
                else:
                    print("⚠️ This tool only works for content you own.")
        
        elif choice == '4':
            list_downloaded_files(temp_folder)
        
        elif choice == '5':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid option")

if __name__ == "__main__":
    main()