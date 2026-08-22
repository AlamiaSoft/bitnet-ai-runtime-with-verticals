# ?? Alamia Local AI Runtime

> **A local-first AI runtime for running capable AI models on everyday hardware ? without requiring a GPU or cloud AI APIs.**  
> *(Local-first, CPU-first, cloud-optional).*

---

## ??? The 5 Pillars of Alamia AI

```text
                    ALAMIA LOCAL AI RUNTIME (:8000)
                                   ?
         ?????????????????????????????????????????????????????
         ?                         ?                         ?
  Alamia Model Garden       Alamia AI Router        Alamia AI Verticals
  (Curated SLM Catalog)   (Capability Selector)   (AI Employees & Auto)
         ?                         ?                         ?
         ?????????????????????????????????????????????????????
                                   ?
                        Alamia Inference Fabric
                                   ?
              ???????????????????????????????????????????
              ?                    ?                    ?
       llama.cpp Engine     BitNet 1-bit Engine     TEI Engine
      (Primary Foundation:   (Specialized 1-bit     (High-Throughput
       SLMs, Embed, Rerank)   Ternary Kernel)        Batch Embeddings)
              ?                    ?                    ?
        Qwen, Phi, Gemma       BitNet 2B-4T         BGE Embeddings
```

1. **?? Alamia Model Garden**: Curated catalog of high-efficiency 1?4B SLMs, vector embeddings, and sequence rerankers (Qwen 2.5, Microsoft Phi-3.5, Google Gemma 2, BAAI BGE, Microsoft BitNet).
2. **?? Alamia AI Router**: Capability-aware routing engine that analyzes tasks (extraction, classification, summarization, coding, reasoning) and selects the optimal model under strict privacy and zero-budget policies.
3. **? Alamia Inference Fabric**: Pluggable inference layer powered by `llama.cpp` as the primary CPU/edge foundation, Microsoft `bitnet-server` for 1-bit ternary execution, and Hugging Face `TEI` for batch vector embeddings.
4. **?? Alamia AI Employees**: Autonomous digital workers with multi-role personas, scheduled routines, task queues, and human-in-the-loop approval gates.
5. **?? Alamia AI Verticals**: Pre-packaged vertical solutions:
   - ?? **AI Employee in a Box**: CRM triage, proposal drafting, and daily executive briefings.
   - ?? **Personal Memory OS**: Local semantic document indexing and private knowledge retrieval.
   - ?? **AI Computer Operator**: Autonomous terminal assistant and development runner.
   - ?? **AI WhatsApp Bot**: Customer order taking, appointment scheduling, and customer support.
   - ?? **AI QA Box**: Automated web regression crawler and test validator.

---

## ?? Quickstart

### Running with Docker

```bash
docker compose up -d --build
```
Open your browser at **http://localhost:8000/dashboard** to access the **Alamia Model Garden & AI Router Dashboard**.

### Running Locally (Python 3.12+)

```bash
pip install -e .
python -m bitnet_runtime.server.app
```

---

## ?? Technology & Model Attributions

- **Microsoft BitNet**: Native 1-bit ternary quantization kernels and BitNet b1.58 models are developed by Microsoft Research.
- **llama.cpp**: High-performance CPU/edge inference engine developed by Georgi Gerganov and contributors.
- **Hugging Face TEI**: Text Embeddings Inference container for high-throughput embedding generation.
- **Qwen / Phi / Gemma**: Model weights by Alibaba Cloud, Microsoft, and Google DeepMind respectively.

---

## ?? License

Apache-2.0 ? 2026 Alamia AI
