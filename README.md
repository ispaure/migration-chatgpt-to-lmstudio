# Migrate ChatGPT Conversations to LM Studio

This script simplifies the process of migrating all your ChatGPT conversations into LM Studio. It takes a single `conversations.json` file, which contains an array of all your ChatGPT conversations, and splits it into individual conversation files that are fully compatible with LM Studio. Each file is formatted to meet LM Studio's specific requirements, ensuring a seamless transition.

The converted conversation files are automatically placed in the user's LM Studio conversations directory, ensuring they appear immediately within the application.

---
## Features

-  **✅ Converts ChatGPT’s `conversations.json` Structure**
    - The script processes a large `conversations.json` file, which is an array of all your ChatGPT conversations.
    - Each conversation within this JSON structure is transformed into a separate, individual conversation file that adheres to the `messages` format required by LM Studio.
- **✅ Preserves ALL User and Assistant Messages**
    - Every message exchanged between you and ChatGPT, whether from the user or assistant side, is meticulously preserved during the conversion process.
    - This guarantees that no part of your conversation history is lost in the transition.
- **✅ Maintains Correct Order with Timestamps**
    - Each converted conversation file is named in the format expected by LM Studio, such as `1758392316161.conversation.json`, where the numeric prefix represents a timestamp.
    - Additionally, the file’s metadata—specifically its creation and modification times—is timestamped. This ensures that conversations are correctly ordered in LM Studio, with the newest ones appearing first.
- **✅ Supports `$tag$` Prefixes for Auto-Sorting**
    - You can use `$tag$` prefixes in the titles of your ChatGPT conversations to automatically sort them into subfolders within LM Studio.
    - For example, a conversation titled `$tech$GPU Notes` will be placed in the `tech/` subfolder with a cleaned title of `GPU Notes`.
    - Note: These dollar-sign tags need to be added manually in ChatGPT before exporting the `conversations.json` file.
- **✅ Cross-Platform Support**
    - The script is designed to work seamlessly on both Windows (`launch_migration.BAT`) and macOS (`launch_migration.COMMAND`) platforms.

---
## Instructions

1. **Export Data from ChatGPT**
    - On the [ChatGPT Website](http://chat.openai.com), navigate to `ChatGPT Settings` → `Data Controls` and select Export Data.
2. **Download and Extract the ZIP File**
    - You will receive an email from ChatGPT with a link containing your data. Download and extract the `.ZIP` file.
3. **Prepare for Conversion**
    - Move the `conversations.json` file from the extracted folder to the migration scripts' directory, alongside the launch `.BAT` and `.COMMAND` files.
4. **Run the Conversion Script**
    - Execute the appropriate launch file for your platform:
        - **Windows**: Double-click `run_migration.BAT` file.
        - **macOS**: Double-click the `run_migration.COMMAND` file. If the command file refuses to execute, open a terminal window and run `chmod +x <command-file-path>`.
    - The script will automatically migrate your conversations to LM Studio's `conversations` subfolder, which is typically located in the user's home directory at `.lmstudio/conversations`. If you have redirected this location using the `.lmstudio-home-pointer` file, the script will handle that as well.
    - Once the conversion is complete, you can close the script window.
6. **View Your Conversations in LM Studio**
    - Open LM Studio, and you will find all your migrated conversations organized under a `ChatGPT Imports - <DateTime>` subfolder.

---
## Requirements

- Python **3.12+** (tested with 3.12.2).
- No external libraries are required, as all modules used are in the Python standard library.

---
## Known Limitations

- The tool currently does not support integrating files, images, videos or other non-text elements from ChatGPT conversations into LM Studio because the software does not support these features.

---
## License

This project is licensed under the MIT License - see the `LICENSE.MD` file for details.

---
## Example Output

After running the script, you should see a directory structure similar to this:

```
📂 User Directory
└── 📂 .lmstudio
    └── 📂 conversations
        └── 📂 ChatGPT Imports - 2025-09-21 (11:54:02)
            ├── 📂 tech
            │   └── 📄 1758392316161.conversation.json
            └── 📂 Uncategorized
                ├── 📄 1758392316000.conversation.json
                └── 📄 1758392316001.conversation.json
```
