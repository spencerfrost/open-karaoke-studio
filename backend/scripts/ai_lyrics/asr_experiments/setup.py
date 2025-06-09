#!/usr/bin/env python3
"""
Install dependencies for ASR experiments.
Run this script first to set up the required packages.
"""

import subprocess
import sys

def install_package(package):
    """Install a package using pip."""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ Successfully installed {package}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install {package}: {e}")
        return False

def main():
    print("🔧 Installing ASR experiment dependencies...")
    print("=" * 50)
    
    packages = [
        "faster-whisper",
        "librosa", 
        "soundfile",
        "numpy"
    ]
    
    success_count = 0
    for package in packages:
        print(f"\n📦 Installing {package}...")
        if install_package(package):
            success_count += 1
    
    print("\n" + "=" * 50)
    print(f"📊 Installation Summary: {success_count}/{len(packages)} packages installed successfully")
    
    if success_count == len(packages):
        print("🎉 All dependencies installed! You can now run the ASR test scripts.")
        print("\nNext steps:")
        print("1. Find a vocals.mp3 file from your karaoke library")
        print("2. Run: python test_faster_whisper.py path/to/vocals.mp3")
        print("3. Run: python test_vocal_start.py path/to/vocals.mp3")
    else:
        print("⚠️  Some packages failed to install. Please check the errors above.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
