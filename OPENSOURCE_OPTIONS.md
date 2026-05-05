# Open Source Voice Agent Evaluation

This document explores options for replacing Gemini with a local, open-source voice agent. The requirements are:
- Process Voice and Text inputs (Images optional).
- Output Voice and Text.
- Capable of running in 'realtime' on an NVIDIA RTX 4060 Ti with 16GB VRAM.

## Current Implementation Context

The current voice agent implementation (`backend/ada.py`) relies entirely on Google's cloud infrastructure, specifically:
*   **Model:** `gemini-2.5-flash-native-audio-preview-12-2025`
*   **Architecture:** It utilizes the **Gemini Multimodal Live API**.
*   **ASR / TTS / LLM:** Because the current Gemini implementation is an end-to-end native audio model, there is currently **no distinct local ASR (Speech-to-Text), Text-only LLM, or TTS (Text-to-Speech) pipeline** in place for the voice agent. Audio PCM data is streamed directly to Google, and audio PCM data is streamed back.

Replacing this means we must either adopt another end-to-end unified model (like Moshi) or manually construct the missing ASR, LLM, and TTS pipeline components locally.

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
*   **Pros:** Specifically designed for real-time speech interaction. It can listen and speak simultaneously (full duplex), prioritizing absolute minimum latency. It's built to run locally and is relatively efficient.
*   **Cons:** **Poor Audio Quality.** While it achieves low latency, the generated voice quality, emotional expressiveness, and overall naturalness are significantly lacking compared to dedicated TTS models. It also struggles with mixed text/voice inputs and structured text outputs compared to standard text LLMs.

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

## Comparison vs. Current Gemini Implementation

Switching from Gemini's cloud-based multimodal API to local open-source models introduces distinct tradeoffs in cost and latency.

**Cost:**
*   **Gemini:** Operates on a pay-per-token/second model. High-frequency real-time audio interaction can quickly become expensive due to the dense data rate of streaming audio and continuous API polling.
*   **Local Open Source:** Essentially **free** to operate after the initial hardware investment (NVIDIA RTX 4060 Ti). This allows for unlimited, continuous 24/7 interaction without recurring API costs.

**Latency:**
*   **Gemini:** Heavily dependent on network conditions and Google's server load. While the Gemini 1.5 Pro/Flash models are fast, round-trip audio transmission introduces unavoidable base latency (often 500ms - 1s+).
*   **Local Open Source:** Eliminates network transport latency entirely.
    *   **Unified Models (Moshi/Qwen2-Audio):** Can achieve sub-300ms Time-To-First-Byte (TTFB) since the audio is processed directly on the GPU. Moshi, designed for full-duplex, is nearly indistinguishable from human response times.
    *   **Chained Architecture:** Introduces minor pipelining latency (ASR -> LLM -> TTS). However, using heavily optimized local components (e.g., Whisper Turbo + Llama-3 8B + Kokoro), total TTFB can still realistically be kept under 500ms-800ms, rivaling or beating standard cloud API calls depending on the user's internet connection.

## Recommendation

**For the Best Quality and Overall Naturalness (Recommended):** Implement a **Chained Architecture**.
*   **ASR:** `distil-whisper` or `whisper-large-v3-turbo`
*   **LLM:** Quantized `Llama-3.1-8B-Instruct` (or `Qwen2-VL-7B` if image input is needed)
*   **TTS:** **Kokoro-82M** or **F5-TTS**
*   **Why:** This approach provides the highest quality output. Models like Kokoro deliver state-of-the-art voice naturalness that unified models currently cannot match. It easily fits in 16GB VRAM and allows independent upgrades as the open-source ecosystem rapidly evolves.

**For Native Audio Understanding (Low Latency Input):** Use **Qwen2-Audio** or **Ultravox**.
*   These natively process audio input (skipping ASR latency) but output text, which must still be passed to a high-quality TTS like Kokoro. This is an excellent middle ground, preserving strong LLM reasoning and top-tier voice output while reducing input latency.

**For Extreme Low Latency (At the Cost of Quality):** Investigate **Moshi** (`kyutai/moshiko-pytorch-bf16`).
*   **Warning:** While Moshi offers full-duplex, near-zero latency interaction, its voice generation quality sounds robotic and poor compared to the alternatives. It should only be chosen if sub-300ms latency is the singular priority over user experience and audio fidelity.
