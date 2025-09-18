#!/usr/bin/env python3
"""
lm_export.py

Reads a ChatGPT-style conversations.json (array of conversations) and writes
LM Studio-compatible conversation files named <createdAt_ms>.conversation.json.

Options:
  --id <conversation_id>       Process only that conversation (optional)
  --keywords <kw1> <kw2> ...   Process only conversations matching any keyword
  --clean                      Remove output directory before running
  --lm-only                    Write LM Studio files only (no other extraction)
  --outdir <path>              Output directory (default: lm_conversations_lmstudio)
"""
import json
from pathlib import Path
import argparse
import shutil
from datetime import datetime
from typing import Any, Dict, List, Tuple, Optional

def to_millis(ts: Optional[float]) -> int:
    """Convert timestamp in seconds (float) or milliseconds (int/float) to ms int."""
    if ts is None:
        return int(round(datetime.now().timestamp() * 1000))
    try:
        tsf = float(ts)
    except Exception:
        return int(round(datetime.now().timestamp() * 1000))
    # if clearly already in milliseconds (big number), keep as int
    if tsf > 1e12:
        return int(tsf)
    return int(round(tsf * 1000))

def text_from_content_obj(content_obj: Any) -> str:
    """
    Extract plain text from a ChatGPT-style content object.
    Handles:
      - {"content_type":"text","parts":["...","..."]}
      - {"text":"..."}
      - list of dicts with 'text'
      - a simple string
    Returns a joined string (parts separated by two newlines).
    """
    if content_obj is None:
        return ""
    if isinstance(content_obj, str):
        return content_obj.strip()
    if isinstance(content_obj, dict):
        # Common ChatGPT shape
        if 'parts' in content_obj and isinstance(content_obj['parts'], list):
            parts = [p for p in content_obj['parts'] if isinstance(p, str) and p.strip() != ""]
            return "\n\n".join([p.strip() for p in parts])
        if 'text' in content_obj and isinstance(content_obj['text'], str):
            return content_obj['text'].strip()
        # Generic recursive collection
        collected = []
        def collect(obj):
            if isinstance(obj, str):
                if obj.strip():
                    collected.append(obj.strip())
            elif isinstance(obj, dict):
                for v in obj.values():
                    collect(v)
            elif isinstance(obj, list):
                for it in obj:
                    collect(it)
        collect(content_obj)
        return "\n\n".join(collected)
    if isinstance(content_obj, list):
        texts = []
        for part in content_obj:
            if isinstance(part, dict) and 'text' in part and isinstance(part['text'], str):
                if part['text'].strip():
                    texts.append(part['text'].strip())
            elif isinstance(part, str):
                if part.strip():
                    texts.append(part.strip())
        return "\n\n".join(texts)
    return ""

def build_lmstudio_object(conversation: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert a single conversation dict (with 'mapping') into LM Studio JSON shape.
    """
    title = conversation.get('title') or conversation.get('name') or ""
    createdAt_ms = to_millis(conversation.get('create_time') or conversation.get('createdAt'))

    lm = {
        "name": title,
        "pinned": False,
        "createdAt": createdAt_ms,
        "preset": "",
        "tokenCount": 0,
        "systemPrompt": conversation.get('system_prompt', "") or "",
        "messages": [],
        "usePerChatPredictionConfig": True,
        "perChatPredictionConfig": {"fields": []},
        "clientInput": "",
        "clientInputFiles": [],
        "userFilesSizeBytes": 0,
        "lastUsedModel": conversation.get('lastUsedModel', {}),
        "notes": conversation.get('notes', []),
        "plugins": conversation.get('plugins', []),
        "pluginConfigs": conversation.get('pluginConfigs', {}),
        "disabledPluginTools": conversation.get('disabledPluginTools', []),
        "looseFiles": conversation.get('looseFiles', [])
    }

    mapping = conversation.get('mapping') or {}
    items: List[Tuple[int, str, Dict[str, Any], str]] = []  # (ts_ms, msg_id, msg_obj, text)

    # collect visible messages with text and timestamp
    for msg_id, entry in mapping.items():
        if not isinstance(entry, dict):
            continue
        msg = entry.get('message')
        if not isinstance(msg, dict):
            continue
        metadata = msg.get('metadata') or {}
        # skip visually hidden messages
        if metadata.get('is_visually_hidden_from_conversation'):
            continue
        content_obj = msg.get('content')
        text = text_from_content_obj(content_obj)
        if not text.strip():
            # skip empty-content messages
            continue
        ct = msg.get('create_time') or 0
        ts_ms = to_millis(ct)
        items.append((ts_ms, msg_id, msg, text))

    # sort messages by timestamp ascending
    items.sort(key=lambda t: (t[0] if t[0] else 0, t[1]))

    # build LM-style messages
    for ts_ms, msg_id, msg, text in items:
        role = (msg.get('author') or {}).get('role', 'user')
        role = role.lower() if isinstance(role, str) else 'user'
        if role == 'user':
            versions = [
                {
                    "type": "singleStep",
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": text
                        }
                    ]
                }
            ]
            lm_msg = {"versions": versions, "currentlySelected": 0}
            lm["messages"].append(lm_msg)
        else:
            # assistant or other roles
            step = {
                "type": "contentBlock",
                "stepIdentifier": f"{ts_ms}-0",
                "content": [
                    {
                        "type": "text",
                        "text": text
                    }
                ],
                "defaultShouldIncludeInContext": True,
                "shouldIncludeInContext": True
            }
            versions = [
                {
                    "type": "multiStep",
                    "role": "assistant",
                    "steps": [step],
                    "senderInfo": {"senderName": (msg.get('metadata') or {}).get('model_slug') or ""}
                }
            ]
            lm_msg = {"versions": versions, "currentlySelected": 0}
            lm["messages"].append(lm_msg)

    # tokenCount estimate (rough)
    approx_tokens = sum(len(m['versions'][0].get('content', [{}])[0].get('text', "")) for m in lm["messages"] if m.get('versions'))
    lm['tokenCount'] = max(approx_tokens // 4, 0)

    return lm

def filter_conversations(conversations: List[Dict[str, Any]], target_id: Optional[str], keywords: Optional[List[str]]) -> List[Dict[str, Any]]:
    if target_id:
        filtered = [c for c in conversations if c.get('id') == target_id]
        return filtered
    if not keywords:
        return conversations
    lower_kws = [k.lower() for k in keywords]
    out = []
    for c in conversations:
        title = (c.get('title') or "").lower()
        if any(kw in title for kw in lower_kws):
            out.append(c)
            continue
        # search content quickly
        mapping = c.get('mapping') or {}
        concat = ""
        for entry in mapping.values():
            if isinstance(entry, dict):
                msg = entry.get('message')
                if isinstance(msg, dict):
                    content = msg.get('content')
                    if isinstance(content, str):
                        concat += " " + content.lower()
                    elif isinstance(content, dict) and 'parts' in content:
                        for p in content.get('parts', []):
                            if isinstance(p, str):
                                concat += " " + p.lower()
                    elif isinstance(content, list):
                        for p in content:
                            if isinstance(p, dict) and 'text' in p:
                                concat += " " + p.get('text', "").lower()
        if any(kw in concat for kw in lower_kws):
            out.append(c)
    return out

def main():
    parser = argparse.ArgumentParser(description="Export conversations.json to LM Studio formatted files.")
    parser.add_argument('conversations_file', help='Path to conversations.json (array of conversations)')
    parser.add_argument('--id', help='Process only conversation with this ID')
    parser.add_argument('--keywords', nargs='*', help='Process only conversations matching these keywords (title or content)')
    parser.add_argument('--clean', action='store_true', help='Delete output directory before extracting')
    parser.add_argument('--lm-only', action='store_true', help='Write only LM Studio JSON output (default behavior here)')
    parser.add_argument('--outdir', default='lm_conversations_lmstudio', help='Output directory')
    args = parser.parse_args()

    conversations_path = Path(args.conversations_file)
    if not conversations_path.exists():
        print("Error: conversations.json not found at", conversations_path)
        return

    with open(conversations_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if not isinstance(data, list):
            print("Error: expected conversations.json to be an array of conversation objects.")
            return
        conversations = data

    conversations = filter_conversations(conversations, args.id, args.keywords)

    outdir = Path(args.outdir)
    if args.clean and outdir.exists():
        shutil.rmtree(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    for conv in conversations:
        lm_obj = build_lmstudio_object(conv)
        # filename should be createdAt ms per LM Studio convention
        createdAt = lm_obj.get('createdAt') or lm_obj.get('createdAt', to_millis(None))
        filename = outdir / f"{int(createdAt)}.conversation.json"
        filename.write_text(json.dumps(lm_obj, ensure_ascii=False, indent=2), encoding='utf-8')
        print("Wrote", filename, "(", lm_obj.get('name', '') , ")")

if __name__ == "__main__":
    main()
