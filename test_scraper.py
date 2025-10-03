#!/usr/bin/env python3
"""
Test script for Firecrawl integration with BeautifulSoup fallback
"""
import os
import sys

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_scraper():
    """Test the scraper with fallback mechanism"""
    from api.scraper import WebsiteScraper
    
    print("=" * 60)
    print("Testing Firmable Web Scraper with Fallback")
    print("=" * 60)
    print()
    
    # Initialize scraper
    print("Initializing scraper...")
    try:
        scraper = WebsiteScraper()
        print(f"✅ Scraper initialized")
        print(f"   Using Firecrawl: {scraper.use_firecrawl}")
        print()
    except Exception as e:
        print(f"❌ Failed to initialize scraper: {e}")
        return False
    
    # Test URL
    test_url = "https://example.com"
    print(f"Testing URL: {test_url}")
    print()
    
    try:
        # Scrape website
        result = scraper.scrape_website(test_url)
        
        # Display results
        print("✅ Scrape successful!")
        print()
        print("Results:")
        print(f"  Scraper used: {result.get('scraper_used', 'unknown')}")
        print(f"  Title: {result.get('title', 'N/A')}")
        print(f"  Description: {result.get('description', 'N/A')[:100]}...")
        print(f"  Chunks: {len(result.get('chunks', []))}")
        print(f"  Headings: {len(result.get('headings', []))}")
        print(f"  Internal links: {len(result.get('internal_pages', []))}")
        print(f"  External links: {len(result.get('external_links', []))}")
        print(f"  Emails found: {len(result.get('contact_info', {}).get('emails', []))}")
        print(f"  Phones found: {len(result.get('contact_info', {}).get('phones', []))}")
        print()
        
        # Show first chunk
        if result.get('chunks'):
            print("First chunk preview:")
            print("-" * 60)
            print(result['chunks'][0][:300] + "...")
            print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ Scrape failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_both_scrapers():
    """Test both Firecrawl and BeautifulSoup"""
    print("\n" + "=" * 60)
    print("Testing Both Scrapers")
    print("=" * 60)
    
    # Test with Firecrawl if available
    firecrawl_key = os.environ.get("FIRECRAWL_API_KEY")
    if firecrawl_key:
        print("\n🔥 Testing with Firecrawl...")
        test_scraper()
    else:
        print("\n⚠️  No FIRECRAWL_API_KEY found, skipping Firecrawl test")
    
    # Test with BeautifulSoup fallback
    print("\n🥣 Testing BeautifulSoup fallback...")
    # Temporarily remove Firecrawl key to force fallback
    original_key = os.environ.get("FIRECRAWL_API_KEY")
    if original_key:
        del os.environ["FIRECRAWL_API_KEY"]
    
    test_scraper()
    
    # Restore key
    if original_key:
        os.environ["FIRECRAWL_API_KEY"] = original_key

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test Firmable scraper")
    parser.add_argument("--both", action="store_true", help="Test both scrapers")
    args = parser.parse_args()
    
    if args.both:
        test_both_scrapers()
    else:
        success = test_scraper()
        sys.exit(0 if success else 1)
