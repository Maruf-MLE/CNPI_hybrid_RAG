"""
List all available Gemini models
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv()

try:
    import google.generativeai as genai
    
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("❌ GEMINI_API_KEY not found")
        sys.exit(1)
    
    genai.configure(api_key=api_key)
    
    print("=" * 70)
    print("Available Gemini Models:")
    print("=" * 70)
    
    for model in genai.list_models():
        print(f"\nModel: {model.name}")
        print(f"  Display Name: {model.display_name}")
        print(f"  Supported Methods: {model.supported_generation_methods}")
        print(f"  Vision Capable: {'vision' in model.name.lower() or 'flash' in model.name.lower() or 'pro' in model.name.lower()}")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
