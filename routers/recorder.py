import os
import logging
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, UploadFile, File
from pydantic import BaseModel
from database import SessionLocal
from openai import OpenAI
from sqlalchemy.orm import Session
from models import Record
import assemblyai as aai

aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(
    prefix="/recorder",
    tags=["Recorder"]
)

load_dotenv()

groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)


class ChatMessage(BaseModel):
    message: str


@router.post("/audio")
async def upload_audio(
    file: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    try:
        file_location = f"temp_{file.filename}"

        with open(file_location, "wb") as f:
            f.write(await file.read())

        with open(file_location, "rb") as audio:
            transcriber = aai.Transcriber()

            config = aai.TranscriptionConfig(
                speech_models=["universal"],
                speaker_labels=True
            )

            transcription = transcriber.transcribe(file_location, config=config)

        text = transcription.text

        summary = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "Resuma reuniões de forma clara e objetiva."
                },
                {
                    "role": "user",
                    "content": f"Resuma o seguinte conteúdo:\n\n{text}"
                }
            ]
        )

        record_resume = Record(
            resume=summary.choices[0].message.content
        )

        db.add(record_resume)
        db.commit()
        db.refresh(record_resume)

        return {
            "transcription": text,
            "summary": summary.choices[0].message.content
        }

    except Exception as e:
        logger.error(e)
        return {"error": str(e)}

