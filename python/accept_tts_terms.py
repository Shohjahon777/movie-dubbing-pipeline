#!/usr/bin/env python3
"""
Helper script to accept Coqui XTTS v2 terms of service on HuggingFace Hub
Run this once before starting the app to accept the terms.
"""

import os
import sys
from huggingface_hub import login, hf_hub_download
from huggingface_hub.utils import HfHubHTTPError

def accept_tts_terms():
    """Accept Coqui XTTS v2 terms of service"""
    
    print("=" * 60)
    print("Coqui XTTS v2 Terms of Service Acceptance")
    print("=" * 60)
    print()
    print("This script will help you accept the terms for:")
    print("https://huggingface.co/coqui/XTTS-v2")
    print()
    
    # Check if token is set
    token = os.getenv("HUGGING_FACE_HUB_TOKEN")
    
    if not token:
        print("HUGGING_FACE_HUB_TOKEN not set. Please provide your token.")
        print()
        print("Option 1: Set environment variable:")
        print("  export HUGGING_FACE_HUB_TOKEN=your_token_here")
        print()
        print("Option 2: Login interactively:")
        print("  huggingface-cli login")
        print()
        
        try:
            token = input("Or enter your HuggingFace token now: ").strip()
            if token:
                os.environ["HUGGING_FACE_HUB_TOKEN"] = token
            else:
                print("\nNo token provided. Please visit the URL below to accept terms manually:")
                print("https://huggingface.co/coqui/XTTS-v2")
                print("\nThen run this script again with your token.")
                return False
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled.")
            return False
    
    # Login with token
    try:
        if token:
            login(token=token)
        else:
            login()
        print("✓ Logged in to HuggingFace Hub")
    except Exception as e:
        print(f"Error logging in: {e}")
        print("\nPlease try:")
        print("  1. Get your token from: https://huggingface.co/settings/tokens")
        print("  2. Run: huggingface-cli login")
        return False
    
    # Try to download a small file from the model repo to trigger terms acceptance
    print("\nAttempting to access XTTS-v2 model (this will prompt for terms acceptance)...")
    try:
        # Try to access the model repository
        # This will trigger the terms acceptance if not already accepted
        hf_hub_download(
            repo_id="coqui/XTTS-v2",
            filename="config.json",
            local_dir="./models/coqui",
            force_download=False
        )
        print("✓ Terms accepted! Model repository accessed successfully.")
        return True
    except HfHubHTTPError as e:
        if "403" in str(e) or "terms" in str(e).lower():
            print("\n" + "=" * 60)
            print("TERMS ACCEPTANCE REQUIRED")
            print("=" * 60)
            print("\nPlease manually accept the terms:")
            print("1. Visit: https://huggingface.co/coqui/XTTS-v2")
            print("2. Click 'Agree and access repository'")
            print("3. Accept the terms")
            print("\nThen run this script again.")
            return False
        else:
            print(f"Error: {e}")
            return False
    except Exception as e:
        print(f"Error accessing model: {e}")
        return False


if __name__ == "__main__":
    success = accept_tts_terms()
    sys.exit(0 if success else 1)

