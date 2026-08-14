# Work Order Traveler → Excel Automation

Windows background automation: watches a `data/` folder, sends new work order
traveler photos to Google Gemini (vision), and appends one row per photo to
`output/work_orders.xlsx`. Processed photos move to `data/processed/`;
photos Gemini can't read move to `data/needs_review/`.

## What you need

- Python 3.9+ installed from [python.org](https://www.python.org/downloads/)
  (tick **"Add Python to PATH"** during install)
- A Google Gemini API key from https://aistudio.google.com/apikey
- Internet access on the machine

## 1. Install the requirements

Open a **Command Prompt**, then:

```
cd %USERPROFILE%\Desktop\work_order_automation
pip install -r requirements.txt
```

## 2. Set your API key (one time)

```
setx GEMINI_API_KEY "your-key-here"
```

**Close and reopen the Command Prompt** (or the window used to start the
watcher) after running `setx`, otherwise the key won't be picked up.

## 3. Start the watcher

Double-click **`run.bat`** in this folder. A console window stays open showing
each photo being processed. Logs are also written to `automation.log`.

To stop it, press `Ctrl+C` in the window.

## 4. Run automatically on Windows startup

1. Press `Win + R`, type `shell:startup`, press Enter.
2. Right-click in that folder → **New → Shortcut**.
3. For the location, paste:
   ```
   C:\Users\Devendra\Desktop\work_order_automation\run.bat
   ```
4. Click **Finish**. The watcher will now start automatically every time you log in.

A console window will appear on every boot — that's normal and expected.

## Daily use

1. Make sure the watcher is running (the console window is open).
2. Drop the traveler photos into the `data/` folder.
3. Watch the console: `[success] photo.jpg: Work Order 123 added to Excel`.
4. Photos that couldn't be read land in `data/needs_review/` — check those
   manually with the original paperwork.

## Excel file notes

- The file is created automatically at `output/work_orders.xlsx` with headers
  `Sr No | Work Order | Item Code | Description | Qty | Cat | Status`.
- **Sr No** auto-continues from the last row.
- If the file is open in Excel, the script waits a few seconds, then moves the
  photo to `needs_review/` and tells you to close the file and re-drop the photo.
- Rows are append-only; existing rows are never edited.

## Troubleshooting

| Problem | Fix |
|---|---|
| "GEMINI_API_KEY is not set" | Run `setx GEMINI_API_KEY "key"`, close and reopen the window, restart `run.bat` |
| "Dependencies are missing" | Run `pip install -r requirements.txt` |
| "Excel file is still locked" | Close the file in Excel, drop the photo again |
| Nothing happens after dropping a photo | Check `automation.log`; photos in `data/needs_review/` were rejected — check them manually |
