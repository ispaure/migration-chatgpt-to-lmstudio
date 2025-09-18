import json
from pathlib import Path
from datetime import datetime
import argparse
import shutil

def sanitize_filename(filename):
    return filename.replace(' ', '_').replace('/', '_')

def assemble_conversation_json(conversation, lm_only=False):
    """
    Assemble a conversation dictionary in LM Studio format.
    If lm_only is True, only include the messages needed for LM Studio.
    """
    messages = []
    mapping = conversation.get('mapping', {})
    for msg_id, entry in mapping.items():
        if 'message' in entry and entry['message']:
            msg = entry['message']
            role = msg.get('author', {}).get('role', 'user')
            content_list = []
            if 'content' in msg:
                if isinstance(msg['content'], list):
                    for part in msg['content']:
                        if isinstance(part, dict) and 'text' in part:
                            content_list.append(part['text'])
                        elif isinstance(part, str):
                            content_list.append(part)
                elif isinstance(msg['content'], dict) and 'text' in msg['content']:
                    content_list.append(msg['content']['text'])
                elif isinstance(msg['content'], str):
                    content_list.append(msg['content'])
            if content_list:
                messages.append({
                    "id": msg_id,
                    "role": role,
                    "content": content_list
                })
    return {
        "id": conversation.get('id'),
        "title": conversation.get('title', ''),
        "create_time": conversation.get('create_time'),
        "update_time": conversation.get('update_time'),
        "mapping": mapping,
        "messages": messages
    }

def parse_conversations(conversations_file, lm_only=False, clean=False, target_id=None, keywords=None):
    # Load conversations
    with open(conversations_file, 'r', encoding='utf-8') as f:
        conversations = json.load(f)

    # Filter by ID
    if target_id:
        conversations = [conv for conv in conversations if conv.get('id') == target_id]
        if not conversations:
            print(f"No conversation found with ID: {target_id}")
            return

    # Filter by keywords in title or content
    if keywords:
        filtered = []
        for conv in conversations:
            title = (conv.get('title') or '').lower()
            content_text = ""
            mapping = conv.get('mapping', {})
            for entry in mapping.values():
                msg = entry.get('message')
                if msg:
                    c = msg.get('content')
                    if isinstance(c, str):
                        content_text += c.lower()
                    elif isinstance(c, list):
                        for part in c:
                            if isinstance(part, dict) and 'text' in part:
                                content_text += part['text'].lower()
            if any(kw.lower() in title or kw.lower() in content_text for kw in keywords):
                filtered.append(conv)
        conversations = filtered
        if not conversations:
            print(f"No conversations matched keywords: {keywords}")
            return

    output_dir = Path('lm_conversations')
    if clean and output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(exist_ok=True)

    for conversation in conversations:
        conv_json = assemble_conversation_json(conversation, lm_only=lm_only)
        # Use create_time for filename
        create_time = int(conversation.get('create_time', datetime.now().timestamp() * 1000))
        filename = output_dir / f"{create_time}.conversation.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(conv_json, f, indent=2)

        print(f"Saved conversation '{conversation.get('title', '')}' to {filename}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Parse ChatGPT conversations.json for LM Studio")
    parser.add_argument('conversations_file', help='Path to conversations.json')
    parser.add_argument('--lm-only', action='store_true', help='Only extract LM-relevant messages')
    parser.add_argument('--clean', action='store_true', help='Delete output directory before extracting')
    parser.add_argument('--id', help='Process only conversation with this ID')
    parser.add_argument('--keywords', nargs='*', help='Process only conversations containing these keywords')
    args = parser.parse_args()

    parse_conversations(
        args.conversations_file,
        lm_only=args.lm_only,
        clean=args.clean,
        target_id=args.id,
        keywords=args.keywords
    )
