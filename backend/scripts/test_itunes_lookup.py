#!/usr/bin/env python3
"""
Test script to explore iTunes lookup API and see what metadata it actually returns.

This script will:
1. Search for a well-known song (e.g., "Bohemian Rhapsody" by Queen)
2. Get the track ID from search results
3. Call the lookup API to get comprehensive metadata
4. Pretty print all the fields to see what's available

Usage:
    python backend/scripts/test_itunes_lookup.py
"""

import json
import sys
from pathlib import Path

# Add backend app to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from app.services.itunes_service import search_itunes, lookup_itunes


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_field(name: str, value, indent: int = 0):
    """Print a field with proper formatting."""
    prefix = "  " * indent
    if isinstance(value, (list, dict)):
        print(f"{prefix}{name}:")
        print(f"{prefix}  {json.dumps(value, indent=2)}")
    else:
        print(f"{prefix}{name}: {value}")


def test_search_and_lookup():
    """Test both search and lookup to compare metadata richness."""
    
    # Test case: A well-known song with good metadata
    test_cases = [
        {
            "artist": "Queen",
            "title": "Bohemian Rhapsody",
            "description": "Classic rock song (should have comprehensive metadata)"
        },
        {
            "artist": "Taylor Swift",
            "title": "Shake It Off",
            "description": "Modern pop song (should have genre IDs and subgenres)"
        },
        {
            "artist": "The Beatles",
            "title": "Let It Be",
            "description": "Classic song (test copyright and collection info)"
        }
    ]
    
    for i, test_case in enumerate(test_cases, 1):
        print_section(f"TEST CASE {i}: {test_case['description']}")
        
        artist = test_case["artist"]
        title = test_case["title"]
        
        print(f"\nSearching for: '{title}' by {artist}")
        
        # Step 1: Search
        search_results = search_itunes(artist=artist, title=title, limit=1)
        
        if not search_results:
            print(f"❌ No search results found for '{title}' by {artist}")
            continue
        
        search_result = search_results[0]
        track_id = search_result.get("id")
        
        print(f"\n✅ Found track ID: {track_id}")
        
        print_section("SEARCH RESULT METADATA")
        print("\nFields from search_itunes():")
        for key, value in sorted(search_result.items()):
            if key != "rawData":  # Skip raw data for cleaner output
                print_field(key, value, indent=1)
        
        # Step 2: Lookup
        print(f"\n\nLooking up comprehensive metadata for track ID: {track_id}...")
        lookup_result = lookup_itunes(track_id)
        
        if not lookup_result:
            print(f"❌ Lookup failed for track ID: {track_id}")
            continue
        
        print_section("LOOKUP RESULT METADATA")
        print("\nFields from lookup_itunes():")
        for key, value in sorted(lookup_result.items()):
            if key not in ["rawData"]:  # Skip raw data
                print_field(key, value, indent=1)
        
        print_section("ARTWORK URL ANALYSIS")
        print("\nArtwork URLs found:")
        artwork_fields = ["artworkUrl30", "artworkUrl60", "artworkUrl100", "artworkUrl600"]
        for field in artwork_fields:
            value = lookup_result.get(field)
            if value:
                print(f"  ✅ {field}: {value}")
            else:
                print(f"  ❌ {field}: Not found")
        
        print_section("GENRE INFORMATION ANALYSIS")
        print("\nGenre-related fields:")
        genre_fields = ["genre", "primaryGenreId", "genreIds"]
        for field in genre_fields:
            value = lookup_result.get(field)
            print_field(field, value, indent=1)
        
        print_section("COMPLETE RAW RESPONSE")
        print("\nFull raw response from iTunes (for debugging):")
        print(json.dumps(lookup_result.get("rawData", {}), indent=2))
        
        print("\n" + "=" * 80)
        print("=" * 80 + "\n")


def main():
    """Main entry point."""
    print("\n" + "🎵" * 40)
    print("  iTunes Lookup API Metadata Explorer")
    print("🎵" * 40)
    
    try:
        test_search_and_lookup()
        
        print_section("TEST SUMMARY")
        print("\n✅ Test completed successfully!")
        print("\nKey findings to look for:")
        print("  1. Are artworkUrl30/60/100 present in search results?")
        print("  2. Does lookup provide artworkUrl600 or do we need URL manipulation?")
        print("  3. What's in genreIds array? Does it contain subgenres?")
        print("  4. What additional fields does lookup provide vs search?")
        print("  5. Is there any subgenre-specific information?")
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
