import os
import re
from collections import Counter
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
ALLOWED = {"png", "jpg", "jpeg", "webp", "bmp", "tif", "tiff"}

def local_review(text):
    """Small offline fallback: useful starter checks, not a full grammar engine."""
    text = (text or "").strip()
    issues = []
    if not text:
        return {"corrected": "", "issues": [], "recommendations": ["Enter or upload some writing first."], "focus": [], "summary": "No text to analyse."}
    sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text) if s.strip()]
    words = re.findall(r"\b[\w']+\b", text)
    add = lambda category, excerpt, message, hint, severity="medium": issues.append({
        "category": category, "excerpt": excerpt, "message": message, "hint": hint, "severity": severity
    })
    if text[0].islower() and text[0].isalpha():
        add("Capitalization", text[:min(35,len(text))], "The first word may need a capital letter.", "Start a sentence with a capital letter.")
    for m in re.finditer(r"\bi\b", text):
        add("Capitalization", m.group(), "The pronoun “I” should be capitalized.", "Write “I”, not “i”.")
    for phrase, replacement, hint in [
        (r"\bhe don't\b", "he doesn't", "Use “doesn't” with he/she/it."),
        (r"\bshe don't\b", "she doesn't", "Use “doesn't” with he/she/it."),
        (r"\bit don't\b", "it doesn't", "Use “doesn't” with he/she/it."),
        (r"\bhe go\b", "he goes", "In the present simple, add -s/-es for he, she, or it."),
        (r"\bshe go\b", "she goes", "In the present simple, add -s/-es for he, she, or it."),
        (r"\bhe have\b", "he has", "Use “has” with he/she/it."),
        (r"\bshe have\b", "she has", "Use “has” with he/she/it."),
        (r"\bmore better\b", "better", "Avoid double comparatives: use “better”."),
        (r"\bvery unique\b", "unique", "“Unique” already means one of a kind."),
        (r"\ba ([aeiou])", r"an \1", "Use “an” before a vowel sound (check exceptions)."),
        (r"\ban ([^aeiou\s])", r"a \1", "Use “a” before a consonant sound (check exceptions)."),
    ]:
        for m in re.finditer(phrase, text, flags=re.I):
            add("Grammar", m.group(), f"This phrase may be incorrect; consider “{replacement}”.", hint)
    if re.search(r"[.!?]\s+[a-z]", text):
        add("Punctuation", "sentence boundary", "A sentence after a full stop may start with a lowercase letter.", "Start each new sentence with a capital letter.")
    if text and text[-1] not in ".!?":
        add("Punctuation", text[-min(25,len(text)):], "The paragraph may need ending punctuation.", "Finish the final sentence with a full stop, question mark, or exclamation mark.")
    repeated = re.findall(r"\b([A-Za-z']+)\s+\1\b", text, flags=re.I)
    for w in repeated:
        add("Word choice", w+" "+w, f"The word “{w}” appears twice in a row.", "Remove the accidental repeated word.")
    if len(words) > 0 and len(words) < 35:
        rec = ["Develop your main idea with one or two supporting details.", "Add a clear example or explanation where it would help the reader."]
    else:
        rec = ["Check that each paragraph has one clear main idea.", "Use linking words such as “because”, “however”, and “for example” where appropriate."]
    if not any(i["category"]=="Grammar" for i in issues):
        rec.insert(0, "Read the paragraph aloud and check that each sentence sounds natural.")
    focus = Counter(i["category"] for i in issues)
    return {"corrected": text, "issues": issues, "recommendations": rec, "focus": [{"name":k,"count":v} for k,v in focus.most_common()], "summary": f"Found {len(issues)} possible issue(s) using the built-in checks. Review suggestions carefully; they are not guaranteed to be correct."}

def ai_review(text):
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return local_review(text)
    try:
        from google import genai
        client = genai.Client(api_key=key)
        prompt = """You are a supportive English writing tutor for a Grade 7 student. Analyse the student's ORIGINAL writing; do not rewrite it into a different meaning or invent facts. Return ONLY valid JSON with keys: corrected (string, minimal corrections only), issues (array of objects with category, excerpt, message, hint, severity), recommendations (array of short strings), focus (array of objects with name,count), summary (string). Identify likely grammar, spelling, punctuation, capitalization, vocabulary, and organization issues. Each hint should teach the rule simply. If uncertain, say so instead of claiming an error. Avoid shaming. Keep language age-appropriate.
STUDENT TEXT:
""" + text
        response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        raw = response.text.strip()
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw)
        data = __import__("json").loads(raw)
        for k, default in [("corrected",text),("issues",[]),("recommendations",[]),("focus",[]),("summary","Analysis complete.")]:
            data.setdefault(k, default)
        return data
    except Exception as e:
        result = local_review(text)
        result["summary"] += " AI service was unavailable, so offline checks were used."
        return result

def extract_text(file_storage):
    filename = secure_filename(file_storage.filename or "")
    ext = filename.rsplit(".",1)[-1].lower() if "." in filename else ""
    if ext not in ALLOWED:
        raise ValueError("Please upload a PNG, JPG, WEBP, BMP, or TIFF image.")
    try:
        from PIL import Image, ImageOps, ImageEnhance, ImageFilter
        import io
        image = Image.open(file_storage.stream).convert("RGB")
        image = ImageOps.exif_transpose(image)
        # Upscale small photos and lightly improve contrast for OCR.
        if image.width < 1200:
            scale = min(2.5, 1200 / max(image.width, 1))
            image = image.resize((int(image.width*scale), int(image.height*scale)))
        image = ImageEnhance.Contrast(image).enhance(1.25)
        image = ImageEnhance.Sharpness(image).enhance(1.3)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
    except Exception:
        raise ValueError("The image could not be opened. Try a clear PNG or JPG image.")
    # EasyOCR can read printed and many handwritten samples, but accuracy varies.
    try:
        import easyocr
        import numpy as np
        reader = easyocr.Reader(["en"], gpu=False)
        result = reader.readtext(np.array(image), detail=1, paragraph=False)
        result.sort(key=lambda item: (int(item[0][0][1]//25), item[0][0][0]))
        text = "\n".join(str(item[1]).strip() for item in result if str(item[1]).strip())
        confidence = round(sum(float(item[2]) for item in result)/len(result)*100) if result else 0
        if not text:
            raise ValueError("No text was detected. Try a brighter, sharper image with the page filling the frame.")
        return text, confidence
    except ImportError:
        raise RuntimeError("Handwriting OCR is not installed yet. In the VS Code terminal run: pip install easyocr")
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError("OCR could not read this image. Try a brighter, straight-on photo with dark writing on plain paper.")

@app.get("/")
def index():
    return render_template("index.html")

@app.post("/api/analyze")
def analyze():
    payload = request.get_json(silent=True) or {}
    text = str(payload.get("text", ""))[:20000]
    if not text.strip():
        return jsonify({"error":"Please enter some writing to analyse."}), 400
    return jsonify(ai_review(text))

@app.post("/api/ocr")
def ocr():
    if "image" not in request.files:
        return jsonify({"error":"Choose an image first."}), 400
    try:
        text, confidence = extract_text(request.files["image"])
        return jsonify({"text":text, "confidence":confidence})
    except (ValueError, RuntimeError) as e:
        return jsonify({"error":str(e)}), 400

@app.errorhandler(413)
def too_large(_):
    return jsonify({"error":"Image is too large. Please use an image under 10 MB."}), 413

if __name__ == "__main__":
    app.run(debug=True, port=int(os.getenv("PORT", "5000")))
