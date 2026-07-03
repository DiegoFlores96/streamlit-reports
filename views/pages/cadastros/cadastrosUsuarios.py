import streamlit as st
from datetime import datetime
from controller.dashboardController import *

SITUACAO_LABEL = "Situação"
import time


def _format_ts(value):
    if not value:
        return "-"
    try:
        return datetime.fromtimestamp(int(value)).strftime("%d/%m/%Y %H:%M")
    except Exception:
        return "-"


# ==========================================
# 1. FUNÇÕES DE MANIPULAÇÃO DE ESTADO (MODAIS)
# ==========================================
def _set_new_user_modal():
    st.session_state.open_new_user_modal = True
    st.session_state.user_view_id = None
    st.session_state.user_delete_confirm_id = None


def _set_edit_user_modal(user_id):
    st.session_state.open_new_user_modal = False
    st.session_state.user_view_id = user_id
    st.session_state.user_delete_confirm_id = None


def _set_delete_user_modal(user_id):
    st.session_state.open_new_user_modal = False
    st.session_state.user_view_id = None
    st.session_state.user_delete_confirm_id = user_id


def _close_all_modals():
    st.session_state.open_new_user_modal = False
    st.session_state.user_view_id = None
    st.session_state.user_delete_confirm_id = None


# ==========================================
# 2. DIÁLOGOS (DECLARADOS NO ESCOPO GLOBAL)
# ==========================================
@st.dialog("Cadastrar novo usuário")
def _new_user_dialog(login_controller):
    with st.form("admin_create_user_modal"):
        novo_email = st.text_input("Email")
        novo_nome = st.text_input("Nome")
        nova_senha = st.text_input("Senha inicial", type="password")
        novo_perfil = st.selectbox("Perfil", ["Padrao", "Admin"])

        st.markdown(" ")
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submit_create_user = st.form_submit_button("Salvar usuário", type="primary", use_container_width=True)
        with col_btn2:
            cancel_create = st.form_submit_button("Cancelar", use_container_width=True)

    if cancel_create:
        _close_all_modals()
        st.rerun()

    if submit_create_user:
        ok, msg = login_controller.register_user(
            novo_email,
            nova_senha,
            novo_nome,
            perfil=novo_perfil,
        )
        if ok:
            st.success(msg)
            _close_all_modals()
            st.rerun()
        else:
            st.error(msg)


@st.dialog("Editar usuário e permissões", width="large")
def _edit_user_dialog(login_controller, dashboard_controller, usuario_sel, setores):
    st.caption(f"Usuário: **{usuario_sel.nome}** ({usuario_sel.email})")

    aba_dados, aba_setores, aba_dashboards = st.tabs(
        ["📝 Dados Básicos", "📁 Setores Autorizados", "📊 Dashboards Liberados"])

    # --- ABA 1: DADOS BÁSICOS DO USUÁRIO ---
    with aba_dados:
        with st.form(f"form_dados_{usuario_sel.id_usuario}"):
            edit_nome = st.text_input("Nome", value=usuario_sel.nome)
            edit_perfil = st.selectbox(
                "Perfil",
                ["Padrao", "Admin"],
                index=0 if (usuario_sel.perfil or "Padrao") == "Padrao" else 1,
            )
            edit_situacao = st.selectbox(
                SITUACAO_LABEL,
                ["Ativado", "Desativado"],
                index=0 if (usuario_sel.situacao or "Ativado") == "Ativado" else 1,
            )
            submit_dados = st.form_submit_button("Salvar dados cadastrais", type="primary", use_container_width=True)

        if submit_dados:
            ok, msg = login_controller.update_user(usuario_sel.id_usuario, edit_nome, edit_perfil, edit_situacao)
            if ok:
                st.success(msg)
            else:
                st.error(msg)

    # --- ABA 2: GRID DE SETORES COM BUSCA ALINHADA NATIVAMENTE ---
    with aba_setores:
        st.markdown("### 📁 Setores do Usuário")
        setores_atuais_ids = login_controller.get_user_allowed_setor_ids(usuario_sel.id_usuario)
        setores_disponiveis = [s for s in setores if s.id_setor not in setores_atuais_ids]

        if setores_disponiveis:
            mapa_disponiveis_s = {s.nome_setor: s.id_setor for s in setores_disponiveis}

            # Usando vertical_alignment="bottom" para alinhar perfeitamente o botão com o selectbox
            col_busca_s, col_btn_s = st.columns([3.5, 1.0], vertical_alignment="bottom")

            setor_para_adicionar = col_busca_s.selectbox(
                "Buscar novo setor para vincular:",
                options=list(mapa_disponiveis_s.keys()),
                index=0,
                key=f"sb_add_setor_{usuario_sel.id_usuario}"
            )

            if col_btn_s.button("➕ Adicionar", key=f"btn_add_s_exec_{usuario_sel.id_usuario}", type="primary",
                                use_container_width=True):
                id_novo_s = mapa_disponiveis_s[setor_para_adicionar]
                novos_ids = list(setores_atuais_ids) + [id_novo_s]
                login_controller.grant_setor_access(usuario_sel.id_usuario, novos_ids)
                st.rerun()
        else:
            st.info("Este usuário já possui acesso a todos os setores cadastrados.")

        st.markdown("#### Lista de Acessos Ativos")
        setores_vinculados = [s for s in setores if s.id_setor in setores_atuais_ids]

        if not setores_vinculados:
            st.info("Nenhum setor associado a este usuário.")
        else:
            with st.container(border=True):
                g_col1, g_col2 = st.columns([5.5, 1.0])
                g_col1.markdown("**Nome do Setor**")
                g_col2.markdown("**Remover**")
                st.markdown("<hr style='margin: 4px 0px; border-color: #ddd;' />", unsafe_allow_html=True)

                for s in setores_vinculados:
                    c_nome, c_acao = st.columns([5.5, 1.0], vertical_alignment="center")
                    c_nome.write(f"🟢 {s.nome_setor}")

                    if c_acao.button("🗑️", key=f"btn_del_setor_{usuario_sel.id_usuario}_{s.id_setor}",
                                     help="Revogar acesso a este setor", use_container_width=True):
                        novos_ids = [x for x in setores_atuais_ids if x != s.id_setor]
                        login_controller.grant_setor_access(usuario_sel.id_usuario, novos_ids)
                        st.rerun()

                    st.markdown("<hr style='margin: 2px 0px; border-color: #f0f2f6;' />", unsafe_allow_html=True)

    # --- ABA 3: GRID DE DASHBOARDS COM BUSCA ALINHADA NATIVAMENTE ---
    with aba_dashboards:
        st.markdown("### 📊 Dashboards Liberados")
        todos_dashboards = dashboard_controller.list_dashboards(active_only=False)
        dashboards_usuario_ids = dashboard_controller.get_user_allowed_dashboard_ids(usuario_sel.id_usuario)
        dashboards_disponiveis = [d for d in todos_dashboards if d["id_dashboard"] not in dashboards_usuario_ids]

        if dashboards_disponiveis:
            mapa_disponiveis_d = {f"{d['nome_dashboard']} [{d['nome_setor']}]": d["id_dashboard"] for d in
                                  dashboards_disponiveis}

            # Usando vertical_alignment="bottom" para alinhar perfeitamente o botão com o selectbox
            col_busca_d, col_btn_d = st.columns([3.5, 1.0], vertical_alignment="bottom")

            dash_para_adicionar = col_busca_d.selectbox(
                "Buscar novo dashboard para vincular:",
                options=list(mapa_disponiveis_d.keys()),
                index=0,
                key=f"sb_add_dash_{usuario_sel.id_usuario}"
            )

            if col_btn_d.button("➕ Adicionar", key=f"btn_add_d_exec_{usuario_sel.id_usuario}", type="primary",
                                use_container_width=True):
                id_novo_d = mapa_disponiveis_d[dash_para_adicionar]
                dashboard_controller.add_user_dashboard(usuario_sel.id_usuario, id_novo_d)
                st.rerun()
        else:
            st.info("Este usuário já possui acesso a todos os dashboards do sistema.")

        st.markdown("#### Lista de Acessos Ativos")
        dashboards_vinculados = [d for d in todos_dashboards if d["id_dashboard"] in dashboards_usuario_ids]

        if not dashboards_vinculados:
            st.info("Nenhum dashboard associado individualmente a este usuário.")
        else:
            with st.container(border=True):
                gd_col1, gd_col2, gd_col3 = st.columns([3.5, 2.0, 1.0])
                gd_col1.markdown("**Dashboard**")
                gd_col2.markdown("**Setor Origem**")
                gd_col3.markdown("**Remover**")
                st.markdown("<hr style='margin: 4px 0px; border-color: #ddd;' />", unsafe_allow_html=True)

                for d in dashboards_vinculados:
                    id_dash = d["id_dashboard"]
                    c_nome, c_setor, c_acao = st.columns([3.5, 2.0, 1.0], vertical_alignment="center")

                    c_nome.write(f"📊 {d['nome_dashboard']}")
                    c_setor.write(f"`{d['nome_setor']}`")

                    if c_acao.button("🗑️", key=f"btn_del_dash_{usuario_sel.id_usuario}_{id_dash}",
                                     help="Revogar acesso a este dashboard", use_container_width=True):
                        dashboard_controller.remove_user_dashboard(usuario_sel.id_usuario, id_dash)
                        st.rerun()

                    st.markdown("<hr style='margin: 2px 0px; border-color: #f0f2f6;' />", unsafe_allow_html=True)

    st.markdown("---")
    if st.button("Fechar Janela", key=f"btn_fechar_{usuario_sel.id_usuario}", use_container_width=True):
        _close_all_modals()
        st.rerun()


@st.dialog("Confirmar desativação")
def _delete_user_dialog(login_controller, usuario_del):
    st.warning(
        f"Você deseja mesmo desativar este usuário?\n\n"
        f"**{usuario_del.nome}** ({usuario_del.email})"
    )
    col1, col2 = st.columns(2)
    confirm_clicked = col1.button("Sim, desativar", type="primary", use_container_width=True)
    cancel_clicked = col2.button("Cancelar", use_container_width=True)

    if confirm_clicked:
        ok, msg = login_controller.deactivate_user(usuario_del.id_usuario)
        if ok:
            st.success(msg)
            _close_all_modals()
            st.rerun()
        else:
            st.error(msg)

    if cancel_clicked:
        _close_all_modals()
        st.rerun()


# ==========================================
# 3. PÁGINA PRINCIPAL
# ==========================================
def render_cadastros_usuarios_page(login_controller, dashboard_controller):
    if not login_controller.is_admin():
        st.warning("Apenas administradores podem acessar esta página.")
        return

    # Inicialização do Session State
    if "open_new_user_modal" not in st.session_state:
        st.session_state.open_new_user_modal = False
    if "user_view_id" not in st.session_state:
        st.session_state.user_view_id = None
    if "user_delete_confirm_id" not in st.session_state:
        st.session_state.user_delete_confirm_id = None

    usuarios = login_controller.list_users()
    setores = login_controller.list_setores()

    # --- PROCESSA OS MODAIS INTERNOS ---
    if st.session_state.open_new_user_modal:
        _new_user_dialog(login_controller)

    if st.session_state.user_view_id is not None:
        usuario_sel = next((u for u in usuarios if u.id_usuario == st.session_state.user_view_id), None)
        if usuario_sel:
            _edit_user_dialog(login_controller, dashboard_controller, usuario_sel, setores)

    if st.session_state.user_delete_confirm_id is not None:
        usuario_del = next((u for u in usuarios if u.id_usuario == st.session_state.user_delete_confirm_id), None)
        if usuario_del:
            _delete_user_dialog(login_controller, usuario_del)

    # Cabeçalho da página principal
    st.title("👥 Cadastros - Usuários")
    st.caption("Cadastro e manutenção de usuários e controle granular de acessos")

    if st.button("➕ Cadastrar novo usuário", type="primary"):
        _set_new_user_modal()
        st.rerun()

    if not usuarios:
        st.info("Nenhum usuário encontrado.")
        return

    st.markdown("### Listagem")

    with st.container(border=True):
        proporcao_colunas = [0.6, 0.6, 0.6, 1.8, 2.0, 1.0, 2.0, 1.2]

        hc1, hc2, hc3, hc4, hc5, hc6, hc7, hc8 = st.columns(proporcao_colunas)
        hc1.markdown("**Edit**")
        hc2.markdown("**Excl**")
        hc3.markdown("**ID**")
        hc4.markdown("**Nome**")
        hc5.markdown("**Email**")
        hc6.markdown("**Perfil**")
        hc7.markdown("**Setores Vinculados**")
        hc8.markdown(f"**{SITUACAO_LABEL}**")
        st.markdown("<hr style='margin: 8px 0px; border-right: none; border-left: none; border-color: #ddd;' />",
                    unsafe_allow_html=True)

        for u in usuarios:
            status_str = "🟢 Ativado" if (u.situacao or "").lower() == "ativado" else "🔴 Desativado"
            id_usuario = u.id_usuario

            ids_vinculados = login_controller.get_user_allowed_setor_ids(id_usuario)
            nomes_setores = [s.nome_setor for s in setores if s.id_setor in ids_vinculados]
            setores_str = ", ".join(nomes_setores) if nomes_setores else "Nenhum setor"

            c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(proporcao_colunas)

            with c1:
                if st.button("👁️", key=f"tbl_view_{id_usuario}", help="Ver/Editar este usuário",
                             use_container_width=True):
                    _set_edit_user_modal(id_usuario)
                    st.rerun()

            with c2:
                if st.button("🗑️", key=f"tbl_del_{id_usuario}", help="Desativar este usuário",
                             use_container_width=True):
                    _set_delete_user_modal(id_usuario)
                    st.rerun()

            c3.write(str(id_usuario))
            c4.write(u.nome)
            c5.write(u.email)
            c6.write(u.perfil or "Padrao")
            c7.write(f"`{setores_str}`")
            c8.write(status_str)

            st.markdown("<hr style='margin: 4px 0px; border-color: #f0f2f6;' />", unsafe_allow_html=True)