# WriteWise AI — Writing Coach

A local-first English writing helper built from the ideas in the uploaded notebook: handwriting OCR, English writing review, improvement hints, and recurring-focus tracking.

## What is included
- A responsive website with text input and handwriting-image upload.
- Image preprocessing plus EasyOCR (English) for text recognition.
- Mistake cards with categories, excerpts, plain-language hints, recommendations, and focus-area counts.
- Optional Gemini-powered review. Without an API key, the app uses small built-in checks as an offline fallback.
- Review history stored in the browser's local storage, so a learner can see recurring categories next time on the same browser/device.
- 10 MB image upload limit and clear error messages.

## Important accuracy note
**No honest implementation can guarantee 99% recognition of every handwritten letter without a defined test dataset and measured evaluation.** Accuracy depends on handwriting style, image quality, language, and the OCR model. The confidence number shown is an approximate OCR score, not a verified accuracy rate. Always proofread OCR output. To establish a 99% target, create a labelled test set representative of the intended users, measure character error rate (CER) and word error rate (WER), and improve/test against held-out samples.

## Run in Visual Studio Code

Use Python 3.10–3.12 if possible. Open this folder in VS Code, then run these commands in its terminal.

### 1. Create and activate a virtual environment

**Windows PowerShell**
```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, use Command Prompt:
```bat
.venv\Scripts\activate.bat
```

**macOS / Linux**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

EasyOCR downloads its recognition weights on first use and may take a while. If installation is difficult, install the base app first with `pip install Flask Pillow`, then add `pip install easyocr` for image OCR.

### 2. (Optional) Enable stronger AI review
1. Create a Gemini API key from Google's AI developer tools.
2. Copy `.env.example` to `.env`.
3. Put your key in `.env`.
4. Install `python-dotenv` (`pip install python-dotenv`) and add `from dotenv import load_dotenv; load_dotenv()` near the top of `app.py`, **or** set `GEMINI_API_KEY` in the terminal environment before starting the app. Do not commit or share your key.

Windows PowerShell for the current terminal:
```powershell
$env:GEMINI_API_KEY="your-key-here"
```
macOS / Linux:
```bash
export GEMINI_API_KEY="your-key-here"
```

Without a key, text analysis still works with the built-in rule checks, but those checks are intentionally limited and are not equivalent to a full grammar model.

### 3. Start the website
```bash
python app.py
```
Open **http://127.0.0.1:5000** in your browser. Keep the terminal running while using the site. Press `Ctrl+C` to stop it.

## How history works
Mistake history is stored in browser `localStorage`, not a server database. It is private to that browser profile and is not synced between devices. Clearing browser site data or pressing **Clear history** deletes it. History stores a short text preview, word count, issue count, date, and issue categories; avoid entering sensitive personal information.

## Project structure
```text
WriteWise_AI/
├── app.py
├── requirements.txt
├── .env.example
├── README.md
├── templates/
│   └── index.html
└── static/
    ├── app.js
    └── style.css
```

## Current limitations and next improvements
- English only; EasyOCR is not specialised for every handwriting style.
- Built-in fallback catches only a few common patterns. Gemini analysis is richer but can still make mistakes.
- No claim of 99% accuracy until a representative, independently labelled test set demonstrates it.
- Next: add a labelled CER/WER evaluation pipeline, collect permissioned handwriting samples, tune preprocessing, compare OCR models, and add a teacher-reviewed correction workflow.
