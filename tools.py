from typing import List
from engine import State, tool_registry


def split_text_tool(state: State) -> State:
    text = state.get("text", "")
    chunk_size = int(state.get("chunk_size", 50))

    words = text.split()
    chunks: List[str] = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i + chunk_size]))

    state["chunks"] = chunks
    return state


def summarize_chunks_tool(state: State) -> State:
    chunks: List[str] = state.get("chunks", [])
    summaries: List[str] = []

    for chunk in chunks:
        words = chunk.split()
        summary = " ".join(words[: min(20, len(words))])
        summaries.append(summary)

    state["summaries"] = summaries
    return state


def merge_summaries_tool(state: State) -> State:
    summaries: List[str] = state.get("summaries", [])
    merged = " ".join(summaries)
    state["merged_summary"] = merged
    return state


def refine_summary_tool(state: State) -> State:
    raw = state.get("summary") or state.get("merged_summary") or ""
    limit = int(state.get("summary_limit", 50))

    words = raw.split()

    # Removing consecutive duplicates
    deduped: List[str] = []
    prev = None
    for w in words:
        if w != prev:
            deduped.append(w)
        prev = w

    # Soft trimming, and if it is still too long, shrink ~30%, but not below limit
    if len(deduped) > limit:
        new_len = max(limit, int(len(deduped) * 0.7))
    else:
        new_len = len(deduped)

    refined = " ".join(deduped[:new_len])
    state["summary"] = refined
    return state


def check_length_tool(state: State) -> State:
    summary = state.get("summary", "")
    limit = int(state.get("summary_limit", 50))
    words = summary.split()
    state["summary_too_long"] = len(words) > limit
    return state

# Registering tools on import

tool_registry["split_text_tool"] = split_text_tool
tool_registry["summarize_chunks_tool"] = summarize_chunks_tool
tool_registry["merge_summaries_tool"] = merge_summaries_tool
tool_registry["refine_summary_tool"] = refine_summary_tool
tool_registry["check_length_tool"] = check_length_tool
