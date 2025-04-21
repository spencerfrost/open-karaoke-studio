# main.py
"""Main application file for Open Karaoke Studio - Entry Point"""

import sys
import traceback

try:
    from openkaraoke.app import App
except ImportError:
    print("Error: Could not import the main App class.", file=sys.stderr)
    traceback.print_exc()
    sys.exit(1)


if __name__ == "__main__":
    try:
        app = App()
        app.run()
    except Exception as e:
        print(f"Critical error in main application: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)