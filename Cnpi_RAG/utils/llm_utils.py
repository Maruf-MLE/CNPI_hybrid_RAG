
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, BaseMessage
import os
from typing import Union

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

def get_llm(model: str | None = None) -> ChatGoogleGenerativeAI:
    """Return a shared ChatGoogleGenerativeAI instance.

    Calling this multiple times returns a lazily-created singleton so that
    every node in the graph shares the *same* underlying connection instead
    of creating a new ChatGoogleGenerativeAI instance on import.

    Parameters:
        model: optional override; defaults to project-wide model name.
    """
    model = model or _MODEL_NAME
    if not hasattr(get_llm, "_instances"):
        get_llm._instances = {}
    if model not in get_llm._instances:
        get_llm._instances[model] = ChatGoogleGenerativeAI(
            model=model,
            google_api_key=os.getenv("GEMINI_API_KEY"),
            # We don't set streaming=True as it might conflict with some LangChain LCEL setups, 
            # unless specifically needed by the graph implementation.
        )
    return get_llm._instances[model]


# ===========================================================================
# Raw call functions (non-LangChain path)
# ===========================================================================

def call_llm(
    system_message: str,
    user_prompt: str,
    model: str = _MODEL_NAME
) -> str:
    """
    Call the Gemini LLM API using ChatPromptTemplate and chain invocation.

    Parameters:
        system_message (str): System prompt to define the AI's behavior
        user_prompt (str): User's question or prompt
        model (str): Model to use (default: gemini-3.5-flash-lite)

    Returns:
        str: LLM's response
    """

    try:
        # Create a ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_message),
            ("user", "{user_input}")
        ])
        
        # Get the LLM instance
        llm = get_llm(model)
        
        # Create and invoke chain using the prompt and LLM
        chain = prompt | llm
        response = chain.invoke({"user_input": user_prompt})
        
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