from fastapi import Header, HTTPException
from jose import jwt
from dotenv import load_dotenv
import requests
import os
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

def get_user(authorization: str = Header(...)):
    try:
        token = authorization.split(" ")[1]

        response = requests.get(
            f"{SUPABASE_URL}/auth/v1/user",
            headers={
                "Authorization": f"Bearer {token}",
                "apikey": SUPABASE_ANON_KEY,
            },
        )

        if response.status_code != 200:
            raise HTTPException(status_code=401, detail="Usuário não autenticado")

        return response.json()

    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")