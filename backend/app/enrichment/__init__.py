"""Enrichment package: post-ingestion processing of articles (docs/05 §3-§6).

Pipeline order (see app.worker):
lang_detect -> translate -> topics -> embed -> hot_score -> cluster.

All LLM-dependent steps are graceful: without MOONSHOT_API_KEY they log and
no-op (topics has a keyword-heuristic fallback; insights has a non-LLM
fallback generator).
"""
