# AIFunctions library

## Description

This code is designed to be a central hub for interacting with various artificial intelligence (AI) models. Think of it as a smart assistant that can talk to different AI brains. It's built to manage conversations, remember what's been said, and send requests to different AI services, making it flexible and powerful for building AI-powered applications.

At its core is a system that keeps track of conversations, like a diary for the AI. It remembers past interactions, making sure the AI has context for current discussions. This "memory" is managed carefully to stay within limits, so the AI doesn't get overwhelmed. The system also knows how to "count words" in a way that AI models understand, which is important for managing how much information is sent to them.

The code acts like a switchboard, directing your requests to the right AI service. Whether you want to talk to OpenAI, Google's AI, or another provider, this system knows how to connect and get a response. It's set up to handle different types of AI models and their unique ways of communicating, making it easy to switch between them or add new ones in the future.

When you ask the AI something, this system handles the entire process. It takes your input, updates the AI's memory, sends the request to the chosen AI model, and then stores the AI's answer. It also keeps track of how long these interactions take, helping to understand and improve the AI's performance. This ensures that every conversation is managed smoothly, from start to finish.

## Technical

The provided Python code defines a class named `Agent` designed to facilitate interactions with various Artificial Intelligence (AI) models. This class encapsulates functionalities for managing conversational memory, handling token limits, and routing requests to different AI services. The `Agent` class is initialized with a comprehensive set of parameters that configure its behavior and operational settings.

The `__init__` method serves as the constructor for the `Agent` class. It accepts numerous parameters to customize the AI interaction:
*   `engine`: A string specifying the AI engine to be used (e.g., 'openai', 'googleai'). This is converted to lowercase for case-insensitive matching.
*   `model`: A string representing the specific AI model to be utilized (e.g., 'gpt-4o', 'gemini-pro').
*   `maxtokens`: An integer defining the maximum number of tokens allowed for a given model's context window.
*   `encoding`: An optional string specifying the encoding method for tokenization. If `None` and the `engine` is 'openai', it defaults to 'o200k_base' for 'gpt-4o' models or 'cl100k_base' for others.
*   `persona`: An optional string that specifies a persona for the AI, likely loaded from configuration files.
*   `user`: An optional string representing the user interacting with the agent.
*   `userhome`: An optional string specifying a custom home directory for storing data, overriding the default system user's home directory.
*   `maxmem`: An integer setting the maximum number of memory items to retain.
*   `freqpenalty`: A float controlling the frequency penalty applied during text generation.
*   `temperature`: A float that influences the randomness or creativity of the AI's responses.
*   `seed`: An integer for seeding random number generation, potentially for reproducible results.
*   `timeout`: An integer specifying the timeout duration in seconds for API requests.
*   `reset`: A boolean flag to indicate whether to reset the memory before processing a request.
*   `save`: A boolean flag to control whether memory should be saved to persistent storage.
*   `timing`: A boolean flag to enable or disable timing of AI API calls for performance monitoring.
*   `isolation`: A boolean flag to indicate if the interaction should be isolated, meaning no memory is loaded or saved.
*   `retry`: An integer specifying the maximum number of retries for failed API requests.
*   `retrytimeout`: An integer defining the sleep duration in seconds between retries.
*   `maxrespsize`: An integer that sets a maximum size for AI responses; a value of 0 disables this check.
*   `maxrespretry`: An integer for the number of retries when a response exceeds `maxrespsize`.
*   `maxrespretrytimeout`: An integer for the sleep duration in seconds between retries for response size limits.
*   `UseOpenAI`: A boolean flag to indicate whether to use OpenAI-compatible libraries for certain services, particularly for Google AI.

The `Agent` class also includes several methods for managing its state and interacting with AI services. The `SetStorage` method configures the file paths for memory and timing data, dynamically determining locations based on the `user` and `userhome` parameters, or falling back to default system paths. The `Reset` method clears the current memory and deletes the associated memory file. The `Get` method retrieves a simplified view of the memory, containing only the 'role' and 'content' of each message. The `Put` method adds a new message to the `Memory` list, calculating its token count using `GetTokenCount`. `UpdateLast` modifies the last entry in the `Memory` list.

The `Read` method loads conversation history from a file specified by `self.MemoryLocation`. It parses each line as JSON, validates essential fields, recalculates token counts, and appends valid entries to `self.Memory`, excluding system messages. The `Write` method persists the current `self.Memory` to `self.MemoryLocation`. It first truncates the memory if `self.MaxMemory` is set and then writes each non-system message as a JSON string to the file.

The `GetTokenCount` method is crucial for managing token limits. It dynamically selects a tokenizer based on the `self.engine` (e.g., `tiktoken` for OpenAI, `AutoTokenizer` for Hugging Face) and the specified `self.model`. It then encodes the provided `data` and returns the number of tokens. For unsupported engines, it provides a basic character-based estimation.

The `MaintainTokenLimit` method ensures that the total token count of messages in `self.Memory` does not exceed `self.maxtokens`. It iteratively removes older messages, prioritizing the removal of user-assistant pairs, until the token limit is met. It returns a list of messages formatted for AI consumption and the current token count.

The `JumpTable` method acts as a dispatcher, routing the request to the appropriate AI service based on the `self.engine` attribute. It takes `messages`, `engine`, `model`, `freqpenalty`, `temperature`, `timeout`, and optional `seed` and `mt` (max tokens context) as parameters. It reads API keys using `FF.ReadTokens` and then calls specific `Get` methods (e.g., `GetOpenAI`, `GetGoogleAI`, `GetAnthropic`) corresponding to the engine. It handles exceptions by setting `self.response` and `self.completion` to `None`.

The `Response` method orchestrates the entire interaction process. It first handles potential memory resets and loads persona-based system messages if applicable. It then reads existing memory (if not in isolation mode), adds the user's input to memory, and calls `MaintainTokenLimit` to ensure the token limit is respected. If the token limit is exceeded, it returns `None`. Otherwise, it enters a retry loop, calling `JumpTable` to interact with the AI service. The loop continues until a response is received or the maximum retries are exhausted. It also includes logic for handling response size limitations. If a response is successfully obtained, it's added to memory, the raw completion is stored, and the memory is saved if `self.save` is true and not in isolation. Timing information is logged if `self.timing` is enabled.

Finally, the code includes a series of `Get` methods (e.g., `GetOpenAI`, `GetGoogleAI`, `GetOpenRouter`, `GetAnthropic`, `GetHuggingFace`, `GetTogetherAI`, `GetCohere`, `GetOllama`, `GetPerplexity`) that are responsible for making direct API calls to specific AI providers. Each of these methods takes an `apikey`, `messages`, `model`, `freqpenalty`, `temperature`, and `timeout`. They instantiate the respective AI client libraries, construct and send the API request, process the response, and return the extracted content and the full completion object. They also set `self.stop` and `self.AIError` based on the AI's response. The `GetGoogleAI` method has a special case for `UseOpenAI=True` which uses an OpenAI-compatible endpoint for Google's models, and a separate path for native Gemini API interaction, including safety settings configuration. The `GetPersona` method is a static method that attempts to load persona system prompts from files, prioritizing channel-specific and NSFW configurations.
