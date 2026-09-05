
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
import os
from typing import Union
import base64
from pathlib import Path

# Load environment variables from .env file
from dotenv import load_dotenv

load_dotenv()


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
# Shared ChatGoogleGenerativeAI Singleton (LangChain path)
# ===========================================================================

_MODEL_NAME = "gemini-3.5-flash-lite"

def get_llm(
    model: str | None = None,
    temperature: float | None = None,
) -> ChatGoogleGenerativeAI:
    """Return a shared ChatGoogleGenerativeAI instance.

    Calling this multiple times returns a lazily-created singleton so that
    every node in the graph shares the *same* underlying connection instead
    of creating a new ChatGoogleGenerativeAI instance on import.

    Parameters:
        model: optional override; defaults to project-wide model name.
        temperature: optional sampling temperature (0.0-2.0).  When omitted,
            Gemini's default temperature is used (good for deterministic
            tasks like routing / SQL generation).  Pass a higher value
            (e.g. 0.8-1.0) for nodes that should produce varied, natural
            replies such as greetings / small-talk.  Each distinct
            temperature is cached as its own instance so deterministic
            nodes are never affected.
    """
    model = model or _MODEL_NAME
    cache_key = (model, temperature)
    if not hasattr(get_llm, "_instances"):
        get_llm._instances = {}
    if cache_key not in get_llm._instances:
        kwargs = dict(
            model=model,
            google_api_key=os.getenv("GEMINI_API_KEY"),
        )
        if temperature is not None:
            kwargs["temperature"] = temperature
        get_llm._instances[cache_key] = ChatGoogleGenerativeAI(**kwargs)
    return get_llm._instances[cache_key]


# ===========================================================================
# Raw call functions (non-LangChain path)
# ===========================================================================

def call_llm(
    system_message: str,
    user_prompt: str,
    model: str = _MODEL_NAME
) -> str:
    """
    Call the Gemini LLM API directly without template formatting.

    Parameters:
        system_message (str): System prompt to define the AI's behavior
        user_prompt (str): User's question or prompt
        model (str): Model to use (default: gemini-3.5-flash-lite)

    Returns:
        str: LLM's response
    """

    try:
        # Get the LLM instance
        llm = get_llm(model)
        
        # Create messages directly without template formatting
        # to avoid issues with curly braces in system/user prompts
        messages = [
            SystemMessage(content=system_message),
            HumanMessage(content=user_prompt)
        ]
        
        # Invoke the LLM directly with message list
        response = llm.invoke(messages)
        
        return extract_content(response)

    except Exception as e:
        print(f"Error calling LLM: {e}")
        return f"Error: Unable to process request. {str(e)}"


def call_llm_with_reasoning(
    system_message: str,
    user_prompt: str,
    model: str = _MODEL_NAME
) -> tuple:
    """
    Call LLM and return both response and reasoning.
    
    Returns:
        tuple: (response, reasoning)
    """
    # Note: For Gemini, reasoning isn't exposed exactly the same way as Groq/DeepSeek,
    # so we return empty reasoning for compatibility with the existing interface.
    response = call_llm(system_message, user_prompt, model)
    return response, ""


def call_llm_with_history(
    system_message: str,
    user_prompt: str,
    chat_history: list[BaseMessage],
    model: str = _MODEL_NAME,
) -> tuple[str, list[BaseMessage]]:
    """Call Gemini with full conversation history so the AI can see prior turns.

    Unlike ``call_llm`` which sends only a single system+user pair, this
    function prepends the accumulated ``chat_history`` (HumanMessage /
    AIMessage objects) *before* the current user prompt.  The AI now
    "remembers" what was said earlier.

    Parameters:
        system_message: System prompt defining AI behaviour.
        user_prompt:    The *current* user question.
        chat_history:   Prior conversation messages (HumanMessage + AIMessage).
                        Pass ``[]`` for the first turn.
        model:          Model name override.

    Returns:
        (response_text, updated_history)
        - response_text:   plain string answer from the LLM.
        - updated_history: the ``chat_history`` list with the new
                           HumanMessage and AIMessage appended.  Pass this
                           to the next call to keep the conversation going.
    """
    try:
        llm = get_llm(model)

        messages: list[BaseMessage] = [SystemMessage(content=system_message)]
        messages.extend(chat_history)
        messages.append(HumanMessage(content=user_prompt))

        response = llm.invoke(messages)
        answer_text = extract_content(response)

        updated_history = list(chat_history)
        updated_history.append(HumanMessage(content=user_prompt))
        updated_history.append(AIMessage(content=answer_text))

        return answer_text, updated_history

    except Exception as e:
        print(f"Error calling LLM with history: {e}")
        return f"Error: Unable to process request. {str(e)}", chat_history


def extract_text_from_image(
    image_data: Union[bytes, str, Path],
    prompt: str = None,
    model: str = None
) -> str:
    """Extract text from an image using Gemini's vision capabilities.
    
    Parameters:
        image_data: Image data as bytes, base64 string, or file path
        prompt: Custom prompt for text extraction (optional)
        model: Model to use (default: same as _MODEL_NAME - gemini-2.0-flash)
    
    Returns:
        str: Extracted text from the image
    """
    # Lazy imports to avoid circular dependency and module loading issues
    try:
        import google.generativeai as genai
    except ImportError:
        return "Error: google-generativeai package not installed. Run: pip install google-generativeai"
    
    try:
        from PIL import Image
        import io
        
        # Use the same model as the rest of the system
        if model is None:
            model = _MODEL_NAME
        
        print(f"[extract_text_from_image] Starting image text extraction with {model}...")
        
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "Error: GEMINI_API_KEY not found in environment variables"
        
        genai.configure(api_key=api_key)
        
        # Prepare image
        if isinstance(image_data, (str, Path)):
            # If it's a file path
            if os.path.exists(image_data):
                image = Image.open(image_data)
            else:
                # Assume it's base64
                image_bytes = base64.b64decode(image_data)
                image = Image.open(io.BytesIO(image_bytes))
        elif isinstance(image_data, bytes):
            image = Image.open(io.BytesIO(image_data))
        else:
            raise ValueError("image_data must be bytes, base64 string, or file path")
        
        print(f"[extract_text_from_image] Image loaded successfully. Size: {image.size}")
        
        # Default prompt optimized for Bengali/English OCR
        if prompt is None:
            prompt = """Extract ALL text from this image accurately. 

Instructions:
1. Extract both Bengali (বাংলা) and English text
2. Maintain the original structure and formatting
3. Include all visible text including titles, paragraphs, lists, tables, notices, etc.
4. If there's no readable text, return "No text found in image"
5. Return ONLY the extracted text, nothing else

Extracted Text:"""
        
        # Use Gemini model with vision capability
        model_instance = genai.GenerativeModel(model)
        
        print(f"[extract_text_from_image] Calling Gemini API for text extraction...")
        
        # Generate content with image and prompt
        response = model_instance.generate_content([prompt, image])
        
        # Block until response is ready
        response.resolve()
        
        extracted_text = response.text.strip()
        
        print(f"[extract_text_from_image] Successfully extracted {len(extracted_text)} characters")
        if extracted_text:
            print(f"[extract_text_from_image] Preview: {extracted_text[:150]}...")
        
        if not extracted_text or extracted_text.lower() == "no text found in image":
            return "Error: No text could be extracted from the image"
        
        return extracted_text
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"[extract_text_from_image] Error: {str(e)}")
        print(f"[extract_text_from_image] Full traceback:\n{error_details}")
        return f"Error: Unable to extract text from image. {str(e)}"


# =============================================================================
# Example Usage
# =============================================================================

if __name__ == "__main__":
    # Test LLM connection
    system_prompt = "You are a helpful assistant for college information queries."
    user_question = "What is the principal's full name?"

    result = call_llm(system_prompt, user_question)
    print("LLM Response:")
    print(result)