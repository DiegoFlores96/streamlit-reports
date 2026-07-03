"""
Módulo de validadores para garantir integridade de dados.

Fornece validações centralizadas para:
  - Email (RFC 5322 simplificado)
  - CNPJ (14 dígitos)
  - Perfil de usuário (enum)
  - Nome de usuário/empresa
  - Força de senha
  - Campos de texto genéricos

Todos os validadores retornam (bool, str) indicando sucesso e mensagem de erro.
"""
import re
from typing import Tuple


# ============================================
# CONSTANTES
# ============================================
PERFIS_VALIDOS = ["Admin", "Gerente", "Padrao"]

REGEX_EMAIL = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
MAX_EMAIL_LEN = 255
MAX_NOME_LEN = 255


# ============================================
# VALIDADORES
# ============================================

def email_valido(email: str) -> Tuple[bool, str]:
    """
    Valida formato de email.
    
    Args:
        email: String com email a validar
        
    Returns:
        (bool, str): (é_válido, mensagem_erro)
    """
    email = (email or "").strip()
    
    # Validação básica
    if not email:
        return False, "Email é obrigatório."
    
    if len(email) > MAX_EMAIL_LEN:
        return False, f"Email não pode ter mais de {MAX_EMAIL_LEN} caracteres."
    
    # Validação regex (RFC 5322 simplified)
    if not re.match(REGEX_EMAIL, email):
        return False, "Formato de email inválido. Use: usuario@dominio.com"
    
    return True, ""


def cnpj_valido(cnpj: str) -> Tuple[bool, str]:
    """
    Valida formato de CNPJ.
    CNPJ é opcional, portanto string vazia é válida.
    Se fornecido, deve ter exatamente 14 dígitos.
    
    Args:
        cnpj: String com CNPJ a validar
        
    Returns:
        (bool, str): (é_válido, mensagem_erro)
    """
    cnpj = (cnpj or "").strip()
    
    # CNPJ é opcional
    if not cnpj:
        return True, ""
    
    # Remove formatação comum
    cnpj_clean = cnpj.replace(".", "").replace("/", "").replace("-", "").strip()
    
    # Deve conter apenas dígitos e ter 14 caracteres
    if not cnpj_clean.isdigit() or len(cnpj_clean) != 14:
        return False, "CNPJ deve conter 14 dígitos (ex: 00.000.000/0000-00)"
    
    return True, ""


def perfil_valido(perfil: str) -> Tuple[bool, str]:
    """
    Valida se perfil é um dos permitidos.
    Converte para título case para comparação.
    
    Args:
        perfil: String com perfil a validar
        
    Returns:
        (bool, str): (é_válido, mensagem_erro)
    """
    perfil_clean = (perfil or "Padrao").strip().title()
    
    if perfil_clean not in PERFIS_VALIDOS:
        opcoes = ", ".join(PERFIS_VALIDOS)
        return False, f"Perfil inválido. Opções: {opcoes}"
    
    return True, ""


def nome_valido(nome: str, min_len: int = 2, max_len: int = MAX_NOME_LEN) -> Tuple[bool, str]:
    """
    Valida nome de usuário ou empresa.
    
    Args:
        nome: String com nome a validar
        min_len: Comprimento mínimo (padrão: 2)
        max_len: Comprimento máximo (padrão: 255)
        
    Returns:
        (bool, str): (é_válido, mensagem_erro)
    """
    nome_clean = (nome or "").strip()
    
    if not nome_clean:
        return False, "Nome é obrigatório."
    
    if len(nome_clean) < min_len:
        return False, f"Nome deve ter no mínimo {min_len} caracteres."
    
    if len(nome_clean) > max_len:
        return False, f"Nome não pode ter mais de {max_len} caracteres."
    
    return True, ""


def senha_valida(senha: str) -> Tuple[bool, str]:
    """
    Valida força de senha.
    Requisitos: mínimo 8 caracteres, 1 maiúscula, 1 número.
    
    Args:
        senha: String com senha a validar
        
    Returns:
        (bool, str): (é_válido, mensagem_erro)
    """
    if not senha:
        return False, "Senha é obrigatória."
    
    if len(senha) < 8:
        return False, "Senha deve ter pelo menos 8 caracteres."
    
    if not any(c.isupper() for c in senha):
        return False, "Senha deve conter pelo menos uma letra maiúscula."
    
    if not any(c.isdigit() for c in senha):
        return False, "Senha deve conter pelo menos um número."
    
    return True, ""


def validar_entrada_texto(texto: str, nome_campo: str, min_len: int = 1, max_len: int = 500) -> Tuple[bool, str]:
    """
    Validador genérico para campos de texto.
    
    Args:
        texto: String a validar
        nome_campo: Nome do campo (para mensagens)
        min_len: Comprimento mínimo
        max_len: Comprimento máximo
        
    Returns:
        (bool, str): (é_válido, mensagem_erro)
    """
    texto_clean = (texto or "").strip()
    
    if len(texto_clean) < min_len:
        return False, f"{nome_campo} é obrigatório."
    
    if len(texto_clean) > max_len:
        return False, f"{nome_campo} não pode ter mais de {max_len} caracteres."
    
    return True, ""
