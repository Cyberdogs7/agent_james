# Open Source Voice Agent Evaluation

This document explores options for replacing Gemini with a local, open-source voice agent. The requirements are:
- Process Voice and Text inputs (Images optional).
- Output Voice and Text.
- Capable of running in 'realtime' on an NVIDIA RTX 4060 Ti with 16GB VRAM.

## Unified Multimodal Models (Any-to-Any / Omni)

The ideal solution is a single model capable of processing and generating both text and audio end-to-end, minimizing latency compared to chained models.

### 1. Qwen2-Audio (and variants)
**Model:** `Qwen/Qwen2-Audio-7B-Instruct`
*   **Capabilities:** Input: Audio + Text. Output: Text.
*   **Pros:** Highly downloaded, natively handles audio without needing a separate Whisper module. It's relatively lightweight (7B parameters) making it a strong candidate for 16GB VRAM, especially if quantized (e.g., GGUF versions available).
*   **Cons:** While excellent at audio understanding and transcription, it primarily outputs text. To achieve voice output, this would need to be chained with a Fast TTS engine.

### 2. Moshi
**Model:** `kyutai/moshiko-pytorch-bf16`
*   **Capabilities:** Full duplex, real-time voice-to-voice interaction.
*   **Pros:** Specifically designed for real-time speech interaction. It can listen and speak simultaneously (full duplex), making it extremely natural. It's built to run locally and is relatively efficient.
*   **Cons:** It's heavily focused on voice-to-voice. Handling mixed text/voice inputs and structured text outputs might require more complex integration compared to standard text LLMs.

### 3. GLM-4-Voice
**Model:** `zai-org/glm-4-voice-9b`
*   **Capabilities:** Voice understanding and generation.
*   **Pros:** Native end-to-end voice modeling. At 9B parameters, it should fit comfortably within 16GB VRAM, especially with 4-bit or 8-bit quantization.
*   **Cons:** Requires separate tokenizer and decoder models to be run in tandem, which might complicate deployment.

### 4. Ultravox
**Model:** `fixie-ai/ultravox-v0_5-llama-3_2-1b` (and larger variants like 8B)
*   **Capabilities:** Input: Audio + Text. Output: Text.
*   **Pros:** Highly efficient. The 1B parameter version is extremely fast and light. It builds directly on Llama architectures.
*   **Cons:** Like Qwen2-Audio, it natively outputs text, requiring a TTS chain for voice output.

## Chained Architecture (ASR + LLM + TTS)

If a single omni-model doesn't meet the specific conversational or reasoning requirements, a chained approach is a viable, highly customizable alternative.

### Components

**1. Automatic Speech Recognition (ASR)**
*   **Option:** `openai/whisper-large-v3-turbo` or `distil-whisper`.
*   **Pros:** Extremely accurate text transcription. 'Turbo' or distilled versions are fast enough for real-time use.

**2. Large Language Model (LLM)**
*   **Option:** `meta-llama/Llama-3.1-8B-Instruct` or `Qwen/Qwen2.5-7B-Instruct`. (Optional Vision: `llava-v1.5-7b` or `Qwen2-VL-7B`).
*   **Pros:** World-class reasoning and text generation. At ~8B parameters, these run very fast on 16GB VRAM, leaving room for ASR and TTS.

**3. Text-to-Speech (TTS)**
*   **Option:** `hexgrad/Kokoro-82M` (Kokoro v1.0) or `SWivid/F5-TTS`.
*   **Pros:** **Kokoro** is the current state-of-the-art for open-source TTS efficiency and naturalness (4.5 MOS), featuring an incredibly lightweight 82M parameter footprint and a permissive Apache 2.0 license. **F5-TTS** is another highly capable open-source alternative known for expressive speech. These significantly outperform older models like Bark or XTTS-v2 in both speed and quality.

### Chained Architecture Feasibility on 16GB VRAM
Running Whisper (small/turbo), an 8B LLM (4-bit quantized), and a lightweight state-of-the-art TTS model concurrently is entirely feasible on an RTX 4060 Ti 16GB.
*   **LLM (8B, 4-bit):** ~5-6 GB VRAM.
*   **Whisper (Turbo):** ~2-3 GB VRAM.
*   **TTS (Kokoro/F5-TTS):** ~1-2 GB VRAM (Kokoro is exceptionally light).
*   **Total:** ~8-11 GB VRAM, leaving a large, comfortable margin.

## Recommendation

**For the lowest latency, most natural voice interaction:** Investigate **Moshi** (`kyutai/moshiko-pytorch-bf16`). It is designed specifically for the real-time, full-duplex voice use case.

**For maximum flexibility and reasoning capability:** Implement a **Chained Architecture** using `distil-whisper`, a quantized `Llama-3.1-8B-Instruct` (or a VL variant if images are needed), and a SOTA lightweight TTS like **Kokoro**. This allows upgrading individual components as better open-source models are released, while maintaining incredible TTS naturalness and minimal VRAM usage.

**For a middle ground (Native Audio Understanding + TTS):** Use **Qwen2-Audio** or **Ultravox** for native audio-in/text-out, and chain it with a fast TTS engine. This eliminates the latency of the ASR step while maintaining strong LLM reasoning.
