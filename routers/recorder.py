import os
import logging
import shutil
import tempfile

from dotenv import load_dotenv
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel
from openai import OpenAI
import assemblyai as aai

# Load env
load_dotenv()

# Config APIs
aai.settings.api_key = os.getenv("ASSEMBLY_API_KEY")

groq_client = OpenAI(
    api_key=os.getenv("GROQ_API_KEY"),
    base_url="https://api.groq.com/openai/v1"
)

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Router
router = APIRouter(
    prefix="/recorder",
    tags=["Recorder"]
)

class ChatMessage(BaseModel):
    message: str


@router.post("/audio")
async def upload_audio(
    file: UploadFile = File(...)
):
    file_location = None

    try:
        logger.info("📥 Recebendo arquivo de áudio...")

        # ✅ Salvar arquivo de forma segura (stream, sem estourar memória)
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            shutil.copyfileobj(file.file, tmp)
            file_location = tmp.name

        logger.info(f"📁 Arquivo salvo em: {file_location}")

        # ✅ Transcrição
        transcriber = aai.Transcriber()

        config = aai.TranscriptionConfig(
            speech_models=["universal"],
            speaker_labels=True
        )

        logger.info("🧠 Iniciando transcrição...")
        transcription = transcriber.transcribe(file_location, config=config)

        if not transcription or not transcription.text:
            raise HTTPException(status_code=400, detail="Falha na transcrição do áudio.")

        text = transcription.text

        logger.info("📝 Transcrição concluída")

        # ✅ Prompt melhorado
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

        logger.info("🤖 Gerando resumo com IA...")

        summary = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um especialista em resumir reuniões corporativas com foco em clareza, objetividade e geração de ações."
                },
                {
                    "role": "user",
                    "content": f"{prompt}\n\nTranscrição:\n{text}"
                }
            ]
        )

        result = summary.choices[0].message.content

        logger.info("✅ Resumo gerado com sucesso")

        return {
            "transcription": text,
            "summary": result,
            "duration": transcription.audio_duration
        }

    except Exception as e:
        logger.exception("❌ Erro ao processar áudio")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # ✅ Sempre remove o arquivo temporário
        if file_location and os.path.exists(file_location):
            try:
                os.remove(file_location)
                logger.info("🧹 Arquivo temporário removido")
            except Exception as cleanup_error:
                logger.warning(f"Erro ao remover arquivo: {cleanup_error}")
