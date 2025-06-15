from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from transformers import MarianTokenizer, MarianMTModel, pipeline
import uvicorn
import torch
import re
import json
from datetime import datetime
from typing import Dict, List, Optional
import asyncio
from pydantic import BaseModel
import speech_recognition as sr
import pyttsx3
import io
import base64
from langdetect import detect
import threading
import queue

# Pydantic models for API
class TranslationRequest(BaseModel):
    text: str
    direction: str
    domain: Optional[str] = "general"
    tone: Optional[str] = "neutral"
    explain: Optional[bool] = False

class VoiceRequest(BaseModel):
    audio_data: str
    direction: str

# Load models at startup
en_fr_model = "Helsinki-NLP/opus-mt-en-fr"
fr_en_model = "Helsinki-NLP/opus-mt-fr-en"

# Load translation models
tokenizer_en2fr = MarianTokenizer.from_pretrained(en_fr_model)
model_en2fr = MarianMTModel.from_pretrained(
    en_fr_model,
    low_cpu_mem_usage=True,
    torch_dtype=torch.float32
)

tokenizer_fr2en = MarianTokenizer.from_pretrained(fr_en_model)
model_fr2en = MarianMTModel.from_pretrained(
    fr_en_model,
    low_cpu_mem_usage=True,
    torch_dtype=torch.float32
)

# Load sentiment analysis model for tone detection
sentiment_analyzer = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment-latest")

# Initialize FastAPI
app = FastAPI(title="NeoTranslate Pro", description="Advanced AI-Powered Translation Service")

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Translation history storage (in production, use a database)
translation_history = []

# Domain-specific vocabularies
DOMAIN_VOCABULARIES = {
    "legal": {
        "contract": "contrat",
        "agreement": "accord",
        "liability": "responsabilité",
        "jurisdiction": "juridiction"
    },
    "medical": {
        "diagnosis": "diagnostic",
        "treatment": "traitement",
        "symptoms": "symptômes",
        "prescription": "ordonnance"
    },
    "business": {
        "revenue": "chiffre d'affaires",
        "stakeholder": "partie prenante",
        "merger": "fusion",
        "acquisition": "acquisition"
    },
    "academic": {
        "research": "recherche",
        "methodology": "méthodologie",
        "hypothesis": "hypothèse",
        "conclusion": "conclusion"
    }
}

# Tone adjustments
TONE_ADJUSTMENTS = {
    "formal": {
        "you": "vous",
        "hi": "bonjour",
        "thanks": "je vous remercie"
    },
    "casual": {
        "you": "tu",
        "hi": "salut",
        "thanks": "merci"
    }
}

def detect_tone(text: str) -> str:
    """Detect the tone of the input text"""
    try:
        result = sentiment_analyzer(text)[0]
        if result['label'] == 'LABEL_2':  # Positive
            return "friendly"
        elif result['label'] == 'LABEL_0':  # Negative
            return "serious"
        else:
            return "neutral"
    except:
        return "neutral"

def apply_domain_vocabulary(text: str, translation: str, domain: str, direction: str) -> str:
    """Apply domain-specific vocabulary corrections"""
    if domain not in DOMAIN_VOCABULARIES:
        return translation
    
    vocab = DOMAIN_VOCABULARIES[domain]
    
    if direction == "en2fr":
        for en_term, fr_term in vocab.items():
            if en_term.lower() in text.lower():
                translation = re.sub(
                    r'\b' + re.escape(en_term) + r'\b', 
                    fr_term, 
                    translation, 
                    flags=re.IGNORECASE
                )
    else:
        for en_term, fr_term in vocab.items():
            if fr_term.lower() in text.lower():
                translation = re.sub(
                    r'\b' + re.escape(fr_term) + r'\b', 
                    en_term, 
                    translation, 
                    flags=re.IGNORECASE
                )
    
    return translation

def calculate_confidence(text: str, translation: str) -> float:
    """Calculate translation confidence score"""
    # Simple confidence calculation based on text length and complexity
    base_confidence = 0.85
    
    # Adjust based on text length
    if len(text.split()) > 20:
        base_confidence -= 0.1
    
    # Adjust based on special characters or numbers
    if re.search(r'[^\w\s]', text):
        base_confidence -= 0.05
    
    return max(0.6, min(0.99, base_confidence))

def generate_alternatives(text: str, direction: str, num_alternatives: int = 2) -> List[str]:
    """Generate alternative translations"""
    alternatives = []
    
    # Simple approach: modify the input slightly and retranslate
    variations = [
        text.replace('.', ''),
        text.replace(',', ''),
        text.strip()
    ]
    
    for variation in variations[:num_alternatives]:
        if variation != text:
            alt_translation = translate_text(variation, direction)
            if alt_translation not in alternatives:
                alternatives.append(alt_translation)
    
    return alternatives[:num_alternatives]

def explain_translation(original: str, translation: str, direction: str) -> Dict:
    """Generate explanation for the translation"""
    explanation = {
        "grammar_notes": [],
        "vocabulary_notes": [],
        "cultural_notes": []
    }
    
    # Simple grammar explanations
    if direction == "en2fr":
        if "the" in original.lower():
            explanation["grammar_notes"].append("'The' translates to 'le/la/les' depending on gender and number")
        if any(word in original.lower() for word in ["you", "your"]):
            explanation["grammar_notes"].append("French has formal (vous) and informal (tu) forms of 'you'")
    else:
        if any(word in original.lower() for word in ["vous", "tu"]):
            explanation["grammar_notes"].append("'Vous' is formal, 'tu' is informal - both translate to 'you' in English")
    
    # Vocabulary notes
    complex_words = [word for word in original.split() if len(word) > 8]
    if complex_words:
        explanation["vocabulary_notes"].append(f"Complex terms: {', '.join(complex_words[:3])}")
    
    return explanation

def translate_text(text: str, direction: str, domain: str = "general", tone: str = "neutral") -> str:
    """Enhanced translation with domain and tone awareness"""
    if direction == "en2fr":
        tokenizer, model = tokenizer_en2fr, model_en2fr
    else:
        tokenizer, model = tokenizer_fr2en, model_fr2en
    
    # Preprocess text based on tone
    processed_text = text
    
    inputs = tokenizer(processed_text, return_tensors="pt", padding=True)
    outputs = model.generate(**inputs, max_length=128, num_beams=4, early_stopping=True)
    translation = tokenizer.decode(outputs[0], skip_special_tokens=True)
    
    # Apply domain-specific vocabulary
    translation = apply_domain_vocabulary(text, translation, domain, direction)
    
    return translation

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/translate")
async def api_translate(request: TranslationRequest):
    """Advanced translation API endpoint"""
    try:
        # Detect input language if not specified
        detected_lang = detect(request.text)
        
        # Perform translation
        translation = translate_text(
            request.text, 
            request.direction, 
            request.domain, 
            request.tone
        )
        
        # Calculate confidence
        confidence = calculate_confidence(request.text, translation)
        
        # Generate alternatives
        alternatives = generate_alternatives(request.text, request.direction)
        
        # Generate explanation if requested
        explanation = None
        if request.explain:
            explanation = explain_translation(request.text, translation, request.direction)
        
        # Detect tone
        detected_tone = detect_tone(request.text)
        
        # Store in history
        history_entry = {
            "id": len(translation_history) + 1,
            "timestamp": datetime.now().isoformat(),
            "original": request.text,
            "translation": translation,
            "direction": request.direction,
            "domain": request.domain,
            "confidence": confidence,
            "detected_language": detected_lang,
            "detected_tone": detected_tone
        }
        translation_history.append(history_entry)
        
        return {
            "success": True,
            "translation": translation,
            "confidence": confidence,
            "alternatives": alternatives,
            "explanation": explanation,
            "detected_language": detected_lang,
            "detected_tone": detected_tone,
            "word_count": len(request.text.split()),
            "character_count": len(request.text)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/voice-translate")
async def voice_translate(request: VoiceRequest):
    """Voice translation endpoint"""
    try:
        # Decode base64 audio data
        audio_data = base64.b64decode(request.audio_data)
        
        # Initialize speech recognition
        r = sr.Recognizer()
        
        # Convert audio data to text
        with sr.AudioFile(io.BytesIO(audio_data)) as source:
            audio = r.record(source)
            text = r.recognize_google(audio, language='en-US' if request.direction == 'en2fr' else 'fr-FR')
        
        # Translate the recognized text
        translation = translate_text(text, request.direction)
        
        return {
            "success": True,
            "recognized_text": text,
            "translation": translation,
            "confidence": calculate_confidence(text, translation)
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/history")
async def get_history():
    """Get translation history"""
    return {"history": translation_history[-20:]}  # Return last 20 translations

@app.post("/api/text-to-speech")
async def text_to_speech(request: dict):
    """Convert text to speech"""
    try:
        text = request.get("text", "")
        language = request.get("language", "en")
        
        # Initialize TTS engine
        engine = pyttsx3.init()
        
        # Set language-specific voice
        voices = engine.getProperty('voices')
        for voice in voices:
            if language == "fr" and "french" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
            elif language == "en" and "english" in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        
        # Generate speech
        engine.save_to_file(text, 'temp_audio.wav')
        engine.runAndWait()
        
        # Read and encode audio file
        with open('temp_audio.wav', 'rb') as audio_file:
            audio_data = base64.b64encode(audio_file.read()).decode()
        
        return {"success": True, "audio_data": audio_data}
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/domains")
async def get_domains():
    """Get available translation domains"""
    return {
        "domains": [
            {"id": "general", "name": "General", "description": "General purpose translation"},
            {"id": "legal", "name": "Legal", "description": "Legal documents and contracts"},
            {"id": "medical", "name": "Medical", "description": "Medical and healthcare texts"},
            {"id": "business", "name": "Business", "description": "Business and corporate communications"},
            {"id": "academic", "name": "Academic", "description": "Academic and research papers"}
        ]
    }

# Legacy endpoint for form submission
@app.post("/translate", response_class=HTMLResponse)
async def translate(request: Request):
    form = await request.form()
    text = form.get("text")
    direction = form.get("direction")
    domain = form.get("domain", "general")
    
    translation = translate_text(text, direction, domain)
    confidence = calculate_confidence(text, translation)
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "original": text, 
            "translated": translation, 
            "direction": direction,
            "confidence": confidence
        }
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
    
#uvicorn main:app --reload or uvicorn app:app --reload --host 0.0.0.0 --port 8000, access it on http://localhost:8000/

