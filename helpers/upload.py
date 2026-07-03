"""Helper para upload de arquivos."""
import os
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import streamlit as st


class UploadHelper:
    """Gerencia upload de arquivos para o servidor de forma segura."""

    # Caminho absoluto para uploads
    BASE_DIR = Path(__file__).parent.parent  # vai para raiz do projeto
    UPLOAD_DIR = BASE_DIR / "views" / "uploads" / "logo"
    
    # Configurações de segurança
    ALLOWED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    ALLOWED_MIME_TYPES = {
        'image/jpeg': '.jpg',
        'image/png': '.png',
        'image/gif': '.gif',
        'image/webp': '.webp'
    }
    MAX_UPLOAD_SIZE = 5 * 1024 * 1024  # 5MB

    @classmethod
    def init_upload_dir(cls):
        """Cria a pasta de uploads se não existir."""
        cls.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        print(f"📁 Pasta de uploads: {cls.UPLOAD_DIR}")

    @classmethod
    def _validar_arquivo(cls, arquivo) -> tuple[bool, str]:
        """Valida arquivo antes do upload.
        
        Verifica:
          - Tamanho máximo
          - Extensão permitida
          
        Returns:
            (válido, mensagem_erro)
        """
        if arquivo is None:
            return False, "Nenhum arquivo fornecido"
        
        # Validar tamanho
        size = len(arquivo.getbuffer())
        if size > cls.MAX_UPLOAD_SIZE:
            return False, f"Arquivo muito grande. Máximo: {cls.MAX_UPLOAD_SIZE // (1024*1024)}MB"
        
        if size == 0:
            return False, "Arquivo vazio"
        
        # Validar extensão
        extensao = f".{arquivo.name.split('.')[-1].lower()}"
        if extensao not in cls.ALLOWED_EXTENSIONS:
            return False, f"Tipo de arquivo não permitido. Aceitos: {', '.join(cls.ALLOWED_EXTENSIONS)}"
        
        return True, ""

    @classmethod
    def salvar_imagem(cls, arquivo, id_empresa: int) -> Optional[str]:
        """
        Salva uma imagem após validação segura.

        Args:
            arquivo: Arquivo enviado pelo Streamlit
            id_empresa: ID da empresa (para nome do arquivo)

        Returns:
            Caminho relativo do arquivo salvo, ou None se falhar
        """
        cls.init_upload_dir()

        if arquivo is None:
            return None

        # Validar arquivo ANTES de processar
        valido, msg_erro = cls._validar_arquivo(arquivo)
        if not valido:
            print(f"⚠️ Validação de arquivo falhou: {msg_erro}")
            return None

        try:
            # Gerar nome único e seguro
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            extensao = f".{arquivo.name.split('.')[-1].lower()}"
            nome_arquivo = f"empresa_{id_empresa}_{timestamp}{extensao}"

            # Caminho absoluto para salvar
            caminho_absoluto = cls.UPLOAD_DIR / nome_arquivo
            
            # Verificação extra: garantir que não há path traversal
            if not str(caminho_absoluto.resolve()).startswith(str(cls.UPLOAD_DIR.resolve())):
                raise ValueError("Tentativa de path traversal detectada")

            # Salvar arquivo
            with open(caminho_absoluto, "wb") as f:
                f.write(arquivo.getbuffer())

            # Retornar caminho relativo para o banco (URL amigável)
            caminho_relativo = f"views/uploads/logo/{nome_arquivo}"
            print(f"✅ Logo salva em: {caminho_absoluto}")

            return caminho_relativo

        except ValueError as e:
            print(f"❌ Erro de segurança ao salvar imagem: {e}")
            return None
        except Exception as e:
            print(f"❌ Erro ao salvar imagem: {e}")
            return None

    @classmethod
    def excluir_imagem(cls, caminho_relativo: str) -> bool:
        """Exclui uma imagem do servidor de forma segura.
        
        Args:
            caminho_relativo: Caminho relativo do arquivo
            
        Returns:
            True se excluído ou não existia, False se erro
        """
        if not caminho_relativo:
            return True

        try:
            # Converter caminho relativo para absoluto
            caminho_absoluto = cls.BASE_DIR / caminho_relativo
            
            # Verificação de segurança: garantir que arquivo está em UPLOAD_DIR
            if not str(caminho_absoluto.resolve()).startswith(str(cls.UPLOAD_DIR.resolve())):
                raise ValueError("Tentativa de path traversal detectada")
            
            if caminho_absoluto.exists():
                caminho_absoluto.unlink()
                print(f"🗑️ Logo excluída: {caminho_absoluto}")
            return True
        except ValueError as e:
            print(f"❌ Erro de segurança ao excluir imagem: {e}")
            return False
        except Exception as e:
            print(f"❌ Erro ao excluir imagem: {e}")
            return False

    @classmethod
    def obter_url_imagem(cls, caminho_relativo: str) -> str:
        """Obtém a URL para exibir a imagem."""
        if not caminho_relativo:
            return ""

        # Verificar se arquivo existe
        caminho_absoluto = cls.BASE_DIR / caminho_relativo
        if caminho_absoluto.exists():
            return caminho_relativo
        return ""