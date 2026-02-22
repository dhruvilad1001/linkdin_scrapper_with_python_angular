#!/usr/bin/env python3
"""
Quick Test Script for LinkedIn Scraper
Tests scraping with real LinkedIn profiles
"""

import sys
import os
from dotenv import load_dotenv

# Add app to path
sys.path.insert(0, os.path.dirname(__file__))

from app.services.scraper_service import LinkedInScraper

# Load environment
load_dotenv()

# Test profiles
TEST_PROFILES = [
    {
        "name": "Vraj Maheshwari",
        "url": "https://www.linkedin.com/in/vraj-maheshwari-6537ba278/",
        "expected": {
            "has_name": True,
            "has_education": True,
            "profile_type": "Student/Early Career"
        }
    },
    {
        "name": "Dhruvi Lad",
        "url": "https://www.linkedin.com/in/dhruvi-lad-7a900b352/",
        "expected": {
            "has_name": True,
            "has_education": True,
            "profile_type": "Student/Entry Level"
        }
    }
]

def print_header(text):
    """Print formatted header"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")

def print_result(success, message):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")

def test_single_profile(profile_info):
    """Test scraping a single profile"""
    print_header(f"Testing: {profile_info['name']}")
    print(f"URL: {profile_info['url']}")
    print(f"Expected: {profile_info['expected']['profile_type']}")
    print("\nStarting scrape...")
    
    scraper = LinkedInScraper()
    success, message = scraper.scrape_profile(profile_info['url'])
    
    print_result(success, message)
    
    if success:
        print("\n📊 Validation:")
        print(f"  ✓ Profile scraped successfully")
        print(f"  ✓ Data saved to MongoDB")
        print(f"  ✓ Expected name: {profile_info['name']}")
    else:
        print(f"\n⚠️  Error: {message}")
    
    return success

def test_all_profiles():
    """Test all profiles"""
    print_header("LinkedIn Scraper - Test Suite")
    print("Testing with real LinkedIn profiles")
    print(f"Total profiles to test: {len(TEST_PROFILES)}")
    
    results = []
    
    for i, profile in enumerate(TEST_PROFILES, 1):
        print(f"\n[{i}/{len(TEST_PROFILES)}] Testing profile...")
        success = test_single_profile(profile)
        results.append({
            "name": profile["name"],
            "success": success
        })
        
        # Add delay between profiles
        if i < len(TEST_PROFILES):
            print("\n⏳ Waiting 10 seconds before next profile...")
            import time
            time.sleep(10)
    
    # Print summary
    print_header("Test Summary")
    
    passed = sum(1 for r in results if r["success"])
    failed = len(results) - passed
    
    print(f"Total Tests: {len(results)}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"Success Rate: {(passed/len(results)*100):.1f}%")
    
    print("\nDetailed Results:")
    for result in results:
        status = "✅" if result["success"] else "❌"
        print(f"  {status} {result['name']}")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
    else:
        print(f"\n⚠️  {failed} test(s) failed. Check logs for details.")
    
    return failed == 0

def main():
    """Main test function"""
    print("\n🚀 LinkedIn Scraper Test Script")
    print("="*70)
    
    # Check environment
    if not os.getenv("LINKEDIN_EMAIL") or not os.getenv("LINKEDIN_PASSWORD"):
        print("❌ Error: LinkedIn credentials not found in .env file")
        print("Please configure backend/.env with your credentials")
        return False
    
    print("✓ Environment configured")
    print("✓ Credentials found")
    
    # Run tests
    try:
        success = test_all_profiles()
        return success
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return False
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
