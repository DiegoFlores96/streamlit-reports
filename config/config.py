import os
from dotenv import load_dotenv
from typing import Dict, List

load_dotenv()

class Config:
    def __init__(self):
        self.name_app = os.getenv("NAME_APP", "Streamlit Reports")
        self.password_encode = os.getenv("PASSWORD_ENCODE", "utf-8")
        self.encoding = os.getenv("ENCODING", "utf-8")

        MESES: Dict[str, str] = {
            "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
            "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
            "09": "Set", "10": "Out", "11": "Nov", "12": "Dez"
        }
        # Formato de datas
        FORMATO_DATA_BR: str = "%d/%m/%Y"
        FORMATO_DATA_US: str = "%Y-%m-%d"
        FORMATO_DATA_HORA: str = "%d/%m/%Y %H:%M:%S"
        FORMATO_DATA_HORA_US: str = "%Y-%m-%d %H:%M:%S"
        CORES: Dict[str, str] = {
            "primaria": "#4f46e5",  # Roxo/Índigo
            "sucesso": "#059669",  # Verde
            "erro": "#dc2626",  # Vermelho
            "alerta": "#f59e0b",  # Laranja
            "info": "#0ea5e9",  # Azul
            "cinza": "#6b7280",  # Cinza
            "fundo": "#f3f4f6",  # Fundo claro
        }
        CORES_GRAFICOS: Dict[str, str] = {
            "Ativos": "#059669",
            "Inativos": "#dc2626",
            "Admin": "#4f46e5",
            "Padrao": "#0ea5e9",
            "Total": "#6b7280"
        }
        # ==================== CONFIGURAÇÕES DE PERFORMANCE ====================
        CACHE_TTL: int = 300  # Tempo de cache em segundos (5 minutos)
        MAX_REGISTROS_TABELA: int = 1000  # Máximo de registros em tabelas

        # ==================== CONFIGURAÇÕES DE NEGÓCIO ====================
        DIAS_DESATIVACAO_RECENTE: int = 30
        TENTATIVAS_LOGIN_MAX: int = 5
        TEMPO_SESSAO_MINUTOS: int = 30

        # ==================== CONFIGURAÇÕES DE PERFIS ====================
        PERFIS: Dict[str, str] = {
            "admin": "Administrador",
            "padrao": "Usuário Padrão",
            "gerente": "Gerente",
            "visitante": "Visitante"
        }