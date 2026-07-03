"""
Módulo de Formatação - Funções reutilizáveis

Este módulo fornece funções para formatação consistente de dados
seguindo princípios de Clean Code e boas práticas.
"""
from datetime import datetime
from typing import Union, Optional, Any
import re
import pandas as pd


# ==================== CONSTANTES ====================

class _Constantes:
    """Constantes internas do módulo"""
    # Formatos de data
    DATA_BR = "%d/%m/%Y"
    DATA_US = "%Y-%m-%d"

    # Configurações padrão
    DECIMAL_PADRAO = 2
    PORCENTAGEM_PADRAO = 1
    ZERO_PADRAO = 2

    # Padrões de texto
    CONECTORES_NOME = {'da', 'de', 'do', 'das', 'dos', 'e', 'a', 'o'}

    # Regex para limpeza
    REGEX_LETRAS = r'[^a-zA-ZáéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ\s]'
    REGEX_LETRAS_NUMEROS = r'[^a-zA-Z0-9áéíóúâêîôûãõçÁÉÍÓÚÂÊÎÔÛÃÕÇ\s]'
    REGEX_NUMEROS = r'[^0-9]'


# ==================== FUNÇÕES AUXILIARES PRIVADAS ====================



def _para_float(valor: Any) -> float:
    """Converte valor para float de forma segura"""
    if isinstance(valor, str):
        valor = valor.replace(',', '.')
    return float(valor)


def _para_datetime(data: Any) -> Optional[datetime]:
    """Converte diferentes formatos para datetime"""
    if isinstance(data, datetime):
        return data

    if isinstance(data, (int, float)):
        return datetime.fromtimestamp(data)

    if isinstance(data, str):
        if data.isdigit():
            return datetime.fromtimestamp(int(data))

        # Tenta formatos diferentes
        for fmt in [_Constantes.DATA_US, _Constantes.DATA_BR]:
            try:
                return datetime.strptime(data, fmt)
            except ValueError:
                continue

    return None


def _aplica_decimal_br(valor: str) -> str:
    """Aplica formato decimal brasileiro (ponto milhar, vírgula decimal)"""
    return valor.replace(",", "X").replace(".", ",").replace("X", ".")


def _is_vazio(valor: Any) -> bool:
    """Retorna True para valores vazios ou nulos."""
    if valor is None:
        return True
    if isinstance(valor, str):
        return valor.strip() == ""
    if isinstance(valor, float) and pd.isna(valor):
        return True
    return False


def converter_para_float_seguro(valor: Any) -> float:
    """Converte texto monetário/numeral para float de forma segura, preservando negativos válidos."""
    if _is_vazio(valor) or pd.isna(valor):
        return 0.0

    if isinstance(valor, (int, float)):
        numero = float(valor)
        return numero

    valor_str = str(valor).strip()
    sinal_negativo = valor_str.startswith("-") or valor_str.startswith("(")

    valor_str = valor_str.replace("R$", "").replace(" ", "").replace("*", "")
    valor_str = re.sub(r"[^0-9,.]", "", valor_str)

    if not valor_str:
        return 0.0

    if "," in valor_str and "." in valor_str:
        if valor_str.rfind(",") > valor_str.rfind("."):
            valor_str = valor_str.replace(".", "").replace(",", ".")
        else:
            valor_str = valor_str.replace(",", "")
    elif "," in valor_str:
        valor_str = valor_str.replace(".", "").replace(",", ".")
    else:
        valor_str = valor_str.replace(",", "")

    if not valor_str or valor_str.count(".") > 1:
        return 0.0

    try:
        numero = float(valor_str)
        return -numero if sinal_negativo and numero > 0 else numero
    except (ValueError, TypeError):
        return 0.0


# ==================== FUNÇÕES DE DATA ====================

def data_br(data: Any) -> str:
    """
    Formata data para DD/MM/YYYY

    Args:
        data: Data em timestamp, string ou datetime

    Returns:
        Data formatada ou string vazia se inválida

    Exemplos:
        >>> data_br('2024-12-15')
        '15/12/2024'
        >>> data_br(datetime(2024, 12, 15))
        '15/12/2024'
    """
    if _is_vazio(data):
        return ""

    try:
        dt = _para_datetime(data)
        return dt.strftime(_Constantes.DATA_BR) if dt else ""
    except (ValueError, TypeError, AttributeError):
        return ""


def data_us(data: Any) -> str:
    """
    Formata data para YYYY-MM-DD

    Args:
        data: Data em timestamp, string ou datetime

    Returns:
        Data formatada ou string vazia se inválida

    Exemplos:
        >>> data_us('15/12/2024')
        '2024-12-15'
    """
    if _is_vazio(data):
        return ""

    try:
        dt = _para_datetime(data)
        return dt.strftime(_Constantes.DATA_US) if dt else ""
    except (ValueError, TypeError, AttributeError):
        return ""


def normalizar_coluna_data(series_dados: pd.Series) -> pd.Series:
    """Converte uma série para datas válidas, preenchendo inválidos com a data atual."""
    datas_convertidas = pd.to_datetime(series_dados, errors="coerce")
    hoje = pd.Timestamp(datetime.now().date())
    datas_treated = datas_convertidas.fillna(hoje)
    return pd.to_datetime(datas_treated.dt.date)


# ==================== FUNÇÕES DE NÚMEROS ====================

def formatar_numero(valor: Any, casas: int = _Constantes.DECIMAL_PADRAO) -> str:
    """
    Formata decimal com vírgula: 1234.56 -> 1.234,56

    Args:
        valor: Valor a ser formatado
        casas: Número de casas decimais

    Returns:
        Número formatado
    """
    try:
        if isinstance(valor, str):
            valor = converter_para_float_seguro(valor)
        elif isinstance(valor, (int, float)):
            valor = float(valor)

        formatado = f"{float(valor):,.{casas}f}"
        return _aplica_decimal_br(formatado)
    except (ValueError, TypeError):
        zeros = '0' * casas
        return f"0,{zeros}"


def decimal(valor: Any, casas: int = _Constantes.DECIMAL_PADRAO) -> str:
    """Alias de compatibilidade para formatar_numero."""
    return formatar_numero(valor, casas)


def reais(valor: Any, simbolo: bool = True) -> str:
    """
    Formata para Real: 1234.56 -> R$ 1.234,56

    Args:
        valor: Valor a ser formatado
        simbolo: Se True, inclui o símbolo R$

    Returns:
        Valor formatado em Real
    """
    valor_fmt = formatar_numero(valor, 2)
    return f"R$ {valor_fmt}" if simbolo else valor_fmt


def dolar(valor: Any, simbolo: bool = True) -> str:
    """
    Formata para Dólar: 1234.56 -> $ 1,234.56

    Args:
        valor: Valor a ser formatado
        simbolo: Se True, inclui o símbolo $

    Returns:
        Valor formatado em Dólar
    """
    try:
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.'))
        valor_fmt = f"{valor:,.2f}"
        return f"US$ {valor_fmt}" if simbolo else valor_fmt
    except (ValueError, TypeError):
        return "US$ 0.00" if simbolo else "0.00"


def porcentagem(valor: Any, casas: int = _Constantes.PORCENTAGEM_PADRAO) -> str:
    """
    Formata porcentagem: 0.15 -> 15,0%

    Args:
        valor: Valor (0.15 = 15%)
        casas: Número de casas decimais

    Returns:
        Porcentagem formatada
    """
    try:
        if isinstance(valor, str):
            valor = float(valor.replace(',', '.'))
        percentual = valor * 100
        return f"{percentual:.{casas}f}%".replace(".", ",")
    except (ValueError, TypeError):
        return "0%"


def zero(valor: Any, tamanho: int = _Constantes.ZERO_PADRAO) -> str:
    """
    Adiciona zero à esquerda: 5 -> 05

    Args:
        valor: Valor a ser preenchido
        tamanho: Tamanho final desejado

    Returns:
        String com zeros à esquerda
    """
    try:
        return str(valor).zfill(tamanho)
    except (ValueError, TypeError):
        return "0" * tamanho


# ==================== FUNÇÕES DE TEXTO ====================

def limpar(texto: Any, manter_numeros: bool = False) -> str:
    """
    Remove caracteres especiais e espaços extras

    Args:
        texto: Texto a ser limpo
        manter_numeros: Se True, mantém números no texto

    Returns:
        Texto limpo

    Exemplos:
        >>> limpar('Olá!!! Mundo!!!')
        'Olá Mundo'
        >>> limpar('ABC123!@#', True)
        'ABC123'
    """
    if _is_vazio(texto):
        return ""

    texto = ' '.join(str(texto).split())
    pattern = _Constantes.REGEX_LETRAS_NUMEROS if manter_numeros else _Constantes.REGEX_LETRAS
    texto_limpo = re.sub(pattern, '', texto)

    return ' '.join(texto_limpo.split()).strip()


def maiusculo(texto: Any) -> str:
    """
    Converte texto para MAIÚSCULO

    Exemplo:
        >>> maiusculo('joão')
        'JOÃO'
    """
    return str(texto).upper() if texto else ""


def minusculo(texto: Any) -> str:
    """
    Converte texto para minúsculo

    Exemplo:
        >>> minusculo('JOÃO')
        'joão'
    """
    return str(texto).lower() if texto else ""


def capitalizar(texto: Any) -> str:
    """
    Primeira letra maiúscula: joão -> João

    Exemplo:
        >>> capitalizar('joão')
        'João'
    """
    return str(texto).capitalize() if texto else ""


def titulo(texto: Any) -> str:
    """
    Primeira letra de cada palavra: joão silva -> João Silva

    Exemplo:
        >>> titulo('joão silva')
        'João Silva'
    """
    return str(texto).title() if texto else ""


def nome_proprio(texto: Any) -> str:
    """
    Formata nome próprio respeitando conectores: joão da silva -> João da Silva

    Args:
        texto: Nome completo

    Returns:
        Nome formatado

    Exemplo:
        >>> nome_proprio('joão da silva')
        'João da Silva'
    """
    if _is_vazio(texto):
        return ""

    palavras = str(texto).lower().strip().split()
    resultado = []

    for palavra in palavras:
        if palavra in _Constantes.CONECTORES_NOME:
            resultado.append(palavra)
        else:
            resultado.append(palavra.capitalize())

    return ' '.join(resultado)


# ==================== FUNÇÕES DE DOCUMENTOS ====================

def cnpj(valor: Any) -> str:
    """
    Formata CNPJ: 12345678000199 -> 12.345.678/0001-99

    Exemplo:
        >>> cnpj('12345678000199')
        '12.345.678/0001-99'
    """
    if _is_vazio(valor):
        return ""

    numeros = re.sub(_Constantes.REGEX_NUMEROS, '', str(valor))

    if len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"

    return str(valor)


def cpf(valor: Any) -> str:
    """
    Formata CPF: 12345678900 -> 123.456.789-00

    Exemplo:
        >>> cpf('12345678900')
        '123.456.789-00'
    """
    if _is_vazio(valor):
        return ""

    numeros = re.sub(_Constantes.REGEX_NUMEROS, '', str(valor))

    if len(numeros) == 11:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"

    return str(valor)


def telefone(valor: Any) -> str:
    """
    Formata telefone: 11912345678 -> (11) 91234-5678

    Exemplos:
        >>> telefone('11912345678')
        '(11) 91234-5678'
        >>> telefone('1123456789')
        '(11) 1234-5678'
    """
    if _is_vazio(valor):
        return ""

    numeros = re.sub(_Constantes.REGEX_NUMEROS, '', str(valor))
    tamanho = len(numeros)

    if tamanho == 11:
        return f"({numeros[:2]}) {numeros[2:7]}-{numeros[7:]}"
    if tamanho == 10:
        return f"({numeros[:2]}) {numeros[2:6]}-{numeros[6:]}"

    return str(valor)


def cep(valor: Any) -> str:
    """
    Formata CEP: 12345678 -> 12345-678

    Exemplo:
        >>> cep('12345678')
        '12345-678'
    """
    if _is_vazio(valor):
        return ""

    numeros = re.sub(_Constantes.REGEX_NUMEROS, '', str(valor))

    if len(numeros) == 8:
        return f"{numeros[:5]}-{numeros[5:]}"

    return str(valor)