import asyncio
from downloader_async import AsyncTSEDownloader
import sys

# Define target states for South Region
SUL_STATES = ['pr', 'sc', 'rs']

async def download_sul():
    print("🚀 Starting Async Download for SOUTH Region (PR, SC, RS)...")
    # Reduced concurrency to avoid rate limiting/blocking
    downloader = AsyncTSEDownloader(max_concurrent=3) 
    
    for uf in SUL_STATES:
        print(f"\n📥 Downloading {uf.upper()}...")
        # No limit - full download
        await downloader.download_uf(uf)
        
    print("\n✅ All South Region downloads completed!")

if __name__ == "__main__":
    # Check if we can import config
    try:
        from config import config
        print(f"Target Directory: {config.RAW_LOGS_DIR}")
    except ImportError:
        print("Warning: Could not import config")
        
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(download_sul())
