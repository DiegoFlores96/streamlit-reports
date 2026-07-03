import streamlit as st
from pathlib import Path
from helpers.upload import UploadHelper

# Configuração de Página Única no Topo
st.set_page_config(page_title="Streamlit Reports", layout="wide")


def _load_and_inject_assets(css_path: str, js_path: str):
    """Lê arquivos CSS e JS externos e injeta na aplicação."""
    try:
        with open(css_path, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.sidebar.error(f"Aviso: Arquivo CSS '{css_path}' não encontrado.")

    try:
        with open(js_path, "r", encoding="utf-8") as f:
            st.markdown(f"<script>{f.read()}</script>", unsafe_allow_html=True)
    except FileNotFoundError:
        st.sidebar.error(f"Aviso: Arquivo JS '{js_path}' não encontrado.")


_load_and_inject_assets(
    css_path="assets/css/style.css",
    js_path="assets/js/app.js"
)

# ============================================
# RECUPERAR TOKEN DO BANCO PELO ID
# ============================================
from controller.token_controller import TokenController
from helpers.jwt_helper import JWTHelper

id_url = st.query_params.get("id")

if id_url:
    try:
        id_usuario = int(id_url)

        if st.session_state.get('id_usuario') == id_usuario and st.session_state.get('logged_in'):
            pass
        else:
            token_controller = TokenController()
            token = token_controller.get_ultimo_token_usuario(id_usuario)

            if token:
                payload = JWTHelper.verificar_token(token)
                if payload and payload.get('id_usuario') == id_usuario:
                    st.session_state['auth_token'] = token
                    st.session_state.logged_in = True
                    st.session_state.id_usuario = id_usuario

                    from controller.loginController import LoginController

                    temp_login = LoginController()
                    session = temp_login.db.get_session()
                    try:
                        from model.TabUsuarios import Usuario

                        usuario = session.query(Usuario).filter_by(id_usuario=id_usuario).first()
                        if usuario:
                            st.session_state.email = usuario.email
                            st.session_state.nome = usuario.nome
                            st.session_state.perfil = usuario.perfil or "Padrao"
                            st.session_state.id_empresa = usuario.id_empresa
                    finally:
                        session.close()

                    token_controller.atualizar_ultimo_acesso(token)
    except ValueError:
        st.sidebar.error("⚠️ O parâmetro de ID fornecido na URL é inválido.")

# ============================================
# IMPORTS DAS VIEWS E CONTROLLERS
# ============================================
from controller.loginController import LoginController
from controller.dashboardController import DashboardController
from middleware.auth import Auth
from middleware.access_control import AccessControlMiddleware
from views.pages.cadastros.cadastroDashboards import render_cadastro_dashboards_page
from views.pages.cadastros.cadastroSetores import render_cadastro_setores_page
from views.pages.cadastros.cadastrosUsuarios import render_cadastros_usuarios_page
from views.pages.dashboard.home import render_dashboard_page, render_home_page
from views.pages.login import render_login_page


# ============================================
# FUNÇÕES AUXILIARES DE ESTILIZAÇÃO E MENUS
# ============================================
def _inject_sidebar_style():
    st.markdown(
        """
        <style>

        </style>
        """,
        unsafe_allow_html=True,
    )


def _icon_for_page_type(tipo_pagina: str) -> str:
    tipo = (tipo_pagina or "").lower()
    if tipo == "dashboard":
        return "📊"
    if tipo == "cadastro":
        return "📁"
    if tipo == "relatorio":
        return "📄"
    return "📁"


def _build_setor_map(paginas: list[dict]) -> dict:
    setor_map = {}
    for p in paginas:
        setor = p.get("setor", "Sem setor")
        setor_map.setdefault(setor, []).append(p)
    return dict(sorted(setor_map.items(), key=lambda item: item[0]))


def _render_page_not_implemented(pagina: dict):
    st.title("Página cadastrada")
    st.warning("Esta página ainda não possui renderização implementada no sistema.")
    col1, col2 = st.columns(2)
    col1.metric("Tipo", (pagina.get("tipo_pagina") or "-").title())
    col2.metric("Código", pagina.get("codigo_pagina") or "-")
    st.markdown("---")
    st.subheader("Detalhes")
    st.write(f"Nome: {pagina.get('nome_dashboard', '-')}")
    st.write(f"Setor: {pagina.get('setor', '-')}")
    st.write(f"Descrição: {pagina.get('descricao', '-')}")


# ============================================
# FLUXO PRINCIPAL DE EXECUÇÃO
# ============================================
login_controller = LoginController()
dashboard_controller = DashboardController()

if "pagina_atual" not in st.session_state:
    st.session_state.pagina_atual = "dashboard"

if Auth.require_login(login_controller):
    _inject_sidebar_style()

    # Configuração de Temas Visuais da Empresa
    from controller.empresaController import EmpresaController
    from helpers.tema import obter_cor_alerta, obter_tema_empresa

    empresa_controller = EmpresaController()
    empresa = empresa_controller.get_empresa_do_usuario(login_controller.get_logged_user_id())
    tema_completo = obter_tema_empresa()
    cor_tema_primario = tema_completo['tema_primario']
    cor_tema_secundario = tema_completo['tema_secundario']
    cor_sidebar_fundo = tema_completo['sidebar_fundo']
    cor_sidebar_texto = tema_completo['sidebar_texto']

    if empresa:
        st.markdown(f"""
            <style>
            h1, h2, h3, .stMarkdown h1, .stMarkdown h2 {{
                color: {cor_tema_primario or '#1f2937'} !important;
            }}
            .stButton > button {{
                background-color: {cor_tema_primario or '#2563eb'} !important;
                border-color: {cor_tema_primario or '#2563eb'} !important;
            }}
            .stButton > button:hover {{
                background-color: {cor_tema_secundario or '#1f2937'} !important;
                border-color: {cor_tema_secundario or '#1f2937'} !important;
            }}
            section[data-testid="stSidebar"] {{
                background-color: {cor_sidebar_fundo or '#fafafa'} !important;
            }}
            section[data-testid="stSidebar"] .stMarkdown,
            section[data-testid="stSidebar"] .stButton > button,
            section[data-testid="stSidebar"] .sidebar-title {{
                color: {cor_sidebar_texto or '#1f2937'} !important;
            }}
            </style>
        """, unsafe_allow_html=True)

    # Bloqueador de Fullscreen de Imagem
    st.markdown("""
        <style>
        button[title="View fullscreen"] { display: none !important; }
        .stImage button { display: none !important; }
        </style>
    """, unsafe_allow_html=True)

    # Identidade Visual na Sidebar
    if empresa:
        if empresa.logo:
            caminho_absoluto = UploadHelper.BASE_DIR / empresa.logo
            if caminho_absoluto.exists():
                st.sidebar.image(str(caminho_absoluto), use_container_width=True)
            else:
                st.sidebar.warning("Logo não encontrada")
        else:
            st.sidebar.markdown(
                '<div style="text-align: center; margin-bottom: 20px; margin-top: 10px; font-size: 2rem;">🏢</div>',
                unsafe_allow_html=True)

        st.sidebar.markdown(f"""
            <div style="text-align: center; font-weight: bold; font-size: 1.1rem; margin-bottom: 20px; color: {cor_tema_primario or '#1f2937'};">
                {empresa.nome}
            </div>
        """, unsafe_allow_html=True)
        st.sidebar.markdown("---")

    # Informações do perfil logado
    st.sidebar.header("Navegação")
    st.sidebar.write(f"Usuário: {login_controller.get_logged_user_name()}")
    st.sidebar.write(f"Perfil: {login_controller.get_logged_user_profile()}")
    st.sidebar.markdown("---")

    # Botão Início Fixo
    if st.sidebar.button("🏠 Início", use_container_width=True):
        st.session_state.selected_page_id = None
        st.session_state.pagina_atual = "dashboard"
        st.rerun()

    # ============================================
    # MENU ADMIN EM EXPANDER
    # ============================================
    if login_controller.is_admin():
        paginas_admin = ["config_empresa", "gerenciar_usuarios", "gerenciar_dashboards", "associar_usuario",
                         "cadastro_setores"]
        expander_admin_aberto = st.session_state.pagina_atual in paginas_admin

        with st.sidebar.expander("⚙️ Administração", expanded=expander_admin_aberto):
            if st.button("🏢 Configurar Empresa", key="side_btn_config_empresa", use_container_width=True):
                st.session_state.pagina_atual = "config_empresa"
                st.rerun()

            if st.button("👥 Gerenciar Usuários", key="side_btn_gerenciar_usuarios", use_container_width=True):
                st.session_state.pagina_atual = "gerenciar_usuarios"
                st.rerun()

            if st.button("📊 Gerenciar Dashboards", key="side_btn_gerenciar_dashboards", use_container_width=True):
                st.session_state.pagina_atual = "gerenciar_dashboards"
                st.rerun()

            if st.button("📁 Gerenciar Setores", key="side_btn_gerenciar_setores", use_container_width=True):
                st.session_state.pagina_atual = "cadastro_setores"
                st.rerun()

            if st.button("🔗 Associar Usuários à Empresa", key="side_btn_associar_usuario", use_container_width=True):
                st.session_state.pagina_atual = "associar_usuario"
                st.rerun()

    # ============================================
    # 📊 CARREGAR DASHBOARDS CUSTOMIZADOS (Sempre visível na Sidebar)
    # ============================================
    paginas = AccessControlMiddleware.get_allowed_pages(login_controller)
    selected_page_id = st.session_state.get("selected_page_id")

    if paginas:
        # 🔥 Filtro para ocultar as duplicadas da pasta "Administração"
        paginas_exibicao = [
            p for p in paginas
            if (p.get("setor") or "").lower() not in ["administração", "administracao"]
               and (p.get("codigo_pagina") or "").lower() not in ["cadastros_usuarios", "cadastro_setores",
                                                                  "cadastro_dashboards"]
        ]
    else:
        paginas_exibicao = []

    if paginas_exibicao:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 📊 Dashboards")
        st.sidebar.markdown("<div class='sidebar-title'>Setores</div>", unsafe_allow_html=True)

        setor_map = _build_setor_map(paginas_exibicao)
        for setor, itens in setor_map.items():
            open_expander = any(p.get("id_dashboard") == selected_page_id for p in itens)
            with st.sidebar.expander(f"📁 {setor}", expanded=open_expander):
                for p in itens:
                    icone = _icon_for_page_type(p.get("tipo_pagina", ""))
                    nome = p.get("nome_dashboard", "Página")
                    is_active = p.get("id_dashboard") == selected_page_id
                    prefix = "• " if not is_active else "● "
                    if st.button(
                            f"{prefix}{icone} {nome}",
                            key=f"submenu_{p.get('id_dashboard')}",
                            use_container_width=True,
                    ):
                        st.session_state.selected_page_id = p.get("id_dashboard")
                        st.session_state.pagina_atual = "dashboard"
                        st.rerun()

    # ============================================
    # 🔀 ROTEADOR DE PÁGINAS PRINCIPAL
    # ============================================
    if st.session_state.pagina_atual == "config_empresa":
        from views.pages.admin.configuracao_empresa import render_configuracao_empresa_page

        render_configuracao_empresa_page(login_controller)

    elif st.session_state.pagina_atual == "associar_usuario":
        from views.pages.admin.associar_usuario_empresa import render_associar_usuario_empresa_page

        render_associar_usuario_empresa_page(login_controller)

    elif st.session_state.pagina_atual == "gerenciar_usuarios":
        render_cadastros_usuarios_page(login_controller, dashboard_controller)

    elif st.session_state.pagina_atual == "gerenciar_dashboards":
        render_cadastro_dashboards_page(login_controller, dashboard_controller)

    elif st.session_state.pagina_atual == "cadastro_setores":
        render_cadastro_setores_page(login_controller)

    # Condição isolada que garante que se for "dashboard", renderiza as exibições normais
    if st.session_state.pagina_atual == "dashboard":
        pagina = None
        if selected_page_id is not None:
            for p in paginas:
                if p.get("id_dashboard") == selected_page_id:
                    pagina = p
                    break

        if pagina is None:
            render_home_page(login_controller, paginas)
        else:
            codigo = (pagina.get("codigo_pagina") or "").lower()
            if codigo == "dashboard_exemplo":
                render_dashboard_page(login_controller)
            elif codigo == "cadastros_usuarios":
                render_cadastros_usuarios_page(login_controller, dashboard_controller)
            elif codigo == "cadastro_setores":
                render_cadastro_setores_page(login_controller)
            elif codigo == "cadastro_dashboards":
                render_cadastro_dashboards_page(login_controller, dashboard_controller)
            else:
                dashboard_controller.renderizar_dashboard(codigo, login_controller)

    # Rodapé da Sidebar: Botão Sair
    st.sidebar.markdown("---")
    if st.sidebar.button("Sair", type="primary", use_container_width=True):
        login_controller.logout()
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()
else:
    render_login_page(login_controller)