# app/utils/agent.py ** NEW

import openai
import logging

logger = logging.getLogger(__name__)

def ask_openai_agent(api_key, model, system_prompt, context, messages):
    """
    Calls the OpenAI chat API with full context and returns the full reply (not streaming).
    """
    try:
        client = openai.OpenAI(api_key=api_key)
        chat_messages = [
            {"role": "system", "content": f"{system_prompt}\n{context}"}
        ] + messages

        response = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            temperature=0.7,
            stream=False,
        )
        # Get the answer from the first choice
        if response.choices and hasattr(response.choices[0].message, "content"):
            return response.choices[0].message.content
        logger.warning("No choices in OpenAI response")
        return "No answer returned."
    except Exception as e:
        logger.error(f"OpenAI chat API call failed: {e}", exc_info=True)
        return "AI service unavailable. Please try again later."

def ask_openai_agent_stream(api_key, model, system_prompt, context, messages):
    """
    Streams tokens/chunks from OpenAI chat API (for /chat/stream endpoint).
    Yields text chunks.
    """
    try:
        client = openai.OpenAI(api_key=api_key)
        chat_messages = [
            {"role": "system", "content": f"{system_prompt}\n{context}"}
        ] + messages

        response = client.chat.completions.create(
            model=model,
            messages=chat_messages,
            temperature=0.7,
            stream=True,
        )
        for chunk in response:
            if hasattr(chunk, "choices"):
                delta = chunk.choices[0].delta
                if hasattr(delta, "content") and delta.content:
                    yield delta.content
    except Exception as e:
        logger.error(f"OpenAI streaming failed: {e}", exc_info=True)
        yield "AI service unavailable. Please try again later."

"""
--------------------------------------------------------------------
Purpose:
    Contains OpenAI chat helpers for both normal (single-reply) and streaming
    endpoints.

What It Does:
    - ask_openai_agent: Returns one full reply (dashboard, sync chat)
    - ask_openai_agent_stream: Streams chunks for UI (SSE)

Used By:
    - app/routes/agent.py endpoints

Good Practice:
    - All errors handled/logged, no secrets ever returned
    - API key passed per-user (multi-tenant)
    - Can easily add validation, quota, or observability

--------------------------------------------------------------------
"""
