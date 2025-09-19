# Migrate ChatGPT Conversations to LM Studio

This script converts a `conversations.json` export from ChatGPT into **LM Studio–compatible** conversation files.  
Each conversation is written as `<timestamp>.conversation.json` in the LM Studio format so that they can be directly moved to the `conversations` folder of LM Studio.

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

## Instructions
1. Export from ChatGPT (ChatGPT Settings -> Data Controls -> Export data)
2. Extract archive
3. Move the `conversations.json` alongside the launch `.BAT` and `.COMMAND` files
4. Execute the launch file for your platform
5. A folder should be created in your user home directory named `lm_conversations_lmstudio` which contains your converted conversation files
6. Move the conversation files in their designated subfolder (Windows: `%USERPROFILE%/.lmstudio/conversations`, macOS: `~.lmstudio/conversations`)

## Requirements

- Python **3.12+** (tested with 3.12.2).  
- No external libraries required even though a venv is created by the launch script.

```txt
# All modules used are in the Python standard library
