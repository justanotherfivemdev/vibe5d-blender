import bpy
from bpy.props import StringProperty, BoolProperty, IntProperty, EnumProperty, CollectionProperty
from bpy.types import Scene, PropertyGroup, WindowManager


class VIBE5D_ChatMessage(PropertyGroup):
    role: EnumProperty(
        name="Role",
        description="Who sent this message",
        items=[
            ('system', 'System', 'System message'),
            ('user', 'User', 'Message from user'),
            ('assistant', 'Assistant', 'Message from AI assistant'),
            ('tool', 'Tool', 'Tool response message'),
            ('error', 'Error', 'Error message')
        ],
        default='user'
    )

    content: StringProperty(
        name="Content",
        description="Message content",
        default=""
    )

    timestamp: StringProperty(
        name="Timestamp",
        description="When this message was created",
        default=""
    )

    message_id: StringProperty(
        name="Message ID",
        description="Unique identifier for this message",
        default=""
    )

    chat_id: StringProperty(
        name="Chat ID",
        description="Unique identifier for the chat this message belongs to",
        default=""
    )

    tool_calls_json: StringProperty(
        name="Tool Calls JSON",
        description="JSON string of tool calls (for assistant messages)",
        default=""
    )

    image_data: StringProperty(
        name="Image Data",
        description="Base64 encoded image data URI (for messages with images)",
        default=""
    )

    tool_call_id: StringProperty(
        name="Tool Call ID",
        description="ID of the tool call this response corresponds to (for tool messages)",
        default=""
    )


def register_properties():
    bpy.utils.register_class(VIBE5D_ChatMessage)

    Scene.vibe5d_model = StringProperty(
        name="Model",
        description="AI model to use for all interactions",
        default="gpt-4o-mini"
    )

    Scene.vibe5d_prompt = StringProperty(
        name="Prompt",
        description="Current prompt input",
        default=""
    )

    Scene.vibe5d_output_content = StringProperty(
        name="Output Content",
        description="Generated output content",
        default=""
    )

    Scene.vibe5d_final_code = StringProperty(
        name="Final Code",
        description="Final generated code",
        default=""
    )

    Scene.vibe5d_guide_content = StringProperty(
        name="Guide Content",
        description="Generated guide content",
        default=""
    )

    Scene.vibe5d_last_error = StringProperty(
        name="Last Error",
        description="Last error message",
        default=""
    )

    Scene.vibe5d_console_output = StringProperty(
        name="Console Output",
        description="Console output from code execution",
        default=""
    )

    Scene.vibe5d_is_generating = BoolProperty(
        name="Is Generating",
        description="Whether AI is currently generating",
        default=False
    )

    Scene.vibe5d_execution_pending = BoolProperty(
        name="Execution Pending",
        description="Whether code execution is pending",
        default=False
    )

    Scene.vibe5d_chat_messages = CollectionProperty(
        type=VIBE5D_ChatMessage,
        name="Chat Messages",
        description="Collection of chat messages"
    )

    Scene.vibe5d_chat_messages_index = IntProperty(
        name="Chat Messages Index",
        description="Current index in chat messages collection",
        default=0,
        min=0
    )

    Scene.vibe5d_current_chat_id = StringProperty(
        name="Current Chat ID",
        description="Current chat identifier",
        default=""
    )

    Scene.vibe5d_current_text_input = StringProperty(
        name="Current Text Input",
        description="Current unsent text input",
        default=""
    )

    Scene.vibe5d_custom_instruction = StringProperty(
        name="Custom Instruction",
        description="Single multiline custom instruction for AI behavior",
        default=""
    )

    Scene.vibe5d_provider = EnumProperty(
        name="LLM Provider",
        description="Which LLM provider to use for AI interactions",
        items=[
            ('openai', 'OpenAI / ChatGPT',
             'Use the OpenAI API directly (requires API key from platform.openai.com)'),
            ('local', 'Local / Custom API',
             'Use any OpenAI-compatible API server — Ollama, LM Studio, LocalAI, '
             'vLLM, text-generation-webui, or any other compatible endpoint'),
        ],
        default='openai'
    )

    Scene.vibe5d_provider_api_key = StringProperty(
        name="API Key",
        description="API key for the selected LLM provider",
        default="",
        subtype='PASSWORD'
    )

    Scene.vibe5d_provider_base_url = StringProperty(
        name="Base URL",
        description="Base URL for the LLM API endpoint",
        default=""
    )

    Scene.vibe5d_provider_model = StringProperty(
        name="Provider Model",
        description="Model name for the selected provider (e.g., gpt-4o-mini, llama3)",
        default=""
    )

    Scene.vibe5d_ui_active = BoolProperty(
        name="UI Active",
        description="Whether the UI overlay is currently active",
        default=False
    )

    Scene.vibe5d_ui_viewport_config = StringProperty(
        name="UI Viewport Config",
        description="Saved viewport configuration for UI state persistence",
        default="{}"
    )

    Scene.vibe5d_ui_current_view = StringProperty(
        name="UI Current View",
        description="Current view state for UI persistence",
        default="main"
    )

    Scene.vibe5d_ui_conversation_state = StringProperty(
        name="UI Conversation State",
        description="Saved conversation state for UI persistence",
        default="{}"
    )

    Scene.vibe5d_ui_layout_version = IntProperty(
        name="UI Layout Version",
        description="Version of the UI layout for compatibility",
        default=1
    )

    Scene.vibe5d_ui_area_markers = StringProperty(
        name="UI Area Markers",
        description="JSON data for tracking UI area identification",
        default="{}"
    )

    WindowManager.vibe5d_ui_was_active = BoolProperty(
        name="UI Was Active",
        description="Tracks if UI was previously active for state recovery",
        default=False
    )

    Scene.vibe5d_generation_progress = IntProperty(
        name="Generation Progress",
        description="Current generation progress percentage",
        default=0,
        min=0,
        max=100
    )

    Scene.vibe5d_generation_stage = StringProperty(
        name="Generation Stage",
        description="Current generation stage description",
        default=""
    )


def unregister_properties():
    properties_to_remove = [
        "vibe5d_model", 'vibe5d_prompt', 'vibe5d_output_content', 'vibe5d_final_code',
        "vibe5d_guide_content", 'vibe5d_last_error', 'vibe5d_console_output',
        "vibe5d_is_generating", 'vibe5d_execution_pending',
        "vibe5d_chat_messages", 'vibe5d_chat_messages_index',
        "vibe5d_current_chat_id", 'vibe5d_current_text_input',
        "vibe5d_custom_instruction",
        "vibe5d_provider", "vibe5d_provider_api_key", "vibe5d_provider_base_url", "vibe5d_provider_model",
        "vibe5d_ui_active", 'vibe5d_ui_viewport_config', 'vibe5d_ui_current_view',
        "vibe5d_ui_conversation_state", 'vibe5d_ui_layout_version', 'vibe5d_ui_area_markers',
        "vibe5d_generation_progress", 'vibe5d_generation_stage'
    ]

    for prop_name in properties_to_remove:
        if hasattr(Scene, prop_name):
            delattr(Scene, prop_name)

    wm_properties_to_remove = [
        'vibe5d_ui_was_active'
    ]

    for prop_name in wm_properties_to_remove:
        if hasattr(WindowManager, prop_name):
            delattr(WindowManager, prop_name)

    try:
        bpy.utils.unregister_class(VIBE5D_ChatMessage)
    except:
        pass
