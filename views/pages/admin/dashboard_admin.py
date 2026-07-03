import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
from streamlit_extras.metric_cards import style_metric_cards
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode, JsCode
from controller.loginController import LoginController
from controller.empresaController import EmpresaController
from controller.token_controller import TokenController
from helpers.tema import obter_cor_alerta, obter_tema_empresa
from helpers.formata import *
empresa_control = EmpresaController()
ano_atual = datetime.now().year
dados_meses = {}

# Mapeamentos globais para consistência de dados
MESES_NOMES = {
    "01": "Jan", "02": "Fev", "03": "Mar", "04": "Abr",
    "05": "Mai", "06": "Jun", "07": "Jul", "08": "Ago",
    "09": "Set", "10": "Out", "11": "Nov", "12": "Dez"
}

def render_dashboard_admin_content():
    """Renderiza os blocos internos do dashboard administrativo."""

    login_ctrl = LoginController()
    empresa_ctrl = EmpresaController()
    token_ctrl = TokenController()
    tema_completo = obter_tema_empresa()


    usuarios = login_ctrl.list_users()
    usuarios_ativos = [u for u in usuarios if (u.situacao or "").lower() == "ativado"]
    empresas = empresa_ctrl.listar_todas_empresas()
    id_empresa = st.session_state.get("id_empresa", 1)
    cor_tema_primario=tema_completo['tema_primario']
    cor_alerta_vermelho = obter_cor_alerta("vermelho")
    cor_alerta_amarelo = obter_cor_alerta("amarelo")
    cor_alerta_verde = obter_cor_alerta("verde")
    trinta_dias = datetime.now() - timedelta(days=30)
    desativados_recentes = [
        u for u in usuarios
        if (u.situacao or "").lower() != "ativado"
           and u.dt_desativacao
           and datetime.fromtimestamp(int(u.dt_desativacao)) >= trinta_dias
    ]

    # --- CARDS DE MÉTRICAS ---
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("👥 Total de Usuários", len(usuarios), delta=f"+{len(usuarios_ativos)} ativos")
    with col2:
        paginas = login_ctrl.get_menu_pages_for_logged_user()
        st.metric("📋 Dashboards Ativados", len(paginas))
    with col3:
        admins = len([u for u in usuarios if (u.perfil or "").lower() == "admin"])
        st.metric("👑 Administradores", admins)
    with col4:
        st.metric("🔴 Desativados (30 dias)", len(desativados_recentes))

    style_metric_cards(border_left_color="#4f46e5", box_shadow=True)

    # --- PROCESSAMENTO DE DADOS (EVOLUÇÃO MENSAL DOS GRÁFICOS) ---


    for u in usuarios:
        if u.dt_criacao:
            try:
                dt = datetime.fromtimestamp(int(u.dt_criacao))
            except (ValueError, TypeError):
                continue
            if dt.year != ano_atual:
                continue
            chave = dt.strftime("%m/%Y")
            if chave not in dados_meses:
                dados_meses[chave] = {"Ativos": 0, "Inativos": 0}
            if (u.situacao or "").lower() == "ativado":
                dados_meses[chave]["Ativos"] += 1
            else:
                dados_meses[chave]["Inativos"] += 1

    rows = []
    for mes, vals in sorted(dados_meses.items(), key=lambda x: datetime.strptime(x[0], "%m/%Y")):
        total = vals["Ativos"] + vals["Inativos"]
        taxa = round((vals["Inativos"] / total * 100), 1) if total > 0 else 0
        rows.append({
            "Mês": mes,
            "Ativos": vals["Ativos"],
            "Inativos": vals["Inativos"],
            "Taxa de Desativação (%)": taxa
        })

    df_meses = pd.DataFrame(rows)

    # --- GRÁFICOS LADO A LADO ---
    gcol1, gcol2 = st.columns([1, 2])

    with gcol1:
        with st.container(key="card_chart1", border=True):
            perfis = {}
            for u in usuarios:
                perfil = (u.perfil or "Padrao").lower().capitalize()
                perfis[perfil] = perfis.get(perfil, 0) + 1

            df_perfis = pd.DataFrame({
                "Perfil": list(perfis.keys()),
                "Quantidade": list(perfis.values())
            })
            fig = px.bar(
                df_perfis,
                x="Quantidade",
                y="Perfil",
                orientation="h",
                title="Usuários por Perfil",
                color="Perfil",
            )
            fig.update_layout(showlegend=False)
            fig.update_xaxes(title=None, showticklabels=False)
            fig.update_yaxes(title=None)
            st.plotly_chart(fig, use_container_width=True)

    with gcol2:
        with st.container(key="card_barras", border=True):
            fig = px.bar(
                df_meses,
                x="Mês",
                y=["Ativos", "Inativos"],
                title="Usuários Ativos vs Inativos por Mês",
                barmode="group",
                color_discrete_map={"Ativos":cor_alerta_verde, "Inativos": cor_alerta_vermelho},
                custom_data=["Taxa de Desativação (%)"]
            )
            fig.update_yaxes(title=None, showticklabels=False)
            fig.update_traces(
                width=0.3,
                marker_line_width=0,
                hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y}<br>Taxa de desativação: %{customdata[0]}%<extra></extra>"
            )
            fig.update_layout(
                legend=dict(
                    title=None,
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="center",
                    x=0.5
                )
            )
            st.plotly_chart(fig, use_container_width=True)

    # --- MATRIZ DE ACESSO MODELO PIVOT (CADA MÊS É UMA COLUNA) ---
    st.markdown("---")
    with st.container(key="card_matriz", border=True):
        st.subheader("📅 Média de Acessos por Mês")
        st.caption(f"Visualização em matriz onde cada mês corresponde a uma coluna — ano {ano_atual}")

        tokens = token_ctrl.listar_todos_tokens()
        usuario_map = {u.id_usuario: u.nome for u in usuarios if u.id_usuario}

        vistos = set()
        dados_base = []

        # Coleta inicial dos dados brutos por dia para evitar duplicidade na contagem do mesmo dia
        for t in tokens:
            if not t.dt_criacao:
                continue
            try:
                dt = datetime.fromtimestamp(int(t.dt_criacao))
            except:
                continue
            if dt.year != ano_atual:
                continue

            nome = usuario_map.get(t.id_usuario, f"Usuário {t.id_usuario}")
            mes_nome = MESES_NOMES.get(dt.strftime("%m"), "Desconhecido")
            dia = dt.strftime("%d/%m/%Y")

            chave = (nome, mes_nome, dia)
            if chave in vistos:
                continue
            vistos.add(chave)

            dados_base.append({
                "Usuário": nome,
                "Mês": mes_nome,
                "Acessos": 1
            })

        if dados_base:
            df_base = pd.DataFrame(dados_base)

            # Agrupa por Usuário e Mês trazendo a soma total de dias acessados naquele mês
            df_agrupado = df_base.groupby(["Usuário", "Mês"], as_index=False)["Acessos"].sum()

            # Transforma a coluna 'Mês' em colunas horizontais e calcula a média (nesse caso, o valor consolidado)
            df_pivot = df_agrupado.pivot_table(
                index="Usuário",
                columns="Mês",
                values="Acessos",
                aggfunc="mean"
            ).fillna(0)  # Preenche os meses sem acesso com 0

            # Força as colunas a seguirem a ordem cronológica correta do calendário
            ordem_meses_coluna = [m for m in MESES_NOMES.values() if m in df_pivot.columns]
            df_pivot = df_pivot[ordem_meses_coluna]

            # Calcula uma coluna de Média Geral na direita para resumo do Usuário
            df_pivot["Média Geral"] = round(df_pivot.mean(axis=1), 1)

            # Reseta o index para o 'Usuário' voltar a ser uma coluna normal tratável pelo AgGrid
            df_pivot = df_pivot.reset_index()

            # Configuração do AgGrid para exibição limpa
            gb = GridOptionsBuilder.from_dataframe(df_pivot)
            gb.configure_default_column(resizable=True, filterable=True, sortable=True, width=100)

            # Fixa o Usuário na esquerda
            gb.configure_column("Usuário", headerName="👥 Usuário", pinned='left', width=180)

            # Aplica estilo azul destacado na coluna de Média Geral do usuário
            gb.configure_column(
                "Média Geral",
                headerName="📊 Média Geral",
                pinned='right',
                width=130,
                cellStyle=JsCode("""
                    function(params) {
                        return {
                            backgroundColor: '#e0f2fe',
                            fontWeight: 'bold',
                            color: '#0369a1',
                            textAlign: 'center'
                        };
                    }
                """)
            )

            gridOptions = gb.build()
            gridOptions['animateRows'] = True

            AgGrid(
                df_pivot,
                gridOptions=gridOptions,
                update_mode=GridUpdateMode.NO_UPDATE,
                allow_unsafe_jscode=True,
                height=350,
                fit_columns_on_grid_load=True,
                theme="streamlit"
            )
        else:
            st.info("Nenhum acesso registrado no ano atual.")

    # --- TABELA DE EMPRESAS ---
    st.markdown("---")
    with st.expander("🏢 Empresas Cadastradas", expanded=False):
        if empresas:
            dados = []
            for e in empresas:
                qtd = len(empresa_ctrl.listar_usuarios_por_empresa(e.id_empresa))
                dados.append({
                    "Empresa": e.nome,
                    "CNPJ": e.cnpj or "-",
                    "Usuários": qtd,
                    "Status": "🟢 Ativo" if e.ativo else "🔴 Inativo"
                })
            st.dataframe(pd.DataFrame(dados), use_container_width=True, hide_index=True)
        else:
            st.info("Nenhuma empresa cadastrada")


def render_dashboard_admin_page(login_controller):
    if not login_controller.is_admin():
        st.warning("⚠️ Apenas administradores podem acessar esta página.")
        return

    st.title("📊 Dashboard Administrativo")
    render_dashboard_admin_content()

    if st.button("← Voltar", use_container_width=True):
        st.session_state.pagina_atual = "dashboard"
        st.rerun()