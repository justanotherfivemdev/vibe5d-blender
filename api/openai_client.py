import json
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, Any, Callable, Optional, List

from ..utils.logger import logger


class OpenAIStreamingResponse:
    """Mirrors StreamingResponse from websocket_client for compatibility."""

    def __init__(self):
        self.output_content = ""
        self.final_code = ""
        self.status_messages = []
        self.progress = 0
        self.stage = ""
        self.success = False
        self.error = None
        self.message_id = None
        self.request_id = None
        self.usage_info = {}
        self.is_complete = False
        self.tool_calls = []
        self.assistant_message_added = False

        self.current_tool_call = None
        self.tool_call_started = False
        self.tool_call_completed = False
        self.tool_events = []
        self.web_search_events = []
        self.current_tool_name = None
        self.current_tool_status = None
        self.current_tool_success = False
        self.current_search_query = None
        self.current_search_status = None
        self.current_search_success = False
        self.current_search_result_count = 0
        self.current_tool_call_id = None
        self.current_tool_arguments = None
        self.current_tool_result = None
        self.error_code = None
        self.error_retryable = False
        self.error_suggestions = []


# Default system prompt for Blender assistant when using direct OpenAI mode
BLENDER_SYSTEM_PROMPT = """You are Vibe5D, an expert open-source AI assistant for Blender 3D. You help users with:
- Creating, modifying, and managing 3D objects, materials, and scenes
- Writing and explaining Blender Python (bpy) scripts
- Answering questions about Blender workflows, rendering, and techniques
- Providing guidance on modeling, texturing, lighting, and animation

When asked to perform actions in Blender, provide Python code using the bpy module.
Wrap executable code in ```python code blocks.

Keep responses concise and focused on the user's specific question or task.
"""


class OpenAIClient:
    """
    OpenAI-compatible HTTP streaming client.

    Supports any OpenAI-compatible API endpoint including:
    - OpenAI (https://api.openai.com/v1)
    - Anthropic via OpenAI-compatible proxy
    - Google Gemini via OpenAI-compatible proxy
    - Ollama (http://localhost:11434/v1)
    - LM Studio (http://localhost:1234/v1)
    - LocalAI (http://localhost:8080/v1)
    - vLLM, text-generation-webui, etc.
    """

    DEFAULT_OPENAI_BASE_URL = "https://api.openai.com/v1"
    DEFAULT_LOCAL_BASE_URL = "http://localhost:11434/v1"
    DEFAULT_MODEL = "gpt-4o-mini"
    DEFAULT_LOCAL_MODEL = "llama3"

    # OpenAI-format tool definitions so models know they can call execute/query
    TOOL_DEFINITIONS = [
        {
            "type": "function",
            "function": {
                "name": "execute_code",
                "description": (
                    "Execute Python code inside Blender to create or modify 3D objects, "
                    "materials, animations, and scenes. The code runs in a restricted "
                    "environment with access to bpy, bmesh, and mathutils."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Python code to execute in Blender (using bpy module)",
                        }
                    },
                    "required": ["code"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scene_query",
                "description": (
                    "Query the current Blender scene using a SQL-like syntax. "
                    "Supports tables: objects, materials, lights, cameras, collections, "
                    "scene, world, meshes, images, modifiers, constraints, custom_properties, "
                    "texts, curves. Example: SELECT name, location FROM objects WHERE type = 'MESH'"
                ),
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL-like query for scene data",
                        },
                        "format": {
                            "type": "string",
                            "enum": ["csv", "json", "table"],
                            "description": "Output format (default: csv)",
                        },
                    },
                    "required": ["sql"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "scene_context",
                "description": (
                    "Get current Blender scene context including selected objects, "
                    "active object, frame range, render engine, and viewport info."
                ),
                "parameters": {
                    "type": "object",
                    "properties": {},
                },
            },
        },
    ]

    # Context size limits to prevent freezing
    MAX_CONTEXT_CHARS = 100000
    MAX_SINGLE_MESSAGE_CHARS = 50000

    def __init__(self):
        self.response = None
        self.on_progress_callback = None
        self.on_complete_callback = None
        self.on_error_callback = None
        self._is_generating = False
        self._cancel_requested = False
        self._generation_thread = None
        self._connection_timeout = 30
        self._read_timeout = 120

    def is_ready_for_new_request(self) -> bool:
        return not self._is_generating

    def can_send_message(self) -> bool:
        return not self._is_generating

    def cancel_generation(self):
        """Request cancellation of the current generation."""
        self._cancel_requested = True
        logger.info("OpenAI generation cancellation requested")

    def send_prompt_request(
            self,
            request_data: Dict[str, Any],
            on_progress: Optional[Callable] = None,
            on_complete: Optional[Callable] = None,
            on_error: Optional[Callable] = None
    ) -> bool:
        """
        Send a chat completion request using the OpenAI-compatible API.

        request_data should contain:
        - api_key: str (optional for local LLMs)
        - base_url: str
        - model: str
        - messages: list of {role, content}
        - instructions: list of str (system prompts)
        - schema_summary: str (scene context)
        """
        try:
            if self._is_generating:
                logger.warning("Already generating a response")
                return False

            self._is_generating = True
            self._cancel_requested = False

            self.on_progress_callback = on_progress
            self.on_complete_callback = on_complete
            self.on_error_callback = on_error

            self.response = OpenAIStreamingResponse()
            self.response.request_id = f"openai_{int(time.time() * 1000)}"

            thread = threading.Thread(
                target=self._generate_streaming,
                args=(request_data,),
                daemon=True
            )
            thread.start()
            self._generation_thread = thread

            return True

        except Exception as e:
            self._is_generating = False
            logger.error(f"Failed to start OpenAI generation: {str(e)}")
            if self.on_error_callback:
                self.on_error_callback(f"Failed to start generation: {str(e)}")
            return False

    def _build_openai_messages(self, request_data: Dict[str, Any]) -> List[Dict[str, str]]:
        """Build OpenAI-format messages from request data."""
        messages = []

        # System prompt with schema context
        system_parts = [BLENDER_SYSTEM_PROMPT]

        # Add custom instructions
        instructions = request_data.get("instructions", [])
        for inst in instructions:
            if inst and inst.strip():
                system_parts.append(f"\nCustom Instructions:\n{inst.strip()}")

        # Add schema summary (truncated if needed)
        schema_summary = request_data.get("schema_summary", "")
        if schema_summary:
            if len(schema_summary) > self.MAX_SINGLE_MESSAGE_CHARS:
                schema_summary = schema_summary[:self.MAX_SINGLE_MESSAGE_CHARS] + \
                    "\n\n[Scene context truncated due to size. Use queries to explore specific objects and data.]"
                logger.warning(
                    f"Schema summary truncated from {len(request_data.get('schema_summary', ''))} "
                    f"to {self.MAX_SINGLE_MESSAGE_CHARS} chars"
                )
            system_parts.append(f"\nCurrent Scene Context:\n{schema_summary}")

        system_content = "\n".join(system_parts)

        # Truncate overall system message if too large
        if len(system_content) > self.MAX_CONTEXT_CHARS:
            system_content = system_content[:self.MAX_CONTEXT_CHARS] + "\n[Context truncated]"

        messages.append({
            "role": "system",
            "content": system_content
        })

        # Add conversation history
        history_messages = request_data.get("messages", [])
        total_chars = len(system_content)

        for msg in history_messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Skip tool messages - OpenAI handles these differently
            if role == "tool":
                continue

            # Map any custom roles to standard OpenAI roles
            if role not in ("user", "assistant", "system"):
                role = "user"

            # Pass through multimodal content arrays (text + image_url) as-is
            if isinstance(content, list):
                messages.append({"role": role, "content": content})
                continue

            # Truncate individual messages if too large
            if len(content) > self.MAX_SINGLE_MESSAGE_CHARS:
                content = content[:self.MAX_SINGLE_MESSAGE_CHARS] + "\n[Message truncated]"

            # Check total context size
            total_chars += len(content)
            if total_chars > self.MAX_CONTEXT_CHARS:
                logger.warning(f"Context size limit reached ({total_chars} chars), truncating history")
                break

            messages.append({
                "role": role,
                "content": content
            })

        return messages

    def _generate_streaming(self, request_data: Dict[str, Any]):
        """Run streaming generation in a background thread."""
        try:
            api_key = request_data.get("api_key", "")
            base_url = request_data.get("base_url", self.DEFAULT_OPENAI_BASE_URL).rstrip("/")
            model = request_data.get("model", self.DEFAULT_MODEL)

            messages = self._build_openai_messages(request_data)

            # Build the API request
            url = f"{base_url}/chat/completions"

            payload = {
                "model": model,
                "messages": messages,
                "stream": True,
                "temperature": 0.7,
            }

            # Include tool definitions so the model knows it can execute code
            # and query the scene.  Some local models may not support tools —
            # if the endpoint rejects the request we fall back without them.
            tools = request_data.get("tools")
            if tools:
                payload["tools"] = tools

            headers = {
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "User-Agent": "Vibe5D-Blender-Addon"
            }

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            json_data = json.dumps(payload).encode("utf-8")

            req = urllib.request.Request(url, data=json_data, headers=headers, method="POST")

            # Update status
            self.response.stage = "connecting"
            self.response.progress = 10
            self.response.status_messages.append("Connecting to LLM...")
            self._notify_progress()

            try:
                resp = urllib.request.urlopen(req, timeout=self._connection_timeout)
            except urllib.error.HTTPError as e:
                error_body = ""
                try:
                    error_body = e.read().decode("utf-8", errors="replace")
                    error_json = json.loads(error_body)
                    error_msg = error_json.get("error", {}).get("message", error_body)
                except Exception:
                    error_msg = error_body or f"HTTP {e.code}: {e.reason}"

                if e.code == 401:
                    error_msg = "Authentication failed. Please check your API key."
                elif e.code == 429:
                    error_msg = "Rate limit exceeded. Please wait before making another request."
                elif e.code == 404:
                    error_msg = f"Model '{model}' not found or endpoint not available at {base_url}."
                elif e.code >= 500:
                    error_msg = f"Server error ({e.code}). The LLM service may be temporarily unavailable."

                self._handle_generation_error(error_msg)
                return
            except urllib.error.URLError as e:
                self._handle_generation_error(
                    f"Connection failed: {e.reason}. Check that the LLM service is running at {base_url}"
                )
                return
            except Exception as e:
                self._handle_generation_error(f"Connection error: {str(e)}")
                return

            self.response.stage = "generating"
            self.response.progress = 30
            self.response.status_messages.append("Generating response...")
            self._notify_progress()

            # Process SSE stream
            self._process_sse_stream(resp)

        except Exception as e:
            self._handle_generation_error(f"Generation failed: {str(e)}")

    def _process_sse_stream(self, resp):
        """Process Server-Sent Events stream from OpenAI-compatible API."""
        buffer = ""
        try:
            while True:
                if self._cancel_requested:
                    logger.info("Generation cancelled by user")
                    self.response.stage = "cancelled"
                    break

                chunk = resp.read(1024)
                if not chunk:
                    break

                buffer += chunk.decode("utf-8", errors="replace")

                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()

                    if not line:
                        continue

                    if line.startswith("data: "):
                        data_str = line[6:]

                        if data_str == "[DONE]":
                            self.response.is_complete = True
                            self.response.success = True
                            break

                        try:
                            data = json.loads(data_str)
                            self._handle_stream_chunk(data)
                        except json.JSONDecodeError:
                            logger.debug(f"Skipping non-JSON SSE line: {data_str[:100]}")

                if self.response.is_complete:
                    break

        except Exception as e:
            if not self._cancel_requested:
                logger.error(f"Error processing SSE stream: {str(e)}")
                self._handle_generation_error(f"Stream processing error: {str(e)}")
                return

        finally:
            try:
                resp.close()
            except Exception:
                pass

        # Finalize
        self.response.is_complete = True
        self.response.success = not bool(self.response.error)

        if not self.response.final_code and self.response.output_content:
            self.response.final_code = self.response.output_content

        self.response.message_id = f"msg_{int(time.time() * 1000)}"

        self._is_generating = False

        if self.on_complete_callback:
            self.on_complete_callback(self.response)

    def _handle_stream_chunk(self, data: Dict[str, Any]):
        """Process a single SSE chunk from OpenAI-compatible API."""
        choices = data.get("choices", [])
        if not choices:
            return

        choice = choices[0]
        delta = choice.get("delta", {})

        # Handle content chunks
        content = delta.get("content", "")
        if content:
            self.response.output_content += content
            self.response.progress = min(90, self.response.progress + 1)
            self._notify_progress()

        # Handle tool_calls chunks (streamed incrementally by OpenAI-compatible APIs)
        tool_calls = delta.get("tool_calls")
        if tool_calls:
            for tc in tool_calls:
                idx = tc.get("index", 0)

                # Grow the list to accommodate the index
                while len(self.response.tool_calls) <= idx:
                    self.response.tool_calls.append({
                        "id": "",
                        "type": "function",
                        "function": {"name": "", "arguments": ""},
                    })

                entry = self.response.tool_calls[idx]

                # First chunk carries the id and function name
                if tc.get("id"):
                    entry["id"] = tc["id"]
                func = tc.get("function", {})
                if func.get("name"):
                    entry["function"]["name"] = func["name"]
                if func.get("arguments"):
                    entry["function"]["arguments"] += func["arguments"]

            self.response.tool_call_started = True
            self.response.current_tool_call_id = self.response.tool_calls[-1].get("id", "")
            self.response.current_tool_name = (
                self.response.tool_calls[-1].get("function", {}).get("name", "")
            )
            self._notify_progress()

        # Handle finish reason
        finish_reason = choice.get("finish_reason")
        if finish_reason:
            self.response.is_complete = True
            if finish_reason == "stop":
                self.response.success = True
            elif finish_reason == "length":
                self.response.status_messages.append("Response truncated due to length limit")
                self.response.success = True
            elif finish_reason == "tool_calls":
                # The model wants to invoke tools — mark as successful so the
                # caller can inspect response.tool_calls and act on them.
                self.response.tool_call_completed = True
                self.response.success = True

        # Handle usage info if present
        usage = data.get("usage")
        if usage:
            self.response.usage_info = {
                "prompt_tokens": usage.get("prompt_tokens", 0),
                "completion_tokens": usage.get("completion_tokens", 0),
                "total_tokens": usage.get("total_tokens", 0)
            }

    def _notify_progress(self):
        """Notify progress callback (thread-safe via bpy.app.timers)."""
        if self.on_progress_callback and self.response:
            try:
                self.on_progress_callback(self.response)
            except Exception as e:
                logger.debug(f"Progress callback error: {str(e)}")

    def _handle_generation_error(self, error_msg: str):
        """Handle generation error."""
        logger.error(f"OpenAI generation error: {error_msg}")

        if self.response:
            self.response.error = error_msg
            self.response.success = False
            self.response.is_complete = True

        self._is_generating = False

        if self.on_error_callback:
            self.on_error_callback(error_msg)

    def close(self):
        """Cancel any ongoing generation."""
        self._cancel_requested = True
        self._is_generating = False


# Singleton instance
openai_client = OpenAIClient()
