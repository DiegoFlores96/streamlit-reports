import streamlit as st
import base64
from pathlib import Path
from views.pages.admin.dashboard_admin import render_dashboard_admin_content
from views.pages.cadastros.cadastrosUsuarios import render_cadastros_usuarios_page


def obter_imagem_base64(caminho_relativo: str) -> str:
    """Lê uma imagem local e converte para string Base64 para injeção direta no HTML."""
    caminho = Path(caminho_relativo)
    if caminho.exists():
        with open(caminho, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            return f"data:image/png;base64,{encoded_string}"
    return ""


def render_home_page(login_controller, paginas: list[dict]):
    nome = login_controller.get_logged_user_name() or "Usuário"
    perfil = login_controller.get_logged_user_profile() or "Padrao"

    print(f"show_admin_dashboard: {st.session_state.get('show_admin_dashboard', False)}")
    print(f"pagina_atual: {st.session_state.get('pagina_atual', 'dashboard')}")

    st.title("Home")
    st.caption(f"Bem-vindo, {nome}!")

    dashboards = [p for p in paginas if (p.get("tipo_pagina") or "").lower() == "dashboard"]

    # ============================================
    # MOSTRAR DASHBOARDS DO USUÁRIO
    # ============================================
    if dashboards:
        setor_map: dict[str, list[dict]] = {}
        for p in dashboards:
            setor = p.get("setor", "Sem setor")
            setor_map.setdefault(setor, []).append(p)

        st.write(f"Perfil: {perfil}")
        st.markdown("---")

        # Injeção de CSS para estruturar os Cards
        st.markdown(
            """
            <style>
            .card-hint {
                color: #6b7280;
                font-size: 0.85rem;
                margin-top: -0.25rem;
                margin-bottom: 0.75rem;
            }
            .custom-card {
                background-color: #ffffff !important;
                border: 1px solid #e5e7eb !important;
                border-radius: 12px !important;
                padding: 16px !important;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05) !important;
                transition: transform 0.2s, box-shadow 0.2s !important;
                margin-bottom: 5px !important;
                height: 220px !important;
                display: flex !important;
                flex-direction: column !important;
                justify-content: space-between !important;
            }
            .custom-card:hover {
                transform: translateY(-4px) !important;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1) !important;
                border-color: #3b82f6 !important;
            }
            .card-header-title {
                font-size: 1.1rem !important;
                font-weight: 600 !important;
                color: #1f2937 !important;
                margin: 0 0 4px 0 !important;
            }
            .card-desc {
                font-size: 0.85rem !important;
                color: #6b7280 !important;
                margin: 0 !important;
                overflow: hidden !important;
                text-overflow: ellipsis !important;
                display: -webkit-box !important;
                -webkit-line-clamp: 2 !important;
                -webkit-box-orient: vertical !important;
            }
            /* Container para a imagem */
            .card-img-container {
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
                height: 60px !important;
                margin: 6px 0 !important;
                overflow: hidden !important;
            }
            .card-img-container img {
                max-height: 100% !important;
                max-width: 100% !important;
                object-fit: contain !important;
            }
            .card-footer-code {
                font-size: 0.75rem !important;
                background-color: #f3f4f6 !important;
                color: #4b5563 !important;
                padding: 2px 8px !important;
                border-radius: 6px !important;
                align-self: flex-start !important;
                font-family: monospace !important;
            }
            .stButton > button[kind="primary"] {
                background-color: transparent !important;
                color: #3b82f6 !important;
                border: 1px solid #3b82f6 !important;
                width: 100%;
                margin-top: 10px;
                font-size: 0.85rem;
                padding: 4px;
                min-height: auto;
            }
            .stButton > button[kind="primary"]:hover {
                background-color: #3b82f6 !important;
                color: white !important;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )

        # Carrega e converte a imagem uma única vez usando o caminho relativo do projeto
        img_base64 = obter_imagem_base64("assets/img/grafico.png")

        for setor, itens in sorted(setor_map.items(), key=lambda item: item[0]):
            st.subheader(f"📁 {setor}")
            st.markdown("<div class='card-hint'>Clique no botão do card para abrir a página.</div>",
                        unsafe_allow_html=True)
            cols = st.columns(3)

            for idx, pagina in enumerate(itens):
                with cols[idx % 3]:
                    titulo = pagina.get("nome_dashboard", "Dashboard")
                    descricao = pagina.get("descricao") or "Sem descrição"
                    codigo = pagina.get("codigo_pagina", "-")

                    # Se a imagem local não for achada por algum erro de pasta, coloca um emoji de gráfico como plano de fundo reserva
                    img_tag = f'<img src="{img_base64}" alt="Gráfico">' if img_base64 else '<span style="font-size: 2.2rem;">📈</span>'

                    # Monta a estrutura aplicando a tag de imagem processada em Base64
                    html_card = f"""
                    <div class="custom-card">
                        <div>
                            <h4 class="card-header-title">📊 {titulo}</h4>
                            <p class="card-desc">{descricao}</p>
                        </div>

                        <div class="card-img-container">
                            {img_tag}
                        </div>

                        <span class="card-footer-code">Cód: {codigo}</span>
                    </div>
                    """

                    st.html(html_card)

                    # Botão funcional do Streamlit abaixo do card
                    if st.button(
                            "Acessar Painel →",
                            key=f"open_page_{pagina.get('id_dashboard')}",
                            use_container_width=True,
                            type="primary",
                    ):
                        st.session_state.selected_page_id = pagina.get("id_dashboard")
                        st.session_state.pagina_atual = "dashboard"
                        st.rerun()

            st.markdown(" ")

    # ============================================
    # SE NÃO TEM DASHBOARDS E NÃO É ADMIN
    # ============================================
    elif not login_controller.is_admin():
        st.info("Você ainda não possui dashboards liberados. Entre em contato com o administrador.")

    # ============================================
    # PAINEL ADMIN
    # ============================================
    if login_controller.is_admin():
        st.markdown("---")
        st.subheader("⚙️ Painel Administrativo")
        st.caption("Área restrita para administradores")

        col_admin1, col_admin2, col_admin3, col_admin4 = st.columns(4)

        with col_admin1:
            if st.button("🏢 Configurar Empresa", key="btn_config_empresa", use_container_width=True):
                st.session_state.pagina_atual = "config_empresa"
                st.rerun()

        with col_admin2:
            if st.button("👥 Gerenciar Usuários", key="btn_gerenciar_usuarios", use_container_width=True):
                st.session_state.pagina_atual = "gerenciar_usuarios"
                st.rerun()

        with col_admin3:
            if st.button("📊 Gerenciar Dashboards", key="btn_gerenciar_dashboards", use_container_width=True):
                st.session_state.pagina_atual = "gerenciar_dashboards"
                st.rerun()

        with col_admin4:
            if st.button("📁 Gerenciar Setores", key="btn_gerenciar_setores_home", use_container_width=True):
                st.session_state.pagina_atual = "cadastro_setores"
                st.rerun()

        st.markdown(" ")
        render_dashboard_admin_content()


def render_dashboard_page(login_controller):
    st.title("Dashboard")
    st.info("Selecione um dashboard liberado no menu para visualizar o conteúdo detalhado.")