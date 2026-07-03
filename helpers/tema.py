import streamlit as st

from controller.empresaController import EmpresaController


def obter_tema_empresa() -> dict:
    """
    Helper inteligente: Garante que as cores da empresa logada estejam
    na memória (session_state). Se não estiverem, busca no Controller.
    """
    # 1. Se já estiver na memória da sessão, não faz nada e apenas retorna
    if "cores_empresa" in st.session_state:
        return st.session_state.cores_empresa

    # 2. Se não estiver, precisamos descobrir qual é a empresa conectada/logada
    # Pegamos o ID da empresa direto da sessão do usuário (ou assume a padrão 1)
    id_empresa_atual = st.session_state.get("id_empresa")

    # Caso você guarde o objeto do usuário logado na sessão, pode pegar dele:
    if not id_empresa_atual and "usuario_logado" in st.session_state:
        id_empresa_atual = st.session_state.usuario_logado.id_empresa

    # Se mesmo assim não achar nenhum ID (usuário deslogado ou tela de início)
    if not id_empresa_atual:
        id_empresa_atual = None  # ID padrão de segurança

    try:
        # 3. Chama o EmpresaController para buscar no banco de dados
        empresa_control = EmpresaController()
        cores_banco = empresa_control.get_empresa_colors(id_empresa_atual)

        # 4. Salva o dicionário de cores na memória global do Streamlit
        st.session_state.cores_empresa = cores_banco
        return st.session_state.cores_empresa

    except Exception as e:
        # Fallback de segurança extrema para o app nunca quebrar se o banco cair
        return {
            "tema_primario": "#1f2937", "tema_secundario": "#2563eb",
            "sidebar_fundo": "#fafafa", "sidebar_texto": "#1f2937",
            "cor_alerta_vermelho": "#1f2937", "cor_alerta_amarelo": "#1f2937",
            "cor_alerta_verde": "#059669"
        }


def obter_cor_alerta(tipo_alerta: str) -> str:
    """Retorna uma cor de alerta específica filtrada pelo tipo"""
    tema = obter_tema_empresa()

    mapeamento = {
        "vermelho": "cor_alerta_vermelho",
        "amarelo": "cor_alerta_amarelo",
        "verde": "cor_alerta_verde"
    }

    chave = mapeamento.get(tipo_alerta)
    return tema.get(chave, "#1f2937")
