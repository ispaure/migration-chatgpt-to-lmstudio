# ChatGPT → LM Studio Conversation Exporter

This script converts a `conversations.json` export from ChatGPT into **LM Studio–compatible** conversation files.  
Each conversation is written as `<timestamp>.conversation.json` in the LM Studio format so that they can be directly moved to the ~.lmstudio/conversations subfolder.

---

## Features

- ✅ Converts ChatGPT’s `mapping` structure into LM Studio’s `messages` format.  
- ✅ Preserves user and assistant messages.  
- ✅ Cleans up artifacts like ` … ` and citation markers ` `.  
- ✅ Ensures unique `stepIdentifier` values for assistant steps.  
- ✅ Supports `$tag$` prefixes in titles to auto-sort into subfolders (e.g. `$tech$GPU Notes` → `tech/…` with title cleaned). These need to be added manually on ChatGPT before the `conversations.json` export.  
- ✅ No external dependencies — pure Python standard library.

---

## Requirements

- Python **3.12+** (tested with 3.12.2).  
- No external libraries required.

`requirements.txt`:

```txt
# All modules used are in the Python standard library
