# Vibe5D for Blender

**Open-Source Blender AI Assistant**

Vibe5D is a fully open-source AI assistant for Blender 3D. It integrates directly into Blender's viewport with a custom GPU-accelerated UI panel, enabling you to chat with AI models to create, modify, and manage 3D scenes using natural language.

**No license keys, no subscriptions, no cloud dependency.** Use your own OpenAI API key or run a local LLM (Ollama, LM Studio, etc.).

![prompts](docs/media/main.gif)

## Features

- 🎨 **Custom GPU-based UI** in the left sidebar with chat interface
- 🤖 **Multiple LLM providers**: OpenAI/ChatGPT, Ollama, LM Studio, LocalAI, vLLM, or any OpenAI-compatible API
- 🔍 **SQL-like query tool** `vibe5d.query(query)` — lets AI inspect scene data
- 🛡️ **Code execution guards** with blocklist validation and undo-based rollback (not a sandbox — review code before accepting)
- 📝 **Chat history** persistence across sessions
- ⚡ **Context size limiting** to prevent freezing with large scenes
- 🖥️ **Fully local option** — run everything on your machine with no internet required

## Getting Started

![auth](docs/media/6.gif)

1. **Download** the addon from [Releases](https://github.com/justanotherfivemdev/vibe5d-blender/releases) or build it yourself with `python build.py`

2. **Install in Blender:**
   - Go to `Edit > Preferences > Add-ons > Install...`
   - Select the `.zip` file

3. **Configure your LLM provider** in the Settings panel:
   - **OpenAI**: Enter your API key from [platform.openai.com](https://platform.openai.com)
   - **Local LLM**: Start Ollama/LM Studio and point to its API URL (default: `http://localhost:11434/v1`)

> Requires **Blender 4.4** or later

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

## Contributing

Contributions are welcome! Please open issues and pull requests on GitHub.

## License

See [LICENSE](LICENSE) for details.

## Links

- [GitHub Repository](https://github.com/justanotherfivemdev/vibe5d-blender)
- [Discord](https://discord.gg/dXAN23NwkM)
