"""
Test image text extraction with Gemini Vision API
"""
import os
import sys
from pathlib import Path

# Add Cnpi_RAG to path
sys.path.insert(0, str(Path(__file__).parent / "Cnpi_RAG"))

from dotenv import load_dotenv
load_dotenv()

def test_gemini_vision():
    """Test Gemini vision API with a simple text image"""
    try:
        import google.generativeai as genai
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        print("=" * 60)
        print("Testing Gemini Vision API for Text Extraction")
        print("=" * 60)
        
        # Check API key
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ ERROR: GEMINI_API_KEY not found in .env file")
            return False
        
        print(f"✅ GEMINI_API_KEY found: {api_key[:10]}...")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Create a simple test image with text
        print("\n📝 Creating test image with text...")
        img = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add text to image
        text = """CNPI RAG Test Document
        
This is a test document for OCR.
এটি একটি টেস্ট ডকুমেন্ট।

Important Notice:
Classes will resume on Monday.
ক্লাস সোমবার থেকে শুরু হবে।"""
        
        # Use default font
        try:
            # Try to use a better font if available
            font = ImageFont.truetype("arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        draw.text((50, 50), text, fill='black', font=font)
        
        print("✅ Test image created")
        
        # Save for inspection
        test_image_path = "test_image.png"
        img.save(test_image_path)
        print(f"✅ Test image saved to: {test_image_path}")
        
        # Test with different models
        models_to_test = [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-pro-vision",
        ]
        
        for model_name in models_to_test:
            print(f"\n{'=' * 60}")
            print(f"Testing model: {model_name}")
            print(f"{'=' * 60}")
            
            try:
                model = genai.GenerativeModel(model_name)
                
                prompt = """Extract ALL text from this image. 

Instructions:
1. Extract both Bengali (বাংলা) and English text
2. Maintain the original structure and formatting
3. Include all visible text including titles, paragraphs, lists, etc.
4. If there's no text, return "No text found in image"
5. Return ONLY the extracted text, nothing else

Extracted Text:"""
                
                print(f"🔄 Calling {model_name} API...")
                response = model.generate_content([prompt, img])
                response.resolve()
                
                extracted_text = response.text.strip()
                
                print(f"✅ SUCCESS! Extracted {len(extracted_text)} characters")
                print(f"\n📄 Extracted Text:")
                print("-" * 60)
                print(extracted_text)
                print("-" * 60)
                
                return True
                
            except Exception as e:
                print(f"❌ ERROR with {model_name}: {str(e)}")
                import traceback
                print(traceback.format_exc())
                continue
        
        print("\n❌ All models failed")
        return False
        
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        print("\n💡 Installing required packages...")
        os.system("pip install pillow google-generativeai")
        return False
    except Exception as e:
        print(f"❌ Unexpected Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False


def test_from_llm_utils():
    """Test using the actual llm_utils function"""
    print("\n" + "=" * 60)
    print("Testing llm_utils.extract_text_from_image()")
    print("=" * 60)
    
    try:
        from utils.llm_utils import extract_text_from_image
        from PIL import Image, ImageDraw, ImageFont
        import io
        
        # Create test image
        img = Image.new('RGB', (800, 400), color='white')
        draw = ImageDraw.Draw(img)
        
        text = """CNPI Notice
Classes resume Monday
ক্লাস সোমবার থেকে"""
        
        try:
            font = ImageFont.truetype("arial.ttf", 32)
        except:
            font = ImageFont.load_default()
        
        draw.text((100, 100), text, fill='black', font=font)
        
        # Convert to bytes
        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='PNG')
        image_bytes = img_byte_arr.getvalue()
        
        print(f"📝 Created test image ({len(image_bytes)} bytes)")
        print(f"🔄 Calling extract_text_from_image()...")
        
        result = extract_text_from_image(image_bytes)
        
        print(f"\n📄 Result:")
        print("-" * 60)
        print(result)
        print("-" * 60)
        
        if result.startswith("Error:"):
            print("\n❌ Function returned error")
            return False
        else:
            print(f"\n✅ SUCCESS! Extracted {len(result)} characters")
            return True
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(traceback.format_exc())
        return False


if __name__ == "__main__":
    print("\n🚀 Starting Image Text Extraction Tests\n")
    
    # Test 1: Direct Gemini API
    test1_success = test_gemini_vision()
    
    # Test 2: Using llm_utils function
    test2_success = test_from_llm_utils()
    
    print("\n" + "=" * 60)
    print("Test Results:")
    print("=" * 60)
    print(f"Direct Gemini API Test: {'✅ PASSED' if test1_success else '❌ FAILED'}")
    print(f"llm_utils Function Test: {'✅ PASSED' if test2_success else '❌ FAILED'}")
    print("=" * 60)
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed! Image text extraction is working.")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
