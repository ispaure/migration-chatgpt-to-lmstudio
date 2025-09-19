# ChatGPT → LM Studio Conversation Exporter

This script converts a `conversations.json` export from ChatGPT (ChatGPT Settings -> Data Controls -> Export data) into **LM Studio–compatible** conversation files.  
Each conversation is written as `<timestamp>.conversation.json` in the LM Studio format so that they can be directly moved to the user's LM Studio Conversations subfolder (Windows: %USERPROFILE%/.lmstudio/conversations, macOS: ~.lmstudio/conversations).

---

## Features

- ✅ Converts ChatGPT’s `mapping` structure into LM Studio’s `messages` format.
- ✅ Preserves user and assistant messages.  
- ✅ Cleans up artifacts like ` … ` and citation markers ` `.  
- ✅ Ensures unique `stepIdentifier` values for assistant steps.  
- ✅ Supports `$tag$` prefixes in titles to auto-sort into subfolders (e.g. `$tech$GPU Notes` → `tech/…` with title cleaned). These need to be added manually on ChatGPT before the `conversations.json` export.  
- ✅ No external dependencies — pure Python standard library.
- ✅ Windows and macOS support (launch_lm_export.bat / launch_lm_export.command)

---

## Requirements

- Python **3.12+** (tested with 3.12.2).  
- No external libraries required even though a venv is created by the launch script.

```txt
# All modules used are in the Python standard library
