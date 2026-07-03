import streamlit as st
import time
from controller.dashboardController import DashboardController

TIPOS_PAGINA = ["dashboard", "cadastro", "relatorio", "outro"]


# ==========================================
# 1. FUNÇÕES DE MANIPULAÇÃO DE ESTADO (MODAIS)
# ==========================================
def _set_new_dashboard_modal():
    st.session_state.open_new_dashboard_modal = True
    st.session_state.dashboard_view_id = None
    st.session_state.dashboard_delete_confirm_id = None


def _set_edit_dashboard_modal(dashboard_id):
    st.session_state.open_new_dashboard_modal = False
    st.session_state.dashboard_view_id = dashboard_id
    st.session_state.dashboard_delete_confirm_id = None


def _set_delete_dashboard_modal(dashboard_id):
    st.session_state.open_new_dashboard_modal = False
    st.session_state.dashboard_view_id = None
    st.session_state.dashboard_delete_confirm_id = dashboard_id


def _close_dashboard_modals():
    st.session_state.open_new_dashboard_modal = False
    st.session_state.dashboard_view_id = None
    st.session_state.dashboard_delete_confirm_id = None


# ==========================================
# 🌟 APENAS DOIS DROPDOWNS REATIVOS EM TEMPO REAL
# ==========================================
def renderizar_dois_dropdowns(arquivos_fisicos, sufixo_chave="", caminho_atual_banco=""):
    if not arquivos_fisicos:
        st.warning("Nenhum arquivo encontrado nas pastas.")
        return st.text_input("Código da página (manual)", value="exemplo", key=f"manual_{sufixo_chave}")

    # Agrupa os arquivos por pasta de forma segura
    mapa_estrutura = {}
    for arq in arquivos_fisicos:
        caminho = arq.get("caminho_completo") or arq.get("caminho_final") or arq.get("label", "")
        nome_arq = arq.get("nome_arquivo") or caminho.split("/")[-1]

        partes = caminho.split("/")
        pasta = partes[0].upper() if len(partes) > 1 else "RAIZ"

        if pasta not in mapa_estrutura:
            mapa_estrutura[pasta] = []

        mapa_estrutura[pasta].append({
            "nome_arquivo": nome_arq,
            "caminho_final": caminho
        })

    # Descobre o índice padrão da pasta se estiver em modo de edição
    default_pasta_idx = 0
    if caminho_atual_banco:
        for idx, pasta in enumerate(mapa_estrutura.keys()):
            if any(a["caminho_final"] == caminho_atual_banco for a in mapa_estrutura[pasta]):
                default_pasta_idx = idx
                break

    lista_pastas = list(mapa_estrutura.keys())

    # 1º DROPDOWN: Escolha da pasta (Atualiza o estado ao clicar)
    pasta_selecionada = st.selectbox(
        "📁 Selecione a Pasta",
        lista_pastas,
        index=default_pasta_idx,
        key=f"drop_pasta_{sufixo_chave}"
    )

    # Filtra estritamente os arquivos da pasta selecionada
    arquivos_filtrados = mapa_estrutura.get(pasta_selecionada, [])
    lista_nomes_arquivos = [a["nome_arquivo"] for a in arquivos_filtrados]

    # Descobre o índice do arquivo para a edição dentro desta pasta específica
    default_arquivo_idx = 0
    if caminho_atual_banco:
        for idx, a in enumerate(arquivos_filtrados):
            if a["caminho_final"] == caminho_atual_banco:
                default_arquivo_idx = idx
                break

    # Se mudar de pasta, resguarda para não quebrar o índice do Streamlit
    if default_arquivo_idx >= len(lista_nomes_arquivos):
        default_arquivo_idx = 0

    # 2º DROPDOWN: Apenas arquivos da pasta selecionada
    if lista_nomes_arquivos:
        arquivo_selecionado_nome = st.selectbox(
            "📄 Selecione o Arquivo",
            lista_nomes_arquivos,
            index=default_arquivo_idx,
            key=f"drop_arq_{sufixo_chave}"
        )

        idx_final = lista_nomes_arquivos.index(arquivo_selecionado_nome)
        objeto_final = arquivos_filtrados[idx_final]
        codigo_final = objeto_final["caminho_final"]

        #st.caption(f"Caminho dinâmico mapeado: `{codigo_final}`")
        return codigo_final
    else:
        st.warning("Nenhum arquivo nesta pasta.")
        return ""


# ==========================================
# 2. DIÁLOGOS (DECLARADOS NO ESCOPO GLOBAL)
# ==========================================
@st.dialog("Cadastrar nova página")
def _new_dashboard_dialog(dashboard_controller, setores):
    mapa_setores = {f"{s.id_setor} - {s.nome_setor}": s.id_setor for s in setores}
    arquivos_fisicos = dashboard_controller.obter_arquivos_disponiveis()

    # 🌟 Os dropdowns reativos ficam fora do form para atualizar o segundo selectbox instantaneamente
    codigo_pagina = renderizar_dois_dropdowns(arquivos_fisicos, sufixo_chave="new")

    with st.form("admin_create_dashboard_modal"):
        nome_dashboard = st.text_input("Nome da página")
        desc_dashboard = st.text_area("Descrição")
        tipo_pagina = st.selectbox("Tipo da página", TIPOS_PAGINA)
        setor_escolhido = st.selectbox("Vincular ao Setor (Banco)", list(mapa_setores.keys()))

        st.markdown(" ")
        # 🌟 Criação de duas colunas internas para colocar os botões lado a lado
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submit_dash = st.form_submit_button("Criar página", type="primary", use_container_width=True)
        with col_btn2:
            cancel_dash = st.form_submit_button("Cancelar", use_container_width=True)

    # Se o usuário clicar em cancelar, fecha o diálogo imediatamente
    if cancel_dash:
        _close_dashboard_modals()
        st.rerun()

    if submit_dash:
        if not codigo_pagina:
            st.error("Por favor, selecione um arquivo válido antes de salvar.")
            return

        ok, msg = dashboard_controller.create_dashboard(
            nome_dashboard,
            desc_dashboard,
            mapa_setores[setor_escolhido],
            tipo_pagina=tipo_pagina,
            codigo_pagina=codigo_pagina,
        )
        if ok:
            st.success(msg)
            _close_dashboard_modals()
            st.rerun()
        else:
            st.error(msg)


@st.dialog("Editar página", width="small")
def _edit_dashboard_dialog(dashboard_controller, dashboard, setores):
    mapa_setores = {f"{s.id_setor} - {s.nome_setor}": s.id_setor for s in setores}
    labels = list(mapa_setores.keys())

    default_setor_index = 0
    for i, label in enumerate(labels):
        if mapa_setores[label] == dashboard["id_setor"]:
            default_setor_index = i
            break

    tipo_atual = (dashboard.get("tipo_pagina") or "dashboard").lower()
    codigo_atual = (dashboard.get("codigo_pagina") or "").strip()

    arquivos_fisicos = dashboard_controller.obter_arquivos_disponiveis()

    # 🌟 Dropdowns fora do form para carregar e atualizar o arquivo mapeado corretamente
    edit_codigo = renderizar_dois_dropdowns(arquivos_fisicos, sufixo_chave="edit", caminho_atual_banco=codigo_atual)

    with st.form(f"admin_edit_dashboard_modal_{dashboard['id_dashboard']}"):
        edit_nome = st.text_input("Nome da página", value=dashboard.get("nome_dashboard", ""))
        edit_desc = st.text_area("Descrição", value=dashboard.get("descricao", ""))
        edit_tipo = st.selectbox(
            "Tipo da página",
            TIPOS_PAGINA,
            index=TIPOS_PAGINA.index(tipo_atual) if tipo_atual in TIPOS_PAGINA else 0,
        )

        setor_escolhido = st.selectbox("Vincular ao Setor (Banco)", labels, index=default_setor_index)
        ativo_label = st.selectbox(
            "Situação",
            ["Ativado", "Desativado"],
            index=0 if dashboard.get("ativo", True) else 1,
        )

        st.markdown(" ")
        # 🌟 Duas colunas internas para os botões do formulário de edição
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            submit_update = st.form_submit_button("Salvar alterações", type="primary", use_container_width=True)
        with col_btn2:
            cancel_edit = st.form_submit_button("Cancelar", use_container_width=True)

    if cancel_edit:
        _close_dashboard_modals()
        st.rerun()

    if submit_update:
        if not edit_codigo:
            st.error("Selecione um arquivo válido.")
            return

        ok, msg = dashboard_controller.update_dashboard(
            dashboard["id_dashboard"],
            edit_nome,
            edit_desc,
            mapa_setores[setor_escolhido],
            edit_tipo,
            edit_codigo,
            ativo_label == "Ativado",
        )
        if ok:
            st.success(msg)
            _close_dashboard_modals()
            st.rerun()
        else:
            st.error(msg)


@st.dialog("Confirmar desativação")
def _delete_dashboard_dialog(dashboard_controller, dashboard):
    st.warning(f"Você deseja mesmo desativar esta página?\n\n**{dashboard.get('nome_dashboard', '-')}**")
    col1, col2 = st.columns(2)
    confirm_clicked = col1.button("Sim, desativar", type="primary", use_container_width=True)
    cancel_clicked = col2.button("Cancelar", use_container_width=True)

    if confirm_clicked:
        ok, msg = dashboard_controller.deactivate_dashboard(dashboard["id_dashboard"])
        if ok:
            st.success(msg)
            _close_dashboard_modals()
            st.rerun()
        else:
            st.error(msg)

    if cancel_clicked:
        _close_dashboard_modals()
        st.rerun()


# ==========================================
# 3. PÁGINA PRINCIPAL
# ==========================================
def render_cadastro_dashboards_page(login_controller,*args, **kwargs):
    if not login_controller.is_admin():
        st.warning("Apenas administradores podem acessar esta página.")
        return

    dashboard_controller = DashboardController()

    if "open_new_dashboard_modal" not in st.session_state:
        st.session_state.open_new_dashboard_modal = False
    if "dashboard_view_id" not in st.session_state:
        st.session_state.dashboard_view_id = None
    if "dashboard_delete_confirm_id" not in st.session_state:
        st.session_state.dashboard_delete_confirm_id = None

    st.title("📟 Cadastros - Páginas")

    aba_paginas, aba_permissoes = st.tabs(["Páginas", "Permissões"])

    with aba_paginas:
        st.subheader("Páginas")

        setores = dashboard_controller.list_setores()
        dashboards = dashboard_controller.list_dashboards(active_only=False)

        if st.session_state.open_new_dashboard_modal and setores:
            _new_dashboard_dialog(dashboard_controller, setores)

        if st.session_state.dashboard_view_id is not None and dashboards and setores:
            dash_sel = next((x for x in dashboards if x["id_dashboard"] == st.session_state.dashboard_view_id), None)
            if dash_sel:
                _edit_dashboard_dialog(dashboard_controller, dash_sel, setores)

        if st.session_state.dashboard_delete_confirm_id is not None and dashboards:
            dash_del = next(
                (x for x in dashboards if x["id_dashboard"] == st.session_state.dashboard_delete_confirm_id), None)
            if dash_del:
                _delete_dashboard_dialog(dashboard_controller, dash_del)

        btn_col1, btn_col2, _ = st.columns([1.5, 1.8, 4.0])

        with btn_col1:
            if st.button("➕ Nova página", type="primary", use_container_width=True):
                _set_new_dashboard_modal()
                st.rerun()

        #with btn_col2:
         #   if st.button("🔄 Sincronizar Pasta", help="Escanear arquivos do servidor", use_container_width=True):
          #      with st.spinner("Sincronizando pastas do servidor... Aguarde."):
           #         sucesso, msg_sinc = dashboard_controller.sincronizar_arquivos_fisicos()

            #    if sucesso:
             #       st.toast("✅ Sincronização concluída com sucesso!", icon="🔄")
              #      time.sleep(3)
               #     st.rerun()
                #else:
                 #   st.error(msg_sinc)

        st.markdown(" ")

        if not setores:
            st.info("Cadastre setores manuais para iniciar.")
        else:
            if not dashboards:
                st.info("Nenhuma página cadastrada.")
            else:
                st.markdown("### Listagem")

                with st.container(border=True):
                    proporcoes_colunas = [0.6, 0.9, 0.6, 2.2, 1.2, 1.8, 1.5, 1.2]

                    hc1, hc2, hc3, hc4, hc5, hc6, hc7, hc8 = st.columns(proporcoes_colunas)
                    hc1.markdown("**Editar**")
                    hc2.markdown("**Excluir**")
                    hc3.markdown("**ID**")
                    hc4.markdown("**Nome**")
                    hc5.markdown("**Tipo**")
                    hc6.markdown("**Código**")
                    hc7.markdown("**Setor**")
                    hc8.markdown("**Status**")
                    st.markdown("<hr style='margin: 8px 0px; border-color: #ddd;' />", unsafe_allow_html=True)

                    for d in dashboards:
                        status_str = "🟢 Ativo" if d.get("ativo") else "🔴 Inativo"
                        id_dash = d["id_dashboard"]

                        c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(proporcoes_colunas)

                        with c1:
                            if st.button("👁️", key=f"tbl_view_dash_{id_dash}", help="Ver/Editar página",
                                         use_container_width=True):
                                _set_edit_dashboard_modal(id_dash)
                                st.rerun()

                        with c2:
                            if st.button("🗑️", key=f"tbl_del_dash_{id_dash}", help="Desativar página",
                                         use_container_width=True):
                                _set_delete_dashboard_modal(id_dash)
                                st.rerun()

                        c3.write(str(id_dash))
                        c4.write(d.get("nome_dashboard") or "-")
                        c5.write((d.get("tipo_pagina") or "-").title())
                        c6.write(d.get("codigo_pagina") or "-")
                        c7.write(d.get("nome_setor") or "-")
                        c8.write(status_str)

                        st.markdown("<hr style='margin: 4px 0px; border-color: #f0f2f6;' />", unsafe_allow_html=True)

    with aba_permissoes:
        usuarios = login_controller.list_users()
        dashboards_ativos = dashboard_controller.list_dashboards(active_only=False)

        if not usuarios or not dashboards_ativos:
            st.info("Cadastre usuários e páginas para liberar permissões.")
            return

        mapa_usuarios = {f"{u.id_usuario} - {u.nome}": u.id_usuario for u in usuarios}
        mapa_dashboards = {
            f"{d['id_dashboard']} - {d['nome_dashboard']} [{d['codigo_pagina']}]": d["id_dashboard"]
            for d in dashboards_ativos
        }

        with st.container(border=True):
            st.markdown("### 🔐 Conceder Acesso a Páginas")

            usuario_label = st.selectbox("Selecione o Usuário", list(mapa_usuarios.keys()))
            usuario_id = mapa_usuarios[usuario_label]

            atuais_ids = dashboard_controller.get_user_allowed_dashboard_ids(usuario_id)
            default_labels = [k for k, v in mapa_dashboards.items() if v in atuais_ids]

            dashboards_sel = st.multiselect(
                "Marque as páginas liberadas para este usuário",
                list(mapa_dashboards.keys()),
                default=default_labels,
            )

            st.markdown(" ")
            if st.button("💾 Salvar permissões", type="primary", use_container_width=True):
                ids = [mapa_dashboards[label] for label in dashboards_sel]
                ok, msg = dashboard_controller.grant_dashboard_access(usuario_id, ids)
                st.success(msg) if ok else st.error(msg)