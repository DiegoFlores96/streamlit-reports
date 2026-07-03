import streamlit as st
from datetime import datetime
from controller.empresaController import EmpresaController
from helpers.upload import UploadHelper


def _set_new_empresa_modal():
    st.session_state.open_new_empresa_modal = True
    st.session_state.empresa_view_id = None
    st.session_state.empresa_delete_confirm_id = None


def _set_edit_empresa_modal(empresa_id):
    st.session_state.open_new_empresa_modal = False
    st.session_state.empresa_view_id = empresa_id
    st.session_state.empresa_delete_confirm_id = None


def _set_delete_empresa_modal(empresa_id):
    st.session_state.open_new_empresa_modal = False
    st.session_state.empresa_view_id = None
    st.session_state.empresa_delete_confirm_id = empresa_id


def _close_all_modals():
    st.session_state.open_new_empresa_modal = False
    st.session_state.empresa_view_id = None
    st.session_state.empresa_delete_confirm_id = None


def _render_new_empresa_dialog(empresa_controller, login_controller):
    with st.form("admin_create_empresa_modal"):
        st.markdown("### 📝 Dados Gerais")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome da Empresa *")
            cnpj = st.text_input("CNPJ")
            razao_social = st.text_input("Razão Social")
            email = st.text_input("Email")
        with col2:
            telefone = st.text_input("Telefone")
            endereco = st.text_input("Endereço")
            cidade = st.text_input("Cidade")
            sub_col1, sub_col2 = st.columns([1, 2])
            with sub_col1:
                estado = st.text_input("UF", max_chars=2)
            with sub_col2:
                cep = st.text_input("CEP")

        st.markdown("---")
        st.markdown("### 🎨 Identidade Visual e Temas")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            tema_primario = st.color_picker("Tema Primário", value="#1F2937")
        with col_c2:
            tema_secundario = st.color_picker("Tema Secundário", value="#2563EB")
        with col_c3:
            sidebar_fundo = st.color_picker("Fundo da Sidebar", value="#FAFAFA")
        with col_c4:
            sidebar_texto = st.color_picker("Texto da Sidebar", value="#1F2937")

        st.markdown("### 🚨 Cores dos Alertas de Dashboard")
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            cor_alerta_vermelho = st.color_picker("Alerta Crítico / Vermelho", value="#1F2937")
        with col_a2:
            cor_alerta_amarelo = st.color_picker("Alerta Atenção / Amarelo", value="#2563EB")
        with col_a3:
            cor_alerta_verde = st.color_picker("Alerta Sucesso / Verde", value="#FAFAFA")

        st.markdown("---")
        logo_file = st.file_uploader(
            "Logo da empresa (PNG, JPG, JPEG)",
            type=["png", "jpg", "jpeg"],
            key="logo_create"
        )

        st.markdown("---")

        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submit = st.form_submit_button("✅ Cadastrar Empresa", use_container_width=True)
        with btn_col2:
            cancel_clicked = st.form_submit_button("Cancelar", use_container_width=True)

    if submit:
        if not nome:
            st.error("O nome da empresa é obrigatório")
        else:
            dados = {
                "nome": nome, "cnpj": cnpj, "razao_social": razao_social,
                "email": email, "telefone": telefone, "endereco": endereco,
                "cidade": cidade, "estado": estado.upper(), "cep": cep,
                "tema_primario": tema_primario, "tema_secundario": tema_secundario,
                "sidebar_fundo": sidebar_fundo, "sidebar_texto": sidebar_texto,
                "cor_alerta_vermelho": cor_alerta_vermelho,
                "cor_alerta_amarelo": cor_alerta_amarelo,
                "cor_alerta_verde": cor_alerta_verde
            }
            ok, msg, id_empresa = empresa_controller.criar_empresa_completa(
                dados, login_controller.get_logged_user_id()
            )
            if ok:
                if logo_file:
                    empresa_controller.upload_logo(logo_file, id_empresa)
                st.success(msg)
                _close_all_modals()
                st.rerun()
            else:
                st.error(msg)

    if cancel_clicked:
        _close_all_modals()
        st.rerun()


def _render_edit_empresa_dialog(empresa_controller, empresa):
    st.caption(f"Editando: {empresa.nome}")

    with st.form(f"admin_edit_empresa_modal_{empresa.id_empresa}"):
        st.markdown("### 📝 Dados Gerais")
        col1, col2 = st.columns(2)
        with col1:
            nome = st.text_input("Nome da Empresa *", value=empresa.nome or "")
            cnpj = st.text_input("CNPJ", value=empresa.cnpj or "")
            razao_social = st.text_input("Razão Social", value=empresa.razao_social or "")
            email = st.text_input("Email", value=empresa.email or "")
        with col2:
            telefone = st.text_input("Telefone", value=empresa.telefone or "")
            endereco = st.text_input("Endereço", value=empresa.endereco or "")
            cidade = st.text_input("Cidade", value=empresa.cidade or "")
            sub_col1, sub_col2 = st.columns([1, 2])
            with sub_col1:
                state = st.text_input("UF", value=empresa.estado or "", max_chars=2)
            with sub_col2:
                cep = st.text_input("CEP", value=empresa.cep or "")

        st.markdown("---")
        st.markdown("### 🎨 Identidade Visual e Temas")
        col_c1, col_c2, col_c3, col_c4 = st.columns(4)
        with col_c1:
            tema_primario = st.color_picker("Tema Primário",
                                            value=getattr(empresa, "tema_primario", "#1F2937") or "#1F2937")
        with col_c2:
            tema_secundario = st.color_picker("Tema Secundário",
                                              value=getattr(empresa, "tema_secundario", "#2563EB") or "#2563EB")
        with col_c3:
            sidebar_fundo = st.color_picker("Fundo da Sidebar",
                                            value=getattr(empresa, "sidebar_fundo", "#FAFAFA") or "#FAFAFA")
        with col_c4:
            sidebar_texto = st.color_picker("Texto da Sidebar",
                                            value=getattr(empresa, "sidebar_texto", "#1F2937") or "#1F2937")

        st.markdown("### 🚨 Cores dos Alertas de Dashboard")
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            cor_alerta_vermelho = st.color_picker("Alerta Crítico / Vermelho",
                                                  value=getattr(empresa, "cor_alerta_vermelho", "#1F2937") or "#1F2937")
        with col_a2:
            cor_alerta_amarelo = st.color_picker("Alerta Atenção / Amarelo",
                                                 value=getattr(empresa, "cor_alerta_amarelo", "#2563EB") or "#2563EB")
        with col_a3:
            cor_alerta_verde = st.color_picker("Alerta Sucesso / Verde",
                                               value=getattr(empresa, "cor_alerta_verde", "#FAFAFA") or "#FAFAFA")

        st.markdown("---")
        col_logo1, col_logo2 = st.columns([1, 2])
        with col_logo1:
            if empresa.logo:
                caminho = UploadHelper.BASE_DIR / empresa.logo
                if caminho.exists():
                    st.image(str(caminho), width=80, caption="Logo atual")
                else:
                    st.info("Logo não encontrada")
            else:
                st.info("Nenhuma logo")
        with col_logo2:
            logo_file = st.file_uploader(
                "Nova logo (PNG, JPG, JPEG)",
                type=["png", "jpg", "jpeg"],
                key=f"logo_{empresa.id_empresa}"
            )

        st.markdown("---")
        # Criando duas colunas internas ao formulário para alinhar os botões lado a lado
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            submit = st.form_submit_button("💾 Salvar alterações", use_container_width=True)
        with btn_col2:
            cancel_clicked = st.form_submit_button("Cancelar", use_container_width=True)

    if submit:
        if not nome:
            st.error("O nome da empresa é obrigatório")
        else:
            dados = {
                "nome": nome, "cnpj": cnpj, "razao_social": razao_social,
                "email": email, "telefone": telefone, "endereco": endereco,
                "cidade": cidade, "estado": state.upper(), "cep": cep,
                "tema_primario": tema_primario, "tema_secundario": tema_secundario,
                "sidebar_fundo": sidebar_fundo, "sidebar_texto": sidebar_texto,
                "cor_alerta_vermelho": cor_alerta_vermelho,
                "cor_alerta_amarelo": cor_alerta_amarelo,
                "cor_alerta_verde": cor_alerta_verde
            }
            ok, msg = empresa_controller.atualizar_empresa(empresa.id_empresa, dados)
            if logo_file:
                empresa_controller.upload_logo(logo_file, empresa.id_empresa)
            if ok:
                st.success(msg)
                _close_all_modals()
                st.rerun()
            else:
                st.error(msg)

    if cancel_clicked:
        _close_all_modals()
        st.rerun()


def _render_delete_empresa_dialog(empresa_controller, empresa):
    usuarios = empresa_controller.listar_usuarios_por_empresa(empresa.id_empresa)
    usuarios_ativos = [u for u in usuarios if (u.situacao or "").lower() == "ativado"]

    if usuarios_ativos:
        st.error(
            f"Não é possível desativar a empresa **{empresa.nome}** pois ela possui "
            f"**{len(usuarios_ativos)} usuário(s) ativo(s)**. "
            f"Desative os usuários primeiro antes de desativar a empresa."
        )
        st.markdown("**Usuários ativos:**")
        for u in usuarios_ativos:
            st.write(f"- {u.nome} ({u.email})")

        if st.button("Fechar", use_container_width=True):
            _close_all_modals()
            st.rerun()
        return

    st.warning(
        f"Você deseja mesmo desativar esta empresa?\n\n"
        f"**{empresa.nome}** — CNPJ: {empresa.cnpj or '-'}"
    )
    col1, col2 = st.columns(2)
    confirm_clicked = col1.button("Sim, desativar", type="primary", use_container_width=True)
    cancel_clicked = col2.button("Cancelar", use_container_width=True)

    if confirm_clicked:
        ok, msg = empresa_controller.excluir_empresa(empresa.id_empresa)
        if ok:
            st.success(msg)
            _close_all_modals()
            st.rerun()
        else:
            st.error(msg)

    if cancel_clicked:
        _close_all_modals()
        st.rerun()


def render_configuracao_empresa_page(login_controller):
    if not login_controller.is_admin():
        st.warning("Apenas administradores podem acessar esta página.")
        return

    col_titulo, col_voltar = st.columns([4, 1])
    with col_titulo:
        st.title("🏢 Configuração de Empresas")
        st.caption("Cadastro e manutenção de empresas")
    with col_voltar:
        st.markdown("<div style='margin-top: 16px'>", unsafe_allow_html=True)
        if st.button("← Voltar", use_container_width=True):
            st.session_state.pagina_atual = "dashboard"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    empresa_controller = EmpresaController()

    if "open_new_empresa_modal" not in st.session_state:
        st.session_state.open_new_empresa_modal = False
    if "empresa_view_id" not in st.session_state:
        st.session_state.empresa_view_id = None
    if "empresa_delete_confirm_id" not in st.session_state:
        st.session_state.empresa_delete_confirm_id = None

    if st.button("➕ Cadastrar nova empresa", type="primary"):
        _set_new_empresa_modal()
        st.rerun()

    if st.session_state.get("open_new_empresa_modal", False):
        if hasattr(st, "dialog"):
            @st.dialog("Cadastrar nova empresa", width="large")
            def _new_empresa_dialog():
                _render_new_empresa_dialog(empresa_controller, login_controller)

            _new_empresa_dialog()
        else:
            with st.expander("Nova empresa", expanded=True):
                _render_new_empresa_dialog(empresa_controller, login_controller)

    empresas = empresa_controller.listar_todas_empresas()
    if not empresas:
        st.info("Nenhuma empresa cadastrada.")
        return

    st.markdown("### Listagem")

    with st.container(border=True):
        # Cabeçalho da Tabela
        hc1, hc2, hc3, hc4, hc5, hc6 = st.columns([0.6, 0.6, 2.5, 2.0, 1.5, 1.2])
        hc1.markdown("**Editar**")
        hc2.markdown("**Excluir**")
        hc3.markdown("**Nome da Empresa**")
        hc4.markdown("**CNPJ**")
        hc5.markdown("**Cidade/UF**")
        hc6.markdown("**Status**")
        st.markdown("<hr style='margin: 8px 0px; border-color: #ddd;' />", unsafe_allow_html=True)

        # Linhas da Tabela
        for empresa in empresas:
            qtd_usuarios = len(empresa_controller.listar_usuarios_por_empresa(empresa.id_empresa))
            status_str = "🟢 Ativo" if empresa.ativo else "🔴 Inativo"

            c1, c2, c3, c4, c5, c6 = st.columns([0.6, 0.6, 2.5, 2.0, 1.5, 1.2])

            # Coluna 1: Botão de Olho (👁️)
            with c1:
                if st.button("👁️", key=f"tbl_view_{empresa.id_empresa}", help="Ver/Editar esta empresa",
                             use_container_width=True):
                    _set_edit_empresa_modal(empresa.id_empresa)
                    st.rerun()

            # Coluna 2: Botão de Lixeira (🗑️)
            with c2:
                if st.button("🗑️", key=f"tbl_del_{empresa.id_empresa}", help="Desativar esta empresa",
                             use_container_width=True):
                    _set_delete_empresa_modal(empresa.id_empresa)
                    st.rerun()

            # Colunas de Dados alinhadas perfeitamente em linha
            c3.write(empresa.nome)
            c4.write(empresa.cnpj or "-")
            c5.write(f"{empresa.cidade or '-'}/{empresa.estado or '-'}")
            c6.write(status_str)

            # Linha divisória sutil entre os registros da tabela
            st.markdown("<hr style='margin: 4px 0px; border-color: #f0f2f6;' />", unsafe_allow_html=True)

    # ========== RENDERIZAÇÃO DOS MODAIS (DIALOGS) ==========
    view_id = st.session_state.get("empresa_view_id")
    if view_id is not None:
        empresa_sel = empresa_controller.get_empresa_por_id(view_id)
        if empresa_sel:
            if hasattr(st, "dialog"):
                @st.dialog("Editar empresa", width="large")
                def _edit_empresa_dialog_wrapper():
                    _render_edit_empresa_dialog(empresa_controller, empresa_sel)

                _edit_empresa_dialog_wrapper()
            else:
                with st.expander("Editar empresa", expanded=True):
                    _render_edit_empresa_dialog(empresa_controller, empresa_sel)

    delete_id = st.session_state.get("empresa_delete_confirm_id")
    if delete_id is not None:
        empresa_del = empresa_controller.get_empresa_por_id(delete_id)
        if empresa_del:
            if hasattr(st, "dialog"):
                @st.dialog("Confirmar desativação")
                def _confirm_delete_dialog_wrapper():
                    _render_delete_empresa_dialog(empresa_controller, empresa_del)

                _confirm_delete_dialog_wrapper()
            else:
                _render_delete_empresa_dialog(empresa_controller, empresa_del)