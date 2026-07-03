"""Módulo para gerenciamento de tokens JWT."""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging
import os
import jwt
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class JWTHelper:
    """Helper para criação e validação de tokens JWT."""

    SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "")
    ALGORITHM: str = "HS256"

    # Tempo de expiração do token em minutos (padrão: 60 minutos = 1 hora)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

    @classmethod
    def _get_secret_key(cls) -> str:
        """Obtém a chave JWT e falha de forma segura fora de testes."""
        if cls.SECRET_KEY:
            return cls.SECRET_KEY

        if os.getenv("PYTEST_CURRENT_TEST"):
            return "test-secret-key-12345"

        raise RuntimeError("JWT_SECRET_KEY deve ser configurada antes de iniciar a aplicação.")

    @classmethod
    def criar_token(cls, id_usuario: int, minutos_validade: Optional[int] = None) -> str:
        """
        Cria um novo token JWT.
        """
        if minutos_validade is None:
            minutos_validade = cls.ACCESS_TOKEN_EXPIRE_MINUTES

        expire = datetime.now(timezone.utc) + timedelta(minutes=minutos_validade)

        payload: Dict[str, Any] = {
            'id_usuario': id_usuario,
            'exp': expire,
            'iat': datetime.now(timezone.utc),
            'type': 'access'
        }

        # Usar jwt.encode diretamente
        return jwt.encode(payload, cls._get_secret_key(), algorithm=cls.ALGORITHM)

    @classmethod
    def criar_token_com_dias(cls, id_usuario: int, dias_validade: int = 7) -> str:
        """Cria token com validade em dias."""
        minutos = dias_validade * 24 * 60
        return cls.criar_token(id_usuario, minutos)

    @classmethod
    def verificar_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Verifica se o token é válido."""
        try:
            payload = jwt.decode(token, cls._get_secret_key(), algorithms=[cls.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            logger.info("Token JWT inválido recebido.")
            return None

    @classmethod
    def renovar_token(cls, token: str) -> Optional[str]:
        """Renova o token se ainda for válido."""
        try:
            payload = jwt.decode(
                token,
                cls._get_secret_key(),
                algorithms=[cls.ALGORITHM],
                options={"verify_exp": False}
            )

            if 'id_usuario' not in payload:
                return None

            exp_timestamp = payload.get('exp')
            if exp_timestamp:
                agora = datetime.now(timezone.utc).timestamp()
                if agora - exp_timestamp > 300:
                    return None

            return cls.criar_token(payload['id_usuario'])
        except Exception:
            logger.warning("Falha ao renovar token JWT.", exc_info=False)
            return None