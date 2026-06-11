# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    API_KEY = os.getenv('YOUTUBE_API_KEY')
    SEARCH_TERMS = [term.strip() for term in os.getenv('SEARCH_TERMS', '').split(',')]
    MAX_RESULTS = int(os.getenv('MAX_RESULTS_PER_TERM', 10))
    OUTPUT_DIR = os.getenv('OUTPUT_DIR', './youtube_discovery_results')  # New!
    
    # Video filters
    MIN_DURATION = 300  # minimum 5 minutes (in seconds)
    MAX_DURATION = 3600  # maximum 1 hour
    PUBLISHED_AFTER = '2024-01-01T00:00:00Z'
    
    @classmethod
    def validate(cls):
        if not cls.API_KEY or cls.API_KEY == 'your_api_key_here':
            raise ValueError("Please set your YouTube API key in .env file")
        return True