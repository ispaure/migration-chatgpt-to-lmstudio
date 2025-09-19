#!/usr/bin/env python3
"""
lm_export.py

Exports ChatGPT conversations.json (array) -> LM Studio format.
Also normalizes already-LM-shaped files (messages present).

Usage:
  python lm_export.py conversations.json --clean
  python lm_export.py conversations.json --id <conv-id> --keywords foo bar --verbose
"""

import json
from pathlib import Path
import argparse
import shutil
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional
import re
import os
import unicodedata

# Default model name to stamp into files (requested)
DEFAULT_MODEL_NAME = "qwen2.5-vl-72b-instruct"

P_PRIVATE_USE = re.compile(r'[\uE000-\uF8FF]')  # Private Use Area
P_BRACKETED_REFS = re.compile(r'【[^】]*】')      # e.g.,
P_ZERO_WIDTH = re.compile(r'[\u200B-\u200F\u202A-\u202E\u2060-\u206F\uFEFF]')
DOLLAR_PREFIX_RE = re.compile(r'^\s*\$([A-Za-z0-9 _.-]+)\$\s*(.*)$')


def parse_dollar_prefix(title: str):
    """
    If the title starts with $folder$..., return (folder, clean_title).
    Otherwise return (None, title).
    """
    if not isinstance(title, str):
        return None, title or ""
    m = DOLLAR_PREFIX_RE.match(title)
    if not m:
        return None, title.strip()
    folder = m.group(1).strip()
    clean_title = m.group(2).strip()
    return folder, clean_title or title.strip()


def sanitize_folder_name(name: str) -> str:
    # keep it simple but safe for filesystem
    s = name.strip().replace(os.sep, "_")
    s = re.sub(r'[<>:"|?*\0]', '_', s)
    s = re.sub(r'\s{2,}', ' ', s)
    return s or "Uncategorized"


def sanitize_text(s: str) -> str:
    if not s:
        return s
    # Normalize, then strip our usual offenders
    s = unicodedata.normalize("NFKC", s)
    s = P_PRIVATE_USE.sub('', s)
    s = P_BRACKETED_REFS.sub('', s)
    s = P_ZERO_WIDTH.sub('', s)
    # Trim some double spaces left over after removals
    s = re.sub(r' {2,}', ' ', s)
    # Optional: collapse stray space before punctuation
    s = re.sub(r'\s+([,.:;!?\)])', r'\1', s)
    # Optional: tidy up multiple blank lines
    s = re.sub(r'\n{3,}', '\n\n', s)
    return s.strip()


def to_millis(ts: Optional[float]) -> int:
    if ts is None:
        return int(round(datetime.now().timestamp() * 1000))
    try:
        tsf = float(ts)
    except Exception:
        return int(round(datetime.now().timestamp() * 1000))
    return int(tsf) if tsf > 1e12 else int(round(tsf * 1000))

def text_from_content_obj(content_obj: Any, max_len: int = 2_000_000) -> str:
    """
    Robust, non-recursive collector with size guard to avoid hangs.
    Collects strings from ChatGPT content shapes and joins with double newlines.
    """
    stack = [content_obj]
    out_parts: List[str] = []
    seen = 0
    while stack:
        obj = stack.pop()
        if obj is None:
            continue
        if isinstance(obj, str):
            s = obj.strip()
            if s:
                out_parts.append(s)
                seen += len(s)
        elif isinstance(obj, dict):
            if 'parts' in obj and isinstance(obj['parts'], list):
                for p in reversed(obj['parts']):
                    stack.append(p)
            elif 'text' in obj and isinstance(obj['text'], str):
                s = obj['text'].strip()
                if s:
                    out_parts.append(s)
                    seen += len(s)
            else:
                for v in obj.values():
                    stack.append(v)
        elif isinstance(obj, list):
            for it in reversed(obj):
                stack.append(it)
        if seen > max_len:
            break
    return "\n\n".join(out_parts)

def lm_text_block(text: str) -> Dict[str, Any]:
    # Matches LM Studio’s text blocks closely
    return {
        "type": "text",
        "text": text,
        "fromDraftModel": False,
        "isStructural": False
    }

def minimal_gen_info() -> Dict[str, Any]:
    # Safe, minimal genInfo stub seen in LM files
    return {
        "indexedModelIdentifier": DEFAULT_MODEL_NAME,
        "identifier": DEFAULT_MODEL_NAME,
        "loadModelConfig": {"fields": []},
        "predictionConfig": {"fields": []},
        "stats": {
            "stopReason": "eosFound",
            "tokensPerSecond": 0.0,
            "numGpuLayers": -1,
            "timeToFirstTokenSec": 0.0,
            "totalTimeSec": 0.0,
            "promptTokensCount": 0,
            "predictedTokensCount": 0,
            "totalTokensCount": 0
        }
    }


def normalize_user_single_step(text: str) -> Dict[str, Any]:
    text = sanitize_text(text)
    return {
        "versions": [
            {
                "type": "singleStep",
                "role": "user",
                "content": [ lm_text_block(text) ]
            }
        ],
        "currentlySelected": 0
    }


def normalize_assistant_multistep(steps_texts: List[str], step_id_func) -> Dict[str, Any]:
    steps = []
    for raw in steps_texts:
        text = sanitize_text(raw)
        steps.append({
            "type": "contentBlock",
            "stepIdentifier": step_id_func(),
            "content": [ lm_text_block(text) ],
            "defaultShouldIncludeInContext": True,
            "shouldIncludeInContext": True,
            "genInfo": minimal_gen_info()
        })
    return {
        "versions": [
            {
                "type": "multiStep",
                "role": "assistant",
                "senderInfo": { "senderName": DEFAULT_MODEL_NAME },
                "steps": steps
            }
        ],
        "currentlySelected": 0
    }

def build_from_mapping(conversation: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    title = conversation.get('title') or conversation.get('name') or ""
    createdAt_ms = to_millis(conversation.get('create_time') or conversation.get('CreatedAt') or conversation.get('createdAt'))
    mapping = conversation.get('mapping') or {}

    # Unique step id generator for this conversation
    _step_idx = 0
    def next_step_id():
        nonlocal _step_idx
        sid = f"{createdAt_ms}-{_step_idx}"
        _step_idx += 1
        return sid

    # Extract a system prompt if present (first visible, non-empty system msg)
    system_prompt = ""
    sys_candidates = []
    for node in mapping.values():
        msg = isinstance(node, dict) and node.get("message")
        if isinstance(msg, dict) and (msg.get("author") or {}).get("role") == "system":
            if not (msg.get("metadata") or {}).get("is_visually_hidden_from_conversation"):
                t = text_from_content_obj(msg.get("content"))
                if t.strip():
                    sys_candidates.append((to_millis(msg.get("create_time") or 0), t))
    if sys_candidates:
        sys_candidates.sort(key=lambda x: x[0])
        system_prompt = sys_candidates[0][1]

    # Collect visible items
    items: List[Tuple[int, str, str]] = []  # (ts_ms, role, text)
    for node in mapping.values():
        if not isinstance(node, dict):
            continue
        msg = node.get('message')
        if not isinstance(msg, dict):
            continue
        meta = msg.get('metadata') or {}
        if meta.get('is_visually_hidden_from_conversation'):
            continue
        role = (msg.get('author') or {}).get('role', 'user')
        text = text_from_content_obj(msg.get('content'))
        if not text.strip():
            continue
        ts_ms = to_millis(msg.get('create_time') or 0)
        items.append((ts_ms, role.lower() if isinstance(role, str) else 'user', text))

    items.sort(key=lambda x: (x[0], x[1]))

    # Build messages (group consecutive assistants)
    messages: List[Dict[str, Any]] = []
    i = 0
    while i < len(items):
        _, role, text = items[i]
        if role == "user":
            messages.append(normalize_user_single_step(text))
            i += 1
        elif role == "assistant":
            steps_texts: List[str] = []
            while i < len(items) and items[i][1] == "assistant":
                _, _, t2 = items[i]
                steps_texts.append(t2)
                i += 1
            messages.append(normalize_assistant_multistep(steps_texts, next_step_id))
        else:
            i += 1

    lm: Dict[str, Any] = {
        "name": title,
        "pinned": False,
        "createdAt": createdAt_ms,
        "preset": "",
        "tokenCount": 0,
        "systemPrompt": system_prompt or conversation.get("system_prompt", "") or "",
        "messages": messages,
        "usePerChatPredictionConfig": True,
        "perChatPredictionConfig": {
            "fields": [
                {"key": "llm.prediction.temperature", "value": 0.7},
                {"key": "llm.prediction.systemPrompt", "value": system_prompt or ""}
            ]
        },
        "clientInput": "",
        "clientInputFiles": [],
        "userFilesSizeBytes": 0,
        "lastUsedModel": {
            "identifier": DEFAULT_MODEL_NAME,
            "indexedModelIdentifier": DEFAULT_MODEL_NAME,
            "instanceLoadTimeConfig": {"fields": []},
            "instanceOperationTimeConfig": {"fields": []}
        },
        "notes": conversation.get("notes", []),
        "plugins": conversation.get("plugins", []),
        "pluginConfigs": conversation.get("pluginConfigs", {}),
        "disabledPluginTools": conversation.get("disabledPluginTools", []),
        "looseFiles": conversation.get("looseFiles", [])
    }

    # rough token estimate
    approx_chars = 0
    for m in messages:
        v = m["versions"][0]
        if v["type"] == "singleStep":
            approx_chars += len(v.get("content", [{}])[0].get("text", ""))
        else:
            approx_chars += sum(len(s.get("content", [{}])[0].get("text", "")) for s in v.get("steps", []))
    lm["tokenCount"] = max(approx_chars // 4, 0)

    if verbose:
        print(f"[mapping] {title!r}: messages={len(messages)} systemPrompt_len={len(lm['systemPrompt'])}")
    return lm

def normalize_existing_lm(conversation: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    title = conversation.get("name") or conversation.get("title") or ""
    createdAt_ms = to_millis(conversation.get("createdAt") or conversation.get("create_time"))
    sys_prompt = sanitize_text(conversation.get("systemPrompt", "") or conversation.get("system_prompt", "") or "")

    _step_idx = 0
    def next_step_id():
        nonlocal _step_idx
        sid = f"{createdAt_ms}-{_step_idx}"
        _step_idx += 1
        return sid

    out_msgs: List[Dict[str, Any]] = []
    msgs = conversation.get("messages", [])

    for m in msgs:
        versions = m.get("versions", [])
        if not versions:
            continue
        v0 = versions[0]
        vtype = v0.get("type")
        vrole = v0.get("role", "").lower()
        if vtype == "singleStep" and vrole == "user":
            content = v0.get("content") or []
            text = ""
            if content and isinstance(content, list) and isinstance(content[0], dict):
                text = content[0].get("text", "")
            elif isinstance(content, list) and content and isinstance(content[0], str):
                text = content[0]
            out_msgs.append(normalize_user_single_step(text or ""))
        else:
            steps = v0.get("steps") or []
            fixed_steps = []
            for s in steps:
                cont = s.get("content") or []
                text = ""
                if cont and isinstance(cont, list) and isinstance(cont[0], dict):
                    text = cont[0].get("text", "")
                elif isinstance(cont, list) and cont and isinstance(cont[0], str):
                    text = cont[0]
                text = sanitize_text(text or "")
                fixed_steps.append({
                    "type": "contentBlock",
                    "stepIdentifier": s.get("stepIdentifier") or next_step_id(),
                    "content": [ lm_text_block(text) ],
                    "defaultShouldIncludeInContext": True,
                    "shouldIncludeInContext": True,
                    "genInfo": s.get("genInfo") or minimal_gen_info()
                })
            sender_info = v0.get("senderInfo") or {"senderName": DEFAULT_MODEL_NAME}
            if not sender_info.get("senderName"):
                sender_info["senderName"] = DEFAULT_MODEL_NAME

            out_msgs.append({
                "versions": [
                    {
                        "type": "multiStep",
                        "role": "assistant",
                        "senderInfo": sender_info,
                        "steps": fixed_steps
                    }
                ],
                "currentlySelected": 0
            })

    # Ensure perChatPredictionConfig has sane defaults
    per_chat = conversation.get("perChatPredictionConfig") or {"fields": []}
    if not per_chat.get("fields"):
        per_chat = {
            "fields": [
                {"key": "llm.prediction.temperature", "value": 0.7},
                {"key": "llm.prediction.systemPrompt", "value": sys_prompt}
            ]
        }

    # Ensure lastUsedModel has identifiers
    last_used = conversation.get("lastUsedModel") or {}
    if not last_used.get("identifier"):
        last_used["identifier"] = DEFAULT_MODEL_NAME
    if not last_used.get("indexedModelIdentifier"):
        last_used["indexedModelIdentifier"] = DEFAULT_MODEL_NAME
    if "instanceLoadTimeConfig" not in last_used:
        last_used["instanceLoadTimeConfig"] = {"fields": []}
    if "instanceOperationTimeConfig" not in last_used:
        last_used["instanceOperationTimeConfig"] = {"fields": []}

    lm = {
        "name": title,
        "pinned": bool(conversation.get("pinned", False)),
        "createdAt": createdAt_ms,
        "preset": conversation.get("preset", ""),
        "tokenCount": int(conversation.get("tokenCount", 0)),
        "systemPrompt": sys_prompt,
        "messages": out_msgs,
        "usePerChatPredictionConfig": bool(conversation.get("usePerChatPredictionConfig", True)),
        "perChatPredictionConfig": per_chat,
        "clientInput": conversation.get("clientInput", ""),
        "clientInputFiles": conversation.get("clientInputFiles", []),
        "userFilesSizeBytes": int(conversation.get("userFilesSizeBytes", 0)),
        "lastUsedModel": last_used,
        "notes": conversation.get("notes", []),
        "plugins": conversation.get("plugins", []),
        "pluginConfigs": conversation.get("pluginConfigs", {}),
        "disabledPluginTools": conversation.get("disabledPluginTools", []),
        "looseFiles": conversation.get("looseFiles", [])
    }

    # Recompute token count
    approx_chars = 0
    for m in lm["messages"]:
        v = m["versions"][0]
        if v["type"] == "singleStep":
            approx_chars += len(v.get("content", [{}])[0].get("text", ""))
        else:
            approx_chars += sum(len(s.get("content", [{}])[0].get("text", "")) for s in v.get("steps", []))
    lm["tokenCount"] = max(approx_chars // 4, 0)

    if verbose:
        print(f"[normalize] {title!r}: in_msgs={len(msgs)} out_msgs={len(out_msgs)}")
    return lm


def filter_conversations(conversations: List[Dict[str, Any]], target_id: Optional[str], keywords: Optional[List[str]]) -> List[Dict[str, Any]]:
    if target_id:
        return [c for c in conversations if c.get('id') == target_id]
    if not keywords:
        return conversations
    lower_kws = [k.lower() for k in keywords]
    out: List[Dict[str, Any]] = []
    for c in conversations:
        title = (c.get('title') or c.get('name') or "").lower()
        if any(kw in title for kw in lower_kws):
            out.append(c)
            continue
        mapping = c.get('mapping') or {}
        blob = ""
        for entry in mapping.values():
            if isinstance(entry, dict):
                msg = entry.get('message')
                if isinstance(msg, dict):
                    cnt = msg.get('content')
                    if isinstance(cnt, str):
                        blob += " " + cnt.lower()
                    elif isinstance(cnt, dict) and 'parts' in cnt:
                        for p in cnt.get('parts', []):
                            if isinstance(p, str):
                                blob += " " + p.lower()
                    elif isinstance(cnt, list):
                        for p in cnt:
                            if isinstance(p, dict) and isinstance(p.get('text'), str):
                                blob += " " + p['text'].lower()
        if any(kw in blob for kw in lower_kws):
            out.append(c)
    return out

def main():
    parser = argparse.ArgumentParser(description="Export/normalize conversations to LM Studio format.")
    parser.add_argument('conversations_file', help='Path to conversations.json (array of conversations or single LM conversation)')
    parser.add_argument('--id', help='Only process this conversation ID (when input is an array)')
    parser.add_argument('--keywords', nargs='*', help='Only conversations containing these keywords (title or content)')
    parser.add_argument('--clean', action='store_true', help='Delete output directory before extracting')
    parser.add_argument('--outdir', default='lm_conversations_lmstudio', help='Output directory')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    args = parser.parse_args()

    src_path = Path(args.conversations_file)
    if not src_path.exists():
        print("Error: not found:", src_path)
        return

    try:
        data = json.loads(src_path.read_text(encoding='utf-8'))
    except Exception as e:
        print("Error reading JSON:", e)
        return

    # Determine if input is an array of conversations or a single LM-styled conversation
    if isinstance(data, list):
        conversations = filter_conversations(data, args.id, args.keywords)
    elif isinstance(data, dict):
        conversations = [data]
    else:
        print("Error: input must be a JSON array or a single conversation object.")
        return

    outdir = Path(args.outdir)
    if args.clean and outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for idx, conv in enumerate(conversations):
        has_mapping = isinstance(conv.get("mapping"), dict)
        has_messages = isinstance(conv.get("messages"), list)

        if args.verbose:
            name = conv.get("title") or conv.get("name") or ""
            print(f"[{idx+1}/{len(conversations)}] title={name!r} mapping={has_mapping} messages={has_messages}")

        # Build LM Studio object
        if has_mapping:
            lm_obj = build_from_mapping(conv, verbose=args.verbose)
        elif has_messages:
            lm_obj = normalize_existing_lm(conv, verbose=args.verbose)
        else:
            # Minimal empty conversation fallback
            lm_obj = {
                "name": conv.get("title") or conv.get("name") or "",
                "pinned": False,
                "createdAt": to_millis(conv.get("create_time") or conv.get("createdAt")),
                "preset": "",
                "tokenCount": 0,
                "systemPrompt": "",
                "messages": [],
                "usePerChatPredictionConfig": True,
                "perChatPredictionConfig": {
                    "fields": [
                        {"key": "llm.prediction.temperature", "value": 0.7},
                        {"key": "llm.prediction.systemPrompt", "value": ""}
                    ]
                },
                "clientInput": "",
                "clientInputFiles": [],
                "userFilesSizeBytes": 0,
                "lastUsedModel": {
                    "identifier": DEFAULT_MODEL_NAME,
                    "indexedModelIdentifier": DEFAULT_MODEL_NAME,
                    "instanceLoadTimeConfig": {"fields": []},
                    "instanceOperationTimeConfig": {"fields": []}
                },
                "notes": [],
                "plugins": [],
                "pluginConfigs": {},
                "disabledPluginTools": [],
                "looseFiles": []
            }

        # Ensure createdAt is an int ms
        createdAt_ms = int(lm_obj.get('createdAt') or to_millis(None))
        lm_obj['createdAt'] = createdAt_ms

        # --- Dollar-prefix folder routing ---
        # Use the *original* title to extract $tag$; then strip it from the LM title
        raw_title = (conv.get("title") or conv.get("name") or "").strip()
        folder, clean_title = parse_dollar_prefix(raw_title)
        if folder:
            folder = sanitize_folder_name(folder)
            # strip the $tag$ from what LM Studio displays
            lm_obj["name"] = clean_title
        else:
            folder = "Uncategorized"

        # Write file to <outdir>/<folder>/<createdAt>.conversation.json
        dest_dir = outdir / folder
        dest_dir.mkdir(parents=True, exist_ok=True)
        out_file = dest_dir / f"{createdAt_ms}.conversation.json"
        out_file.write_text(json.dumps(lm_obj, ensure_ascii=False, indent=2), encoding='utf-8')

        if args.verbose:
            print(f"  -> wrote {folder}/{out_file.name} (name={lm_obj['name']!r})  messages={len(lm_obj.get('messages', []))}")


if __name__ == "__main__":
    main()
