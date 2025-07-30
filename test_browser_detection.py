#!/usr/bin/env python3
"""
Test script to verify browser detection in Docker environment.
Run this inside the Docker container to test the browser setup.
"""

import subprocess
import os

def test_browser_detection():
    """Test browser and ChromeDriver detection"""
    print("=== Browser Detection Test ===")
    
    # Test browser binaries
    browser_paths = [
        "/usr/bin/google-chrome-stable",
        "/usr/bin/google-chrome", 
        "/usr/bin/chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser"
    ]
    
    print("\n--- Browser Binaries ---")
    for path in browser_paths:
        if os.path.exists(path):
            try:
                result = subprocess.run([path, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"✅ {path}: {result.stdout.strip()}")
                else:
                    print(f"❌ {path}: Failed to run")
            except Exception as e:
                print(f"❌ {path}: {e}")
        else:
            print(f"❌ {path}: Not found")
    
    # Test ChromeDriver
    driver_paths = [
        "/usr/local/bin/chromedriver",
        "/usr/bin/chromedriver",
        "chromedriver"
    ]
    
    print("\n--- ChromeDriver ---")
    for path in driver_paths:
        if os.path.exists(path) or path == "chromedriver":
            try:
                result = subprocess.run([path, "--version"], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    print(f"✅ {path}: {result.stdout.strip()}")
                else:
                    print(f"❌ {path}: Failed to run")
            except Exception as e:
                print(f"❌ {path}: {e}")
        else:
            print(f"❌ {path}: Not found")
    
    # Test architecture
    print("\n--- Architecture ---")
    try:
        result = subprocess.run(["dpkg", "--print-architecture"], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            arch = result.stdout.strip()
            print(f"✅ Architecture: {arch}")
        else:
            print("❌ Could not determine architecture")
    except Exception as e:
        print(f"❌ Architecture detection failed: {e}")

if __name__ == "__main__":
    test_browser_detection() 