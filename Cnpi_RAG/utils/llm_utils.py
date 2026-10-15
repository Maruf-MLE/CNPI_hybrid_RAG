
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
import os
from typing import Union
import base64
from pathlib import Path
import threading

from dotenv import load_dotenv
load_dotenv()

from Cnpi_RAG.utils.key_manager import get_key_manager


# ===========================================================================
# Content extraction helper (Gemini compatibility)
# ===========================================================================

def extract_content(response: Union[AIMessage, str, list]) -> str:
    """Safely extract text from an LLM response.

    Gemini sometimes returns `response.content` as a list of content blocks
    instead of a plain string. This helper normalises both forms into a
    single string so downstream `.strip()` / `.lower()` calls never crash.
    """
    if isinstance(response, AIMessage):
        content = response.content
    else:
        content = response

    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", ""))
            else:
                parts.append(str(block))
        return "".join(parts)

    if isinstance(content, str):
        return content

    return str(content)


# ===========================================================================
# Model name
# ===========================================================================

_MODEL_NAME = "gemini-3.5-flash-lite"


# ===========================================================================
# Rate limit detector
# ===========================================================================

def _is_rate_limit_error(error: Exception) -> bool:
    """429 / Resource Exhausted error কিনা check করো।"""
    err_str = str(error).lower()
    return (
        "429" in err_str
        or "resource_exhausted" in err_str
        or "resource exhausted" in err_str
        or "quota" in err_str
        or "rate limit" in err_str
        or "ratelimit" in err_str
        or "too many requests" in err_str
    )


# ===========================================================================
# LangChain instance factory (per-key, no shared singleton)
# ===========================================================================

def _make_llm(api_key: str, model: str, temperature: float | None = None) -> ChatGoogleGenerativeAI:
    """
    দেওয়া api_key দিয়ে একটা নতুন ChatGoogleGenerativeAI instance বানাও।

    Cache করা হয় না — rotation loop এ প্রতিটা key এর জন্য আলাদা instance
    তৈরি হয় যাতে ভুল key এর cached instance কখনো ব্যবহার না হয়।
    LangChain object তৈরি করা সস্তা (~0ms), তাই এতে কোনো performance সমস্যা নেই।
    """
    kwargs = dict(model=model, google_api_key=api_key)
    if temperature is not None:
        kwargs["temperature"] = temperature
    return ChatGoogleGenerativeAI(**kwargs)


# ===========================================================================
# get_llm() — backward-compat public API (nodes সরাসরি এটা call করে)
# ===========================================================================
# NOTE: এই ফাংশনটা শুধু তখনই call হয় যখন কোনো node সরাসরি get_llm() নেয়
# এবং নিজেই llm.invoke() করে। সেক্ষেত্রে rotation হয় না।
# Rotation চাইলে call_llm() / call_llm_with_history() ব্যবহার করো।

_get_llm_cache: dict = {}
_get_llm_lock = threading.Lock()

def get_llm(
    model: str | None = None,
    temperature: float | None = None,
) -> ChatGoogleGenerativeAI:
    """Return a ChatGoogleGenerativeAI instance using the first available key.

    Node গুলো সরাসরি এই ফাংশন call করে তারপর llm.invoke() করে।
    এখানে সবসময় প্রথম available key ব্যবহার হয় — index advance হয় না।
    Key rotation শুধু 429 হলে call_llm() / call_llm_with_history() এর ভেতরেই হয়।

    NOTE: এই ফাংশন দিয়ে invoke করলে 429 হলে auto-switch হবে না।
          Auto-switch চাইলে call_llm() ব্যবহার করো।
    """
    model = model or _MODEL_NAME

    km = get_key_manager()
    # সবসময় প্রথম available key নাও — index advance করো না
    api_key = None
    for key, label in km._keys:
        if not km._is_exhausted(key):
            api_key = key
            break
    if api_key is None:
        # সব exhausted — fallback
        api_key = km._keys[0][0] if km._keys else (
            os.getenv("GEMINI_API_KEY_1") or os.getenv("GEMINI_API_KEY", "")
        )

    cache_key = (model, temperature, api_key)
    with _get_llm_lock:
        if cache_key not in _get_llm_cache:
            _get_llm_cache[cache_key] = _make_llm(api_key, model, temperature)
        return _get_llm_cache[cache_key]


# ===========================================================================
# call_llm() — rotation + retry (মূল entry point)
# ===========================================================================

def call_llm(
    system_message: str,
    user_prompt: str,
    model: str = _MODEL_NAME
) -> str:
    """
    Gemini LLM call with automatic key rotation.

    কীভাবে কাজ করে:
      1. key_manager থেকে সব available key এর ordered list নাও
      2. প্রতিটা key দিয়ে একটা নতুন LangChain instance বানাও ও invoke করো
      3. 429 error → সেই key mark_exhausted() করো → পরের key তে যাও
      4. অন্য error → সাথে সাথে error return করো (key বদলে লাভ নেই)
      5. সব key শেষ → informative error message return করো

    Returns:
        str: LLM response অথবা "Error: ..." string
    """
    km = get_key_manager()

    # key manager এর ভেতর থেকে পুরো ordered list নাও
    # _is_exhausted check করে available গুলো আগে, exhausted গুলো পরে সাজাই
    available_keys = [
        (key, label)
        for key, label in km._keys
        if not km._is_exhausted(key)
    ]

    if not available_keys:
        min_wait = min((km.get_hours_remaining(k) for k, _ in km._keys), default=24.0)
        return (
            f"Error: সব Gemini API key exhausted। "
            f"আনুমানিক {min_wait:.1f} ঘন্টা পর আবার চেষ্টা করুন।"
        )

    messages = [
        SystemMessage(content=system_message),
        HumanMessage(content=user_prompt),
    ]

    for api_key, label in available_keys:
        try:
            llm = _make_llm(api_key, model)   # সবসময় fresh instance
            response = llm.invoke(messages)
            return extract_content(response)

        except Exception as e:
            if _is_rate_limit_error(e):
                km.mark_exhausted(api_key, label, str(e))
                print(f"[LLM] {label} rate-limited → switching to next key...")
                continue  # পরের key তে যাও
            # অন্য error — key বদলে লাভ নেই
            print(f"[LLM] Non-rate-limit error ({label}): {e}")
            return f"Error: Unable to process request. {str(e)}"

    # সব available key ব্যর্থ হলে
    return "Error: সব Gemini API key exhausted। কিছুক্ষণ পর আবার চেষ্টা করুন।"


# ===========================================================================
# call_llm_with_reasoning() — wrapper
# ===========================================================================

def call_llm_with_reasoning(
    system_message: str,
    user_prompt: str,
    model: str = _MODEL_NAME
) -> tuple:
    """Call LLM and return (response, reasoning). Gemini reasoning not exposed."""
    response = call_llm(system_message, user_prompt, model)
    return response, ""


# ===========================================================================
# call_llm_with_history() — conversation history + rotation
# ===========================================================================

def call_llm_with_history(
    system_message: str,
    user_prompt: str,
    chat_history: list[BaseMessage],
    model: str = _MODEL_NAME,
) -> tuple[str, list[BaseMessage]]:
    """Call Gemini with full conversation history + key rotation.

    Parameters:
        system_message: System prompt.
        user_prompt:    Current user question.
        chat_history:   Prior messages. Pass [] for first turn.
        model:          Model name override.

    Returns:
        (response_text, updated_history)
    """
    km = get_key_manager()

    available_keys = [
        (key, label)
        for key, label in km._keys
        if not km._is_exhausted(key)
    ]

    if not available_keys:
        min_wait = min((km.get_hours_remaining(k) for k, _ in km._keys), default=24.0)
        err = f"Error: সব Gemini API key exhausted। {min_wait:.1f}h পর আবার চেষ্টা করুন।"
        return err, chat_history

    messages: list[BaseMessage] = [SystemMessage(content=system_message)]
    messages.extend(chat_history)
    messages.append(HumanMessage(content=user_prompt))

    for api_key, label in available_keys:
        try:
            llm = _make_llm(api_key, model)
            response = llm.invoke(messages)
            answer_text = extract_content(response)

            updated_history = list(chat_history)
            updated_history.append(HumanMessage(content=user_prompt))
            updated_history.append(AIMessage(content=answer_text))
            return answer_text, updated_history

        except Exception as e:
            if _is_rate_limit_error(e):
                km.mark_exhausted(api_key, label, str(e))
                print(f"[LLM] {label} rate-limited → switching key...")
                continue
            print(f"[LLM] Error with history ({label}): {e}")
            return f"Error: Unable to process request. {str(e)}", chat_history

    return "Error: সব Gemini API key exhausted। কিছুক্ষণ পর আবার চেষ্টা করুন।", chat_history


# ===========================================================================
# extract_text_from_image() — vision + rotation
# ===========================================================================

def extract_text_from_image(
    image_data: Union[bytes, str, Path],
    prompt: str = None,
    model: str = None
) -> str:
    """Extract text from an image using Gemini vision + key rotation."""
    try:
        import google.generativeai as genai
    except ImportError:
        return "Error: google-generativeai not installed. Run: pip install google-generativeai"

    try:
        from PIL import Image
        import io

        if model is None:
            model = _MODEL_NAME

        print(f"[ImageOCR] Starting with model={model}")

        # Image একবারই prepare করো (loop এর বাইরে)
        if isinstance(image_data, (str, Path)):
            if os.path.exists(str(image_data)):
                image = Image.open(image_data)
            else:
                image = Image.open(io.BytesIO(base64.b64decode(image_data)))
        elif isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
        else:
            raise ValueError("image_data must be bytes, base64 string, or file path")

        print(f"[ImageOCR] Image loaded. Size: {image.size}")

        if prompt is None:
            prompt = """Extract ALL text from this image accurately.

Instructions:
1. Extract both Bengali (বাংলা) and English text
2. Maintain the original structure and formatting
3. Include all visible text: titles, paragraphs, lists, tables, notices
4. If no readable text, return "No text found in image"
5. Return ONLY the extracted text, nothing else

Extracted Text:"""

        km = get_key_manager()
        available_keys = [
            (key, label)
            for key, label in km._keys
            if not km._is_exhausted(key)
        ]

        if not available_keys:
            min_wait = min((km.get_hours_remaining(k) for k, _ in km._keys), default=24.0)
            return f"Error: সব Gemini API key exhausted। {min_wait:.1f}h পর আবার চেষ্টা করুন।"

        for api_key, label in available_keys:
            try:
                # google.generativeai global configure — প্রতিটা key এর জন্য
                genai.configure(api_key=api_key)
                model_instance = genai.GenerativeModel(model)

                print(f"[ImageOCR] Calling Gemini with {label}...")
                response = model_instance.generate_content([prompt, image])
                response.resolve()
                extracted_text = response.text.strip()

                print(f"[ImageOCR] Extracted {len(extracted_text)} chars")
                if not extracted_text or extracted_text.lower() == "no text found in image":
                    return "Error: No text could be extracted from the image"

                return extracted_text

            except Exception as e:
                if _is_rate_limit_error(e):
                    km.mark_exhausted(api_key, label, str(e))
                    print(f"[ImageOCR] {label} rate-limited → switching key...")
                    continue
                import traceback
                print(f"[ImageOCR] Error with {label}: {e}\n{traceback.format_exc()}")
                return f"Error: Unable to extract text from image. {str(e)}"

        return "Error: সব Gemini API key exhausted। কিছুক্ষণ পর আবার চেষ্টা করুন।"

    except Exception as e:
        import traceback
        print(f"[ImageOCR] Fatal: {e}\n{traceback.format_exc()}")
        return f"Error: Unable to extract text from image. {str(e)}"


# =============================================================================
# CLI test
# =============================================================================

if __name__ == "__main__":
    km = get_key_manager()
    print("=== Key Status ===")
    for s in km.status():
        print(f"  {s['label']}: {s['status']}"
              + (f" ({s['hours_remaining']}h remaining)" if s['hours_remaining'] else ""))

    print("\n=== LLM Test ===")
    result = call_llm(
        "You are a helpful assistant.",
        "Say hello in Bengali."
    )
    print("Response:", result)
