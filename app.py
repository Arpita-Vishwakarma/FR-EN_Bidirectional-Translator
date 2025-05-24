from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from transformers import MarianTokenizer, MarianMTModel
import uvicorn
import torch

# Load models at startup
en_fr_model = "Helsinki-NLP/opus-mt-en-fr"
fr_en_model = "Helsinki-NLP/opus-mt-fr-en"

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

# Initialize FastAPI
app = FastAPI()

# Mount static directory for CSS/JS if needed
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Translation utility functions
def translate_text(text: str, direction: str) -> str:
    if direction == "en2fr":
        tokenizer, model = tokenizer_en2fr, model_en2fr
    else:
        tokenizer, model = tokenizer_fr2en, model_fr2en
    inputs = tokenizer(text, return_tensors="pt", padding=True)
    outputs = model.generate(**inputs, max_length=128)
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# HTML homepage with form
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        "index.html", {"request": request}
    )

# Endpoint to handle translation
@app.post("/translate", response_class=HTMLResponse)
async def translate(request: Request):
    form = await request.form()
    text = form.get("text")
    direction = form.get("direction")
    translation = translate_text(text, direction)
    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "original": text, "translated": translation, "direction": direction}
    )

# Run the application
#uvicorn app:app --reload --- using this command
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
