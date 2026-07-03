import streamlit as st

from controller.setorController import SetorController


# ==========================================
# 1. FUNÇÕES DE MANIPULAÇÃO DE ESTADO (MODAIS)
# ==========================================
def _set_new_setor_modal():
    st.session_state.open_new_setor_modal = True
    st.session_state.setor_view_id = None
    st.session_state.setor_delete_confirm_id = None


def _set_edit_setor_modal(setor_id):
    st.session_state.open_new_setor_modal = False
    st.session_state.setor_view_id = setor_id
    st.session_state.setor_delete_confirm_id = None


def _set_delete_setor_modal(setor_id):
    st.session_state.open_new_setor_modal = False
    st.session_state.setor_view_id = None
    st.session_state.setor_delete_confirm_id = setor_id


def _close_setor_modals():
    st.session_state.open_new_setor_modal = False
    st.session_state.setor_view_id = None
    st.session_state.setor_delete_confirm_id = None


# ==========================================
# 2. DIÁLOGOS (DECLARADOS NO ESCOPO GLOBAL)
# ==========================================
@st.dialog("Cadastrar novo setor")
def _new_setor_dialog(setor_controller):
    with st.form("create_setor_modal_form"):
        nome_setor = st.text_input("Nome do setor")
        submit_create = st.form_submit_button("Criar setor")

    if st.button("Cancelar", key="cancel_new_setor", use_container_width=True):
        _close_setor_modals()
        st.rerun()

    if submit_create:
        ok, msg = setor_controller.create_setor(nome_setor)
        if ok:
            st.success(msg)
            _close_setor_modals()
            st.rerun()
        else:
            st.error(msg)


@st.dialog("Editar setor", width="large")
def _edit_setor_dialog(setor_controller, setor):
    with st.form(f"update_setor_modal_form_{setor.id_setor}"):
        edit_nome = st.text_input("Nome", value=setor.nome_setor)
        idx = 0 if (setor.situacao or "Ativado") == "Ativado" else 1
        edit_situacao = st.selectbox("Situação", ["Ativado", "Desativado"], index=idx)
        submit_update = st.form_submit_button("Salvar alterações")

    if st.button("Cancelar", key=f"cancel_setor_{setor.id_setor}", use_container_width=True):
        _close_setor_modals()
        st.rerun()

    if submit_update:
        ok, msg = setor_controller.update_setor(setor.id_setor, edit_nome, edit_situacao)
        if ok:
            st.success(msg)
            _close_setor_modals()
            st.rerun()
        else:
            st.error(msg)


@st.dialog("Confirmar desativação")
def _delete_setor_dialog(setor_controller, setor):
    st.warning(
        f"Você deseja mesmo desativar este setor?\n\n"
        f"**{setor.nome_setor}**"
    )
    col1, col2 = st.columns(2)
    confirm_clicked = col1.button("Sim, desativar", type="primary", use_container_width=True)
    cancel_clicked = col2.button("Cancelar", use_container_width=True)

    if confirm_clicked:
        ok, msg = setor_controller.deactivate_setor(setor.id_setor)
        if ok:
            st.success(msg)
            _close_setor_modals()
            st.rerun()
        else:
            st.error(msg)

    if cancel_clicked:
        _close_setor_modals()
        st.rerun()


# ==========================================
# 3. PÁGINA PRINCIPAL
# ==========================================
def render_cadastro_setores_page(login_controller):
    if not login_controller.is_admin():
        st.warning("Apenas administradores podem acessar esta página.")
        return

    # Inicialização segura do Session State
    if "open_new_setor_modal" not in st.session_state:
        st.session_state.open_new_setor_modal = False
    if "setor_view_id" not in st.session_state:
        st.session_state.setor_view_id = None
    if "setor_delete_confirm_id" not in st.session_state:
        st.session_state.setor_delete_confirm_id = None

    setor_controller = SetorController()

    st.title("📁 Cadastros - Setores")
    st.caption("Cadastro e manutenção dos setores (pastas de páginas).")

    st.subheader("Setores")

    setores = setor_controller.list_setores()

    # --- DISPARO DOS DIÁLOGOS (Sem interrupções para manter o fundo atualizado) ---
    if st.session_state.open_new_setor_modal:
        _new_setor_dialog(setor_controller)

    if st.session_state.setor_view_id is not None and setores:
        setor_sel = next((s for s in setores if s.id_setor == st.session_state.setor_view_id), None)
        if setor_sel:
            _edit_setor_dialog(setor_controller, setor_sel)

    if st.session_state.setor_delete_confirm_id is not None and setores:
        setor_del = next((s for s in setores if s.id_setor == st.session_state.setor_delete_confirm_id), None)
        if setor_del:
            _delete_setor_dialog(setor_controller, setor_del)
    # -----------------------------------------------------------------------------

    if st.button("➕ Cadastrar novo setor", type="primary"):
        _set_new_setor_modal()
        st.rerun()

    if not setores:
        st.info("Nenhum setor cadastrado.")
    else:
        st.markdown("### Listagem")

        # CONTAINER PADRONIZADO EM GRID COM AS PROPORÇÕES CORRETAS
        with st.container(border=True):
            # Proporções de colunas mapeadas de forma harmônica (foco no espaçamento de Excluir)
            proporcoes_colunas = [0.6, 0.9, 0.8, 4.2, 1.5]

            # Cabeçalho da Tabela
            hc1, hc2, hc3, hc4, hc5 = st.columns(proporcoes_colunas)
            hc1.markdown("**Editar**")
            hc2.markdown("**Excluir**")
            hc3.markdown("**ID**")
            hc4.markdown("**Nome**")
            hc5.markdown("**Status**")
            st.markdown("<hr style='margin: 8px 0px; border-color: #ddd;' />", unsafe_allow_html=True)

            # Linhas da Tabela
            for setor in setores:
                id_setor = setor.id_setor

                # Tratamento visual do Status/Situação
                status_raw = str(setor.situacao or "Ativado").strip().lower()
                status_str = "🟢 Ativo" if status_raw in ["ativado", "ativo", "true", "1"] else "🔴 Inativo"

                c1, c2, c3, c4, c5 = st.columns(proporcoes_colunas)

                # Coluna 1: Editar (👁️)
                with c1:
                    if st.button("👁️", key=f"tbl_view_setor_{id_setor}", help="Ver/Editar setor",
                                 use_container_width=True):
                        _set_edit_setor_modal(id_setor)
                        st.rerun()

                # Coluna 2: Excluir (🗑️)
                with c2:
                    if st.button("🗑️", key=f"tbl_del_setor_{id_setor}", help="Desativar setor",
                                 use_container_width=True):
                        _set_delete_setor_modal(id_setor)
                        st.rerun()

                # Dados injetados na ordem precisa da tabela
                c3.write(str(id_setor))
                c4.write(setor.nome_setor or "-")
                c5.write(status_str)

                st.markdown("<hr style='margin: 4px 0px; border-color: #f0f2f6;' />", unsafe_allow_html=True)