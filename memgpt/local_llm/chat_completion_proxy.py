"""Key idea: create drop-in replacement for agent's ChatCompletion call that runs on an OpenLLM backend"""

import os
import requests
import json

from .webui.api import get_webui_completion
from .llm_chat_completion_wrappers import airoboros
from .utils import DotDict

HOST = os.getenv("OPENAI_API_BASE")
HOST_TYPE = os.getenv("BACKEND_TYPE")  # default None == ChatCompletion
DEBUG = True


async def get_chat_completion(
    model,  # no model, since the model is fixed to whatever you set in your own backend
    messages,
    functions,
    function_call="auto",
):
    if function_call != "auto":
        raise ValueError(f"function_call == {function_call} not supported (auto only)")

    if model == "airoboros_v2.1":
        llm_wrapper = airoboros.Airoboros21Wrapper()
    else:
        # Warn the user that we're using the fallback
        print(
            f"Warning: could not find an LLM wrapper for {model}, using the airoboros wrapper"
        )
        llm_wrapper = airoboros.Airoboros21Wrapper()

    # First step: turn the message sequence into a prompt that the model expects
    prompt = llm_wrapper.chat_completion_to_prompt(messages, functions)
    if DEBUG:
        print(prompt)

    try:
        if HOST_TYPE == "webui":
            result = get_webui_completion(prompt)
        else:
            print(f"Warning: BACKEND_TYPE was not set, defaulting to webui")
            result = get_webui_completion(prompt)
    except requests.exceptions.ConnectionError as e:
        raise ValueError(f"Was unable to connect to host {HOST}")

    chat_completion_result = llm_wrapper.output_to_chat_completion_response(result)
    if DEBUG:
        print(json.dumps(chat_completion_result, indent=2))

    # unpack with response.choices[0].message.content
    response = DotDict(
        {
            "model": None,
            "choices": [
                DotDict(
                    {
                        "message": DotDict(chat_completion_result),
                        "finish_reason": "stop",  # TODO vary based on backend response
                    }
                )
            ],
            "usage": DotDict(
                {
                    # TODO fix, actually use real info
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                }
            ),
        }
    )
    return response