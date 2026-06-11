# working_downloader_fixed.py
import subprocess
import sys
import os
from pathlib import Path

def check_ytdlp():
    """Check if yt-dlp is installed"""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        return True
    except:
        print("📦 Installing yt-dlp...")
        subprocess.run([sys.executable, '-m', 'pip', 'install', 'yt-dlp'])
        return True

def download_video_simple(video_url, output_folder='my_videos'):
    """Simple download that should work"""
    
    Path(output_folder).mkdir(exist_ok=True)
    
    print(f"\n📥 Downloading: {video_url}")
    print(f"📁 Saving to: {output_folder}/")
    print("-" * 50)
    
    # Try format 22 (mp4) which often works
    cmd = [
        'yt-dlp',
        '-f', '22',  # Format 22 = MP4 720p
        '-o', f'{output_folder}/%(title)s.%(ext)s',
        '--no-playlist',
        video_url
    ]
    
    result = subprocess.run(cmd)
    
    if result.returncode == 0:
        print("\n✅ Download complete!")
        return True
    
    # If format 22 fails, try best
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

def download_with_workaround(video_url, output_folder='my_videos'):
    """Download with workaround for 403 errors"""
    
    Path(output_folder).mkdir(exist_ok=True)
    
    # Use android player client (often bypasses restrictions)
    cmd = [
        'yt-dlp',
        '--extractor-args', 'youtube:player_client=android',
        '-f', 'best',
        '-o', f'{output_folder}/%(title)s.%(ext)s',
        '--no-playlist',
        video_url
    ]
    
    print(f"\n📥 Using Android client workaround...")
    result = subprocess.run(cmd)
    return result.returncode == 0

def main():
    print("🎬 Download Your Own YouTube Video")
    print("=" * 50)
    
    video_url = "https://youtube.com/watch?v=ukzFI9rgwfU"
    
    print(f"\n📹 Video: {video_url}")
    confirm = input("\n✅ Is this YOUR video? (y/n): ")
    
    if confirm.lower() != 'y':
        print("\n⚠️ This tool only works for content you own.")
        return
    
    # Check yt-dlp
    check_ytdlp()
    
    print("\n🚀 Starting download...")
    
    # Try methods in order
    methods = [
        ("Simple download", download_video_simple),
        ("Android client workaround", download_with_workaround),
    ]
    
    success = False
    for method_name, method_func in methods:
        print(f"\n📋 Trying: {method_name}")
        if method_func(video_url):
            success = True
            break
        print(f"   {method_name} failed, trying next...")
    
    if success:
        print("\n" + "=" * 50)
        print("✨ SUCCESS! Your video has been downloaded.")
        print("📁 Check the 'my_videos' folder")
        
        # List downloaded files
        files = list(Path('my_videos').glob('*.mp4'))
        if files:
            print(f"\n📁 Downloaded files:")
            for f in files:
                size = f.stat().st_size / (1024 * 1024)
                print(f"   - {f.name} ({size:.1f} MB)")
    else:
        print("\n" + "=" * 50)
        print("❌ All automatic methods failed.")
        print("\n💡 Since this is YOUR video, use YouTube Studio:")
        print("   1. Go to https://studio.youtube.com/")
        print("   2. Click 'Content'")
        print("   3. Find your video")
        print("   4. Click the 3 dots (⋮) → Download")
        print("\n   This is the official method and always works!")

if __name__ == "__main__":
    main()