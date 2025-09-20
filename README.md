# Migrate ChatGPT Conversations to LM Studio

This script converts a `conversations.json` export from ChatGPT's website into **LM Studio–compatible** conversation files in the expected location so that they automatically appear in LM Studio alongside other conversations.

---

## Features

- ✅ Converts ChatGPT’s `mapping` structure into LM Studio’s `messages` format.
- ✅ Preserves ALL user and assistant messages.  
- ✅ Timestamps the conversation files to keep proper ordering (LM Studio orders conversation from newest created to oldest created)
- ✅ Supports `$tag$` prefixes in titles to auto-sort into subfolders (e.g. `$tech$GPU Notes` → `tech/…` with title cleaned). These need to be added manually on ChatGPT before the `conversations.json` export.
- ✅ Exports in the LM Studio conversations subfolder -- no second guessing!
- ✅ Windows and macOS support (launch_lm_export.bat / launch_lm_export.command)

---

## Instructions
1. Export data from ChatGPT (ChatGPT Settings -> Data Controls -> Export data)
2. You should get an email from ChatGPT containing your data. Download and extract the `.ZIP` file
3. Move the `conversations.json` alongside the launch files from this GIT
4. Execute the launch file for your platform (Windows: `.BAT` and macOS: `.COMMAND`)
5. The conversations are migrated to LM Studio's Conversations subfolder. Once done you can close the script window.
6. In LM Studio you will see your conversations in a `.ChatGPT Imports - Date/Time` subfolder

## Requirements
- Python **3.12+** (tested with 3.12.2).
- No external libraries required even though a venv is created by the launch script.

## Arguments
- conversations_file (required): Path to conversations.json file containing an array of conversations from ChatGPT (By default, expected alongside the launch script files)
- --id: Process only the conversation with the specified ID (when input contains an array of conversations)
- --keywords: Process only conversations containing the specified keywords in either the title or content
- --clean: Delete the output directory before processing (useful for fresh exports)
- --outdir: Specify output directory path (Default: Within the User's .lmstudio/conversations in a new subfolder -- So it should appear in LM Studio alongside other conversations with no need to move files.)
- --verbose: Enable verbose logging output


