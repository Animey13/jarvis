# Project Architecture Notes

## System Components
- **STT**: Faster-Whisper CTranslate2 engine for offline speech recognition.
- **TTS**: Kokoro ONNX neural speech synthesis running locally on CPU.
- **LLM**: Ollama server orchestrating Llama 3 8B model.
- **RAG**: Local TF-IDF embeddings with cosine similarity vector store.