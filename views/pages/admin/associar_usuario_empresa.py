import streamlit as st
from controller.loginController import LoginController
from controller.empresaController import EmpresaController


def render_associar_usuario_empresa_page(login_controller):
    """Página para associar usuários à empresa (apenas admin)"""

    if not login_controller.is_admin():
        st.warning("⚠️ Apenas administradores podem acessar esta página.")
        if st.button("← Voltar"):
            st.session_state.pagina_atual = "dashboard"
            st.rerun()
        return

    st.title("🔗 Associar Usuários à Empresa")
    st.caption("Associe os usuários cadastrados a uma empresa")

    login_ctrl = LoginController()
    empresa_ctrl = EmpresaController()

    # Listar empresas
    empresas = empresa_ctrl.listar_empresas()
    if not empresas:
        st.warning("⚠️ Nenhuma empresa cadastrada. Cadastre uma empresa primeiro.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🏢 Cadastrar Empresa", use_container_width=True):
                st.session_state.pagina_atual = "config_empresa"
                st.rerun()
        with col2:
            if st.button("← Voltar", use_container_width=True):
                st.session_state.pagina_atual = "dashboard"
                st.rerun()
        return

    # Listar usuários
    usuarios = login_ctrl.list_users()
    if not usuarios:
        st.warning("⚠️ Nenhum usuário cadastrado.")
        if st.button("👥 Cadastrar Usuário"):
            st.info("Vá em Cadastros > Usuários para criar usuários")
        return

    # Criar dicionários
    mapa_empresas = {f"{e.nome} - {e.cnpj or 'Sem CNPJ'}": e.id_empresa for e in empresas}

    st.subheader("🏢 Selecione a Empresa")
    empresa_selecionada = st.selectbox("Empresa", list(mapa_empresas.keys()))
    id_empresa = mapa_empresas[empresa_selecionada]
    empresa_nome = empresa_selecionada.split(" - ")[0]

    st.markdown("---")

    # Separar usuários já associados dos não associados
    usuarios_associados = []
    usuarios_nao_associados = []

    for u in usuarios:
        if u.id_empresa == id_empresa:
            usuarios_associados.append(u)
        else:
            usuarios_nao_associados.append(u)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"✅ Usuários da {empresa_nome}")
        if usuarios_associados:
            for u in usuarios_associados:
                st.write(f"**{u.nome}** - {u.email} ({u.perfil})")
        else:
            st.info(f"Nenhum usuário associado à {empresa_nome}")

    with col2:
        st.subheader(f"➕ Associar à {empresa_nome}")
        if usuarios_nao_associados:
            mapa_usuarios = {f"{u.nome} ({u.email}) - {u.perfil}": u.id_usuario for u in usuarios_nao_associados}
            usuarios_selecionados = st.multiselect(
                "Selecione os usuários para associar",
                list(mapa_usuarios.keys())
            )

            if st.button("🔗 Associar Selecionados", use_container_width=True):
                ids_selecionados = [mapa_usuarios[nome] for nome in usuarios_selecionados]
                ok, msg = empresa_ctrl.associar_usuarios_empresa(ids_selecionados, id_empresa)
                if ok:
                    st.success(msg)
                    st.balloons()
                    st.rerun()
                else:
                    st.error(msg)
        else:
            st.success("🎉 Todos os usuários já estão associados a esta empresa!")

    st.markdown("---")

    # Botão voltar
    if st.button("← Voltar para o Sistema", use_container_width=True):
        st.session_state.pagina_atual = "dashboard"
        st.rerun()