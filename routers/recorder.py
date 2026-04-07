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

        prompt = """
            Você é um assistente especialista em resumir reuniões profissionais.

            Analise a transcrição abaixo e gere um resumo claro, estruturado e acionável.

            A resposta deve estar em português e seguir exatamente este formato:

            1. Resumo Geral (até 5 linhas)
            - Explique de forma objetiva o que foi discutido.

            2. Principais Pontos
            - Liste os tópicos mais importantes discutidos na reunião.

            3. Decisões Tomadas
            - Liste todas as decisões definidas durante a reunião.

            4. Ações e Responsáveis
            - Liste tarefas, responsáveis e prazos (se mencionados).
            - Use o formato:
            - [Responsável] → tarefa (prazo)

            5. Riscos ou Pendências
            - Liste dúvidas, problemas ou pontos em aberto.

            6. Insights Relevantes (opcional)
            - Observações importantes que podem ajudar na tomada de decisão.

            Regras:
            - Seja direto e evite redundâncias.
            - Não invente informações.
            - Se alguma seção não tiver conteúdo, escreva "Não identificado".
            - Use linguagem profissional, mas simples.
        """

        summary = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um especialista em resumir reuniões corporativas com foco em clareza, objetividade e geração de ações."
                },
                {
                    "role": "user",
                    "content": prompt + "\n\nTranscrição:" + text
                }
            ]
        )

        return {
            "transcription": text,
            "summary": summary.choices[0].message.content,
            "duration": transcription.audio_duration
        }

    except Exception as e:
        logger.error(e)
        return {"error": str(e)}

