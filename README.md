# Vibe5D for Blender

**Open-Source Blender AI Assistant**

Vibe5D is a fully open-source AI assistant for Blender 3D. It integrates directly into Blender's viewport with a custom GPU-accelerated UI panel, enabling you to chat with AI models to create, modify, and manage 3D scenes using natural language.

**No license keys, no subscriptions, no cloud dependency.** Use your own OpenAI API key or run a local LLM (Ollama, LM Studio, etc.).

![prompts](docs/media/main.gif)

## Features

- 🎨 **Custom GPU-based UI** in the left sidebar with chat interface
- 🤖 **Multiple LLM providers**: OpenAI/ChatGPT, Ollama, LM Studio, LocalAI, vLLM, or any OpenAI-compatible API
- 📷 **Photo reference upload** — attach reference images to your prompts for vision-capable models
- 🔍 **SQL-like query tool** `vibe5d.query(query)` — lets AI inspect scene data
- 🛡️ **Code execution guards** with blocklist validation and undo-based rollback (not a sandbox — review code before accepting)
- 📝 **Chat history** persistence across sessions
- ⚡ **Context size limiting** to prevent freezing with large scenes
- 🖥️ **Fully local option** — run everything on your machine with no internet required

## Getting Started

![auth](docs/media/6.gif)

### 1. Install the Addon

**Option A — Download a release:**
- Go to [Releases](https://github.com/justanotherfivemdev/vibe5d-blender/releases) and download the latest `.zip`

**Option B — Build from source:**
```bash
git clone https://github.com/justanotherfivemdev/vibe5d-blender.git
cd vibe5d-blender
python build.py          # or ./build.sh on Unix, build.bat on Windows
```
The build output is `build/vibe5d-blender-<version>.zip`.

### 2. Install in Blender

1. Open Blender (4.4 or later)
2. Go to `Edit > Preferences > Add-ons`
3. Click `Install...` and select the `.zip` file
4. Enable the **Vibe5D** addon in the list

### 3. Configure Your LLM Provider

Open the Vibe5D sidebar in the 3D Viewport (press `N` to open the sidebar, then find the **Vibe5D** tab). Click the **Settings** gear icon and choose your provider:

#### OpenAI / ChatGPT
1. Get an API key from [platform.openai.com](https://platform.openai.com)
2. In Vibe5D Settings, select **OpenAI / ChatGPT**
3. Paste your API key
4. Optionally set a model name (default: `gpt-4o-mini`)

#### Local LLM (Ollama, LM Studio, etc.)
1. Install and start your local LLM server (see [Using Local LLMs](#using-local-llms) below)
2. In Vibe5D Settings, select **Local / Custom API**
3. Set the Base URL (e.g. `http://localhost:11434/v1` for Ollama)
4. Set the model name (e.g. `llama3`)

> **Requires Blender 4.4 or later**

## Using Photo References

Vibe5D supports attaching reference images to your prompts. This works with any vision-capable model (e.g. GPT-4o, GPT-4o-mini, LLaVA, etc.).

### How to Attach an Image

1. Click the **image icon** (📷) in the bottom-left of the chat input area
2. A file browser will open — select your image file
3. Supported formats: **PNG, JPG, JPEG, BMP, TIFF, WebP** (max 20 MB)
4. The input placeholder will update to show the attached filename
5. Type your prompt (e.g. *"Create a 3D model based on this reference"*)
6. Press **Enter** or click **Send** — the image is sent along with your message

The image is encoded as a base64 data URI and sent directly to the LLM provider as part of the multimodal message. No images are uploaded to any external server.

### Tips for Best Results
- Use a **vision-capable model** (GPT-4o, GPT-4o-mini, LLaVA, etc.)
- Provide **clear prompts** describing what you want the AI to do with the reference
- Works great for: recreating objects, matching colors/materials, modeling from concept art

## Using Local LLMs

Vibe5D supports any OpenAI-compatible API. Popular options:

### Ollama (Recommended for local)
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3
# Vibe5D will connect to http://localhost:11434/v1 by default
```

### LM Studio
- Download from [lmstudio.ai](https://lmstudio.ai)
- Start the local server
- Set Base URL to `http://localhost:1234/v1` in Vibe5D settings

### Other Compatible APIs
- LocalAI, vLLM, text-generation-webui, or any OpenAI-compatible endpoint

## Building from Source

### Requirements
- Python 3 (any version that ships with Blender 4.x works)
- No additional dependencies needed

### Build Commands

| Platform | Command | Output |
|----------|---------|--------|
| Any | `python build.py` | `build/vibe5d-blender-<version>.zip` |
| Unix/macOS | `./build.sh` | Same as above |
| Windows | `build.bat` | Same as above |

The build script packages all addon files into a Blender-installable ZIP, excluding development files (docs, tests, build scripts, etc.).

### Installing the Built Addon

```
Blender → Edit → Preferences → Add-ons → Install… → select vibe5d-blender-<version>.zip
```

## Contributing

Contributions are welcome! Please open issues and pull requests on GitHub.

## License

See [LICENSE](LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/justanotherfivemdev/vibe5d-blender)
- [Discord](https://discord.gg/dXAN23NwkM)
