# Model card - nyayshastra-legal

## Serving model (current default)

| | |
|---|---|
| Ollama tag | `nyayshastra-legal` (built from `backend/ollama/Modelfile`) |
| Weights | `hf.co/GSMS-B/Indian-Legal-Qwen2.5-3B-GGUF` Q4_K_M (1.9 GB), Apache-2.0 |
| Upstream | QLoRA of Qwen2.5-3B-Instruct on `GSMS-B/Indian-Legal-QA-BNS-BNSS-BSA` (synthetic QA; provenance not documented upstream; model card lists conflicting base models 1.5B / 3B) |
| Runtime params | temperature 0.1, top_p 0.9, repeat_penalty 1.15, repeat_last_n 256, num_ctx 4096, num_predict 512 |
| Role | Explains retrieved evidence only. Never the source of legal facts. |

Observed failure modes without grounding (2026-10-08): invents citations when asked without context
(e.g. cognizable offence -> "Section 210 BNSS"); conflates neighbouring sections (s.103 vs s.105 penalties);
repetition loops near the token limit at repeat_penalty 1.1. In the RAG pipeline 39% of raw answers contained
an unverifiable section/term/source; all were withheld by the citation verifier.

## Fine-tuning (QLoRA on Apple Silicon, mlx-lm)

| | |
|---|---|
| Base | `GSMS-B/Indian-Legal-Qwen2.5-3B` safetensors, quantized to 4-bit (4.5 bpw) -> QLoRA |
| LoRA | rank 16, alpha 32 (scale 2.0), dropout 0.05, q/k/v/o + MLP projections, top 16 layers, 13.3M trainable params (0.43%) |
| Optimiser | Adam, lr 1.5e-5 cosine (warmup 50), batch 2 x grad-accum 4, max seq 1280, grad checkpointing, loss on answers only |
| Data | `training/generate_instruction_data.py`: 3,858 grounded examples built from verified BNS/BNSS/BSA text (no model-generated facts) |
| Task mix | grounded QA 27%, statute extraction 22%, comparison 15%, refusal 15%, citation grounding 7%, penalty extraction 6%, fact-to-statute 6%, definitions <1% |
| Splits | document-level by section hash (train 3,006 / valid 290 / test 562); every benchmark gold section is forced into test; leakage asserted at build time |
| Artifacts | `training/adapters/nyay-qlora/` (adapter, config, dataset manifest), `training/train.log`, `training/test.log` |

Promotion rule: an exported tag (`training/export_to_ollama.sh`) replaces `nyayshastra-legal` only if
`evaluation/evaluate.py --mode e2e` shows a lower raw unsupported-claim rate with no loss in refusal accuracy.

## Data provenance

`backend/manifests/sources.json` (what is fetched), `fetch_log.json` (resolved URL + sha256),
`dataset_manifest.json` (records, preprocessing, intended use). Statute text is used for retrieval and
for grounded instruction data only; it is not trained on as raw text.

## Limitations

- Only BNS, BNSS and BSA are indexed. IPC/CrPC/IEA/Constitution are pending (India Code unavailable at ingestion).
- No judgment corpus: case-law questions are refused.
- No verified IPC<->BNS mapping table is used for answers (`mappings.csv` has no provenance and is UI-only).
- Not legal advice.
