import logging
from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models import LlmResponse, LlmRequest
from google.adk.tools import BaseTool, ToolContext

# Configure logging to write to 'log.txt'
logging.basicConfig(
    level=logging.INFO,
    filename='log.txt',
    filemode='a', # 'a' appends to the file, 'w' overwrites it every time
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def log_query_to_model(callback_context: CallbackContext, llm_request: LlmRequest):
    logging.info("--- FULL REQUEST TO %s START ---", callback_context.agent_name)
    
    # Log System Instruction
    if llm_request.config and llm_request.config.system_instruction:
        logging.info("[SYSTEM INSTRUCTION]: %s", llm_request.config.system_instruction)
    
    # Log Conversation History
    for i, content in enumerate(llm_request.contents):
        role = content.role or "unknown"
        for part in content.parts:
            if part.text:
                logging.info("[%s - turn %d]: %s", role, i, part.text)
            elif part.function_call:
                logging.info("[%s - turn %d - FUNCTION CALL]: %s(%s)", 
                             role, i, part.function_call.name, part.function_call.args)
            elif part.function_response:
                # Truncate response if it's too long (common with Base64 images)
                resp_str = str(part.function_response.response)
                if len(resp_str) > 1000:
                    resp_str = resp_str[:1000] + "... [TRUNCATED]"
                logging.info("[%s - turn %d - FUNCTION RESPONSE]: %s -> %s", 
                             role, i, part.function_response.name, resp_str)
            elif part.inline_data:
                logging.info("[%s - turn %d - INLINE DATA]: mime_type=%s, data_len=%d", 
                             role, i, part.inline_data.mime_type, len(part.inline_data.data))
    
    logging.info("--- FULL REQUEST TO %s END ---", callback_context.agent_name)

def log_model_response(callback_context: CallbackContext, llm_response: LlmResponse):
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.text:
                logging.info("[response from %s]: %s", callback_context.agent_name, part.text)
            elif part.function_call:
                logging.info("[function call from %s]: %s", callback_context.agent_name, part.function_call.name)


def before_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext):
    logging.info("[tool call]: %s with args %s", tool.name, args)


def after_tool_callback(tool: BaseTool, args: dict[str, Any], tool_context: ToolContext, tool_response: Any):
    logging.info("[tool response]: %s returned %s", tool.name, tool_response)
