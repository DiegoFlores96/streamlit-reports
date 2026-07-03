import os
import re
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv

from controller.empresaController import EmpresaController
from controller.loginController import LoginController
from controller.token_controller import TokenController
from helpers.formata import dolar, formatar_numero, normalizar_coluna_data, reais
from helpers.tema import obter_cor_alerta, obter_tema_empresa

warnings.filterwarnings('ignore')

load_dotenv()

caminho_base = Path(os.getenv("PATH_TESTES_ARQUIVOS"))
arquivo = caminho_base / "TESTES GUSTAVO.xlsx"

id_empresa = st.session_state.get("id_empresa")


def render_page(login_controller=None):
    """Busca e retorna as cores configuradas para o tema da empresa."""
    if not st.session_state.get("auth_token"):
        st.session_state.pagina_atual = "login"
        st.rerun()
        st.stop()
    
    tema_completo = obter_tema_empresa()
    return {
        "primaria": tema_completo['tema_primario'],
        "secundaria": tema_completo['tema_secundario'],
        "sidebar_fundo": tema_completo['sidebar_fundo'],
        "sidebar_texto": tema_completo['sidebar_texto'],
        "cor_alerta_vermelho": obter_cor_alerta("vermelho"),
        "cor_alerta_amarelo": obter_cor_alerta("amarelo"),
        "cor_alerta_verde": obter_cor_alerta("verde")
    }


def listar_abas() -> list[str]:
    xl = pd.ExcelFile(arquivo)
    return xl.sheet_names


def ler_aba(indice: int) -> pd.DataFrame:
    abas = listar_abas()
    aba = abas[indice]
    df = pd.read_excel(arquivo, sheet_name=aba)
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    df = df.dropna(how="all")
    return df


def build_dim_produto() -> pd.DataFrame:
    return ler_aba(0)


def build_dim_estoque() -> pd.DataFrame:
    d_estoque = ler_aba(4)
    estoque_filial = ler_aba(5)
    d_filial = ler_aba(6)
    empresa_filial = ler_aba(7)
    d_empresa = ler_aba(8)

    d_estoque = d_estoque.rename(columns={"COD-ESTOQUE": "COD_ESTOQUE"})
    d_filial = d_filial.rename(columns={"ID": "COD_FILIAL", "EMPRESA": "NOME_FILIAL"})
    d_empresa = d_empresa.rename(columns={"ID": "COD_EMPRESA", "EMPRESA": "NOME_EMPRESA"})

    dim = estoque_filial.merge(d_estoque, on="COD_ESTOQUE", how="left")
    dim = dim.merge(empresa_filial, on="COD_FILIAL", how="left")
    dim = dim.merge(d_filial, on="COD_FILIAL", how="left")
    dim = dim.merge(d_empresa, on="COD_EMPRESA", how="left")

    dim["COD_ESTOQUE"] = dim["COD_ESTOQUE"].str.replace(
        r"EST-(\d+)",
        lambda m: f"EST-{int(m.group(1)):03d}",
        regex=True
    )
    return dim


def build_baixa() -> pd.DataFrame:
    return ler_aba(12)


def numero_para_float(valor) -> float:
    """Converte valor para float sem passar por formatação (preserva precisão para cálculos)."""
    from helpers.formata import converter_para_float_seguro
    return converter_para_float_seguro(valor)


def calcular_valor_compra(df: pd.DataFrame) -> pd.Series:
    if "QUANTIDADE" not in df.columns or "PRECO_CUSTO_LOTE" not in df.columns:
        return pd.Series([0.0] * len(df))

    qtd_segura = df["QUANTIDADE"].apply(numero_para_float)
    preco_seguro = df["PRECO_CUSTO_LOTE"].apply(numero_para_float)
    return qtd_segura * preco_seguro


# ==========================================
# FUNÇÕES DE FORMATAÇÃO DE MOEDAS
# ==========================================


def formatar_moeda_auto(valor, moeda='BRL', casas_decimais=2):
    """Formata valor em moeda com suporte a casas decimais variáveis."""
    if moeda == 'BRL':
        valor_fmt = formatar_numero(valor, casas_decimais)
        return f"R$ {valor_fmt}"
    if moeda == 'USD':
        try:
            if isinstance(valor, str):
                valor = float(valor.replace(',', '.'))
            valor_fmt = f"{valor:,.{casas_decimais}f}"
            return f"US$ {valor_fmt}"
        except (ValueError, TypeError):
            return f"US$ 0{'.' + '0' * casas_decimais if casas_decimais > 0 else ''}"
    
    # Fallback para moedas não reconhecidas
    return f"{valor}"


def build_fato_lote(dim_estoque: pd.DataFrame, dim_produto: pd.DataFrame) -> pd.DataFrame:
    lote = ler_aba(2)
    lote_estoque = ler_aba(3)
    lote["LOTE"] = lote["LOTE"].astype(str).str.strip()
    lote_estoque["LOTE"] = lote_estoque["LOTE"].astype(str).str.strip()

    fato = lote.merge(lote_estoque, on="LOTE", how="left")

    if "ESTOQUE" in fato.columns:
        fato["ESTOQUE"] = fato["ESTOQUE"].astype(str).str.strip().str.replace(
            r"EST-(\d+)", lambda m: f"EST-{int(m.group(1)):03d}", regex=True
        )

    fato = fato.merge(dim_produto[["SKU", "NOME_PRODUTO", "GRUPO", "SUBGRUPO"]], left_on="SKU_MATERIAL", right_on="SKU",
                      how="left").drop(columns=["SKU"])
    fato = fato.merge(dim_estoque[["COD_ESTOQUE", "NOME_ESTOQUE", "NOME_FILIAL", "NOME_EMPRESA"]], left_on="ESTOQUE",
                      right_on="COD_ESTOQUE", how="left").drop(columns=["COD_ESTOQUE"])

    col_recebimento = "DATA_RECE_BIMENTO" if "DATA_RECE_BIMENTO" in fato.columns else "DATA_RECEBIMENTO"
    if col_recebimento in fato.columns:
        fato[col_recebimento] = normalizar_coluna_data(fato[col_recebimento])
    if "DATA_VENCIMENTO" in fato.columns:
        fato["DATA_VENCIMENTO"] = normalizar_coluna_data(fato["DATA_VENCIMENTO"])

    fato["VALOR_COMPRA"] = calcular_valor_compra(fato)
    return fato


def build_fato_baixa(baixa: pd.DataFrame, dim_estoque: pd.DataFrame, dim_produto: pd.DataFrame) -> pd.DataFrame:
    baixa["ESTOQUE_ID"] = baixa["ESTOQUE_ID"].astype(str).str.strip().str.replace(
        r"EST-(\d+)", lambda m: f"EST-{int(m.group(1)):03d}", regex=True
    )
    fato = baixa.merge(dim_estoque, left_on="ESTOQUE_ID", right_on="COD_ESTOQUE", how="left")
    fato = fato.merge(dim_produto, left_on="SKU_PRODUTO", right_on=dim_produto.columns[0], how="left")

    if "DATA_MOV" in fato.columns:
        fato["DATA_MOV"] = normalizar_coluna_data(fato["DATA_MOV"])
    return fato


def build_saldo_estoque(baixa: pd.DataFrame) -> pd.DataFrame:
    return baixa.groupby(["ESTOQUE_ID", "SKU_PRODUTO"])["QUANTIDADE"].sum().reset_index().rename(
        columns={"QUANTIDADE": "SALDO"})


def build_saldo_com_produto(saldo: pd.DataFrame, dim_produto: pd.DataFrame) -> pd.DataFrame:
    return saldo.merge(dim_produto[["SKU", "NOME_PRODUTO", "GRUPO", "SUBGRUPO"]], left_on="SKU_PRODUTO", right_on="SKU",
                       how="left").drop(columns=["SKU"])


def build_saldo_zerado(saldo_produto: pd.DataFrame) -> pd.DataFrame:
    zerado = saldo_produto[saldo_produto["SALDO"] == 0].copy()
    return pd.DataFrame({"TOTAL": [0]}) if zerado.empty else zerado


@st.cache_data
def carregar_dados_completos():
    with st.spinner("🔄 Carregando dados..."):
        dim_estoque = build_dim_estoque()
        dim_produto = build_dim_produto()
        baixa = build_baixa()

        fato_baixa = build_fato_baixa(baixa, dim_estoque, dim_produto)
        fato_lote = build_fato_lote(dim_estoque, dim_produto)
        saldo_estoque = build_saldo_estoque(baixa)
        saldo_produto = build_saldo_com_produto(saldo_estoque, dim_produto)
        saldo_zerado = build_saldo_zerado(saldo_produto)

        return fato_baixa, fato_lote, saldo_produto, saldo_zerado


# ==========================================
# MÓDULOS DE CÁLCULO INDEPENDENTES
# ==========================================

def classificar_lote(row) -> str:
    if pd.isna(row["DATA_VENCIMENTO"]):
        return "Mais de 150 dias"
    hoje = pd.Timestamp(datetime.now().date())
    dias_restantes = (row["DATA_VENCIMENTO"] - hoje).days
    if dias_restantes <= 90: return "Vence até 90 dias"
    if dias_restantes <= 120: return "Vence de 91 a 120 dias"
    if dias_restantes <= 150: return "Vence de 121 a 150 dias"
    return "Mais de 150 dias"


def get_skus_ativos(df_lotes: pd.DataFrame) -> tuple[int, int]:
    if df_lotes.empty: return 0, 0
    return df_lotes["SKU_MATERIAL"].nunique(), df_lotes["GRUPO"].nunique()


def get_produtos_saldo_negativo(df_lotes: pd.DataFrame) -> int:
    if df_lotes.empty: return 0
    qtd_numerica = df_lotes["QUANTIDADE"].apply(numero_para_float)
    return df_lotes[qtd_numerica < 0]["SKU_MATERIAL"].nunique()


def get_skus_vencendo(df_lotes: pd.DataFrame, dias: int = 90) -> int:
    if df_lotes.empty: return 0
    hoje = pd.Timestamp(datetime.now().date())
    datas_venc = pd.to_datetime(df_lotes["DATA_VENCIMENTO"], errors='coerce')
    lotes_vencendo = df_lotes[(datas_venc >= hoje) & ((datas_venc - hoje).dt.days <= dias)]
    return lotes_vencendo["SKU_MATERIAL"].nunique()


def get_proximo_vencimento(df_lotes: pd.DataFrame) -> str:
    if df_lotes.empty: return "N/A"
    hoje = pd.Timestamp(datetime.now().date())
    datas_venc = pd.to_datetime(df_lotes["DATA_VENCIMENTO"], errors='coerce')
    lotes_futuros = df_lotes[datas_venc >= hoje]
    if not lotes_futuros.empty:
        id_data_minima = lotes_futuros["DATA_VENCIMENTO"].min()
        if pd.notna(id_data_minima): return id_data_minima.strftime("%d/%m/%y")
    return "N/A"


def get_custo_total_estoque(df_lotes: pd.DataFrame) -> float:
    if df_lotes.empty: return 0.0
    valores = pd.to_numeric(df_lotes["VALOR_COMPRA"], errors='coerce').fillna(0)
    return float(valores.sum())


def calcular_aging_produtos(df_baixas: pd.DataFrame, df_lotes: pd.DataFrame) -> pd.DataFrame:
    if df_baixas.empty: return pd.DataFrame()
    hoje = pd.Timestamp(datetime.now().date())
    ultimo_mov = df_baixas.groupby("SKU_PRODUTO")["DATA_MOV"].max().reset_index()
    ultimo_mov.columns = ["SKU", "ULTIMA_DATA"]
    ultimo_mov["ULTIMA_DATA"] = pd.to_datetime(ultimo_mov["ULTIMA_DATA"], errors="coerce")
    ultimo_mov["DIAS_SEM_COMPRA"] = (hoje - ultimo_mov["ULTIMA_DATA"]).dt.days

    def categorizar_dias(dias):
        if pd.isna(dias): return "Mais de 120 dias"
        if dias <= 7: return "07 dias"
        if dias <= 15: return "08 a 15 dias"
        if dias <= 30: return "16 a 30 dias"
        if dias <= 45: return "31 a 45 dias"
        if dias <= 60: return "46 a 60 dias"
        if dias <= 90: return "61 a 90 dias"
        if dias <= 120: return "91 a 120 dias"
        return "Mais de 120 dias"

    ultimo_mov["FAIXA_SEM_COMPRA"] = ultimo_mov["DIAS_SEM_COMPRA"].apply(categorizar_dias)
    df_lotes["Q_NUM"] = df_lotes["QUANTIDADE"].apply(numero_para_float)
    estoque_atual = df_lotes.groupby("SKU_MATERIAL")["Q_NUM"].sum().reset_index().rename(
        columns={"SKU_MATERIAL": "SKU", "Q_NUM": "ESTOQUE_ATUAL"})

    df_aging = ultimo_mov.merge(estoque_atual, on="SKU", how="outer")
    df_aging["FAIXA_SEM_COMPRA"] = df_aging["FAIXA_SEM_COMPRA"].fillna("Mais de 120 dias")
    df_aging["ESTOQUE_ATUAL"] = df_aging["ESTOQUE_ATUAL"].fillna(0)
    df_aging["STATUS_GIRO"] = df_aging["ESTOQUE_ATUAL"].apply(lambda x: "Com Estoque" if x > 0 else "Sem Estoque")

    if not df_lotes.empty:
        df_prod_info = df_lotes[["SKU_MATERIAL", "NOME_PRODUTO", "GRUPO", "SUBGRUPO"]].drop_duplicates(
            subset=["SKU_MATERIAL"])
        df_aging = df_aging.merge(df_prod_info, left_on="SKU", right_on="SKU_MATERIAL", how="left").drop(
            columns=["SKU_MATERIAL"])
    return df_aging


def calcular_prazos_recebimento(df_lotes: pd.DataFrame) -> pd.DataFrame:
    if df_lotes.empty: return pd.DataFrame()
    df = df_lotes.copy()
    col_recebimento = "DATA_RECE_BIMENTO" if "DATA_RECE_BIMENTO" in df.columns else "DATA_RECEBIMENTO"
    if col_recebimento not in df.columns: return pd.DataFrame()

    hoje = pd.Timestamp(datetime.now().date())
    df[col_recebimento] = pd.to_datetime(df[col_recebimento], errors="coerce")
    df["DIAS_DIF"] = (df[col_recebimento] - hoje).dt.days

    def categorizar_recebimento(dias):
        if pd.isna(dias): return "Mais de 30 dias"
        if dias < -5: return "Atrasado > 5 dias"
        if dias < 0: return "Atrasado 1 a 4 dias"
        if dias == 0: return "Chega Hoje"
        if dias <= 3: return "Falta 1 a 3 dias"
        if dias <= 7: return "Falta 4 a 7 dias"
        if dias <= 20: return "Falta 10 a 20 dias"
        if dias <= 30: return "Falta 21 a 30 dias"
        return "Mais de 30 dias"

    df["FAIXA_RECEBIMENTO"] = df["DIAS_DIF"].apply(categorizar_recebimento)
    return df


# ==========================================
# CONFIGURAÇÃO DA INTERFACE WEB
# ==========================================
st.set_page_config(page_title="Executive Dashboard | Estoque", layout="wide")

# Executa e armazena as cores dinâmicas da empresa
cores = render_page()

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stDataFrame { font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

st.title("📊 Painel Executivo de Lotes & Estoque")

fato_baixa, fato_lote, saldo_produto, saldo_zerado = carregar_dados_completos()

if fato_lote.empty:
    st.error("❌ Nenhum dado de lote foi carregado. Verifique o arquivo Excel.")
    st.stop()

if "VALOR_COMPRA" not in fato_lote.columns:
    fato_lote["VALOR_COMPRA"] = calcular_valor_compra(fato_lote)

if "DATA_MOV" in fato_baixa.columns:
    fato_baixa["MES"] = fato_baixa["DATA_MOV"].dt.strftime("%m/%Y")
else:
    fato_baixa["MES"] = "01/2024"

# ==========================================
# SELEÇÃO DE MOEDA
# ==========================================
col_moeda1, col_moeda2, col_moeda3 = st.columns([1, 1, 4])
with col_moeda1:
    moeda_selecionada = st.selectbox("💰 Moeda", ["BRL (Real)", "USD (Dólar)"], index=0)
    moeda_codigo = moeda_selecionada.split()[0]

# ==========================================
# FILTROS
# ==========================================
st.markdown("### 🔎 Parâmetros de Busca")
l1_col1, l1_col2, l1_col3 = st.columns(3)

with l1_col1:
    lista_empresas = ["Todos"] + sorted(fato_lote["NOME_EMPRESA"].dropna().unique().tolist())
    empresa_sel = st.selectbox("Empresa", lista_empresas)
with l1_col2:
    lista_filiais = ["Todos"] + sorted(fato_lote["NOME_FILIAL"].dropna().unique().tolist())
    filial_sel = st.selectbox("Filial", lista_filiais)
with l1_col3:
    lista_estoques = ["Todos"] + sorted(fato_lote["NOME_ESTOQUE"].dropna().unique().tolist())
    estoque_sel = st.selectbox("Canal de Estoque", lista_estoques)

l2_col1, l2_col2, l2_col3 = st.columns(3)

with l2_col1:
    lista_grupos = ["Todos"] + sorted(fato_lote["GRUPO"].dropna().unique().tolist())
    grupo_sel = st.selectbox("Grupo de Mercadoria", lista_grupos)
with l2_col2:
    lista_subgrupos = ["Todos"] + sorted(fato_lote["SUBGRUPO"].dropna().unique().tolist())
    subgrupo_sel = st.selectbox("Subgrupo", lista_subgrupos)
with l2_col3:
    fato_lote["PRODUTO_DISPLAY"] = fato_lote["NOME_PRODUTO"].astype(str) + " (" + fato_lote["SKU_MATERIAL"].astype(
        str) + ")"
    lista_produtos_busca = sorted(fato_lote["PRODUTO_DISPLAY"].dropna().unique().tolist())
    produtos_selecionados = st.multiselect("Pesquisa Avançada por Produto", options=lista_produtos_busca)

# ==========================================
# APLICAÇÃO DOS FILTROS
# ==========================================
lotes_filtrados = fato_lote.copy()
baixas_filtradas = fato_baixa.copy()

if empresa_sel != "Todos":
    lotes_filtrados = lotes_filtrados[lotes_filtrados["NOME_EMPRESA"] == empresa_sel]
    baixas_filtradas = baixas_filtradas[baixas_filtradas["NOME_EMPRESA"] == empresa_sel]

if filial_sel != "Todos":
    lotes_filtrados = lotes_filtrados[lotes_filtrados["NOME_FILIAL"] == filial_sel]
    baixas_filtradas = baixas_filtradas[baixas_filtradas["NOME_FILIAL"] == filial_sel]

if estoque_sel != "Todos":
    lotes_filtrados = lotes_filtrados[lotes_filtrados["NOME_ESTOQUE"] == estoque_sel]
    baixas_filtradas = baixas_filtradas[baixas_filtradas["NOME_ESTOQUE"] == estoque_sel]

if grupo_sel != "Todos":
    lotes_filtrados = lotes_filtrados[lotes_filtrados["GRUPO"] == grupo_sel]
    baixas_filtradas = baixas_filtradas[baixas_filtradas["GRUPO"] == grupo_sel]

if subgrupo_sel != "Todos":
    lotes_filtrados = lotes_filtrados[lotes_filtrados["SUBGRUPO"] == subgrupo_sel]
    baixas_filtradas = baixas_filtradas[baixas_filtradas["SUBGRUPO"] == subgrupo_sel]

if produtos_selecionados:
    lotes_filtrados = lotes_filtrados[lotes_filtrados["PRODUTO_DISPLAY"].isin(produtos_selecionados)]
    skus_selecionados = [texto.split("(")[-1].replace(")", "").strip() for texto in produtos_selecionados]
    baixas_filtradas = baixas_filtradas[baixas_filtradas["SKU_PRODUTO"].isin(skus_selecionados)]

# ==========================================
# MÉTRICAS DOS CARDS (CORES DINÂMICAS INTEGRADAS)
# ==========================================
v_skus, v_cats = get_skus_ativos(lotes_filtrados)
v_negativos = get_produtos_saldo_negativo(lotes_filtrados)
v_vencendo = get_skus_vencendo(lotes_filtrados, dias=90)
v_prox_data = get_proximo_vencimento(lotes_filtrados)
v_custo_total = get_custo_total_estoque(lotes_filtrados)

st.markdown("---")
card_col1, card_col2, card_col3, card_col4 = st.columns(4)

html_card_template = """
<div class='card-style' style="border-top: 4px solid {color};">
    <div class= style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 8px;">{title}</div>
    <div class= style="font-size: 28px ; font-weight: 700; color: #f8fafc; line-height: 1.1; margin-bottom: 6px;">{value}</div>
    <div class= style="font-size: 12px; color: {subcolor};">{subtext}</div>
</div>
"""

with card_col1:
    st.markdown(html_card_template.format(
        title="SKUs Ativos", value=f"{v_skus:,}".replace(",", "."),
        subtext=f"📦 Distribuídos em {v_cats} categorias", color=cores["primaria"], subcolor=cores["secundaria"]
    ), unsafe_allow_html=True)

with card_col2:
    color_alert = cores["cor_alerta_vermelho"] if v_negativos > 0 else cores["cor_alerta_verde"]
    sub_alert = "⚠️ ação necessária" if v_negativos > 0 else "✅ nível regularizado"
    st.markdown(html_card_template.format(
        title="Estoque Crítico Negativo", value=v_negativos,
        subtext=sub_alert, color=color_alert, subcolor=color_alert
    ), unsafe_allow_html=True)

with card_col3:
    st.markdown(html_card_template.format(
        title="Risco de Vencimento (90d)", value=v_vencendo,
        subtext=f"📅 Próximo vencimento: {v_prox_data}", color=cores["cor_alerta_vermelho"],
        subcolor=cores["cor_alerta_vermelho"]
    ), unsafe_allow_html=True)

with card_col4:
    valor_formatado_card = f"R$ {formatar_numero(v_custo_total, 2)}" if moeda_codigo == 'BRL' else dolar(v_custo_total, simbolo=True)
    st.markdown(html_card_template.format(
        title="Patrimônio em Estoque", value=valor_formatado_card,
        subtext="💰 Capital total alocado por lote", color=cores["cor_alerta_verde"],
        subcolor=cores["cor_alerta_verde"]
    ), unsafe_allow_html=True)

# ==========================================
# GRÁFICOS
# ==========================================
st.markdown("---")
st.header("📦 Recebimentos e Movimentações")

g_col1, g_col2, g_col3 = st.columns([1.3, 1.3, 1.2])

df_recebimento = calcular_prazos_recebimento(lotes_filtrados)
df_aging = calcular_aging_produtos(baixas_filtradas, lotes_filtrados)
with g_col1:
    with st.container(border=True, gap="xsmall"):
        st.subheader("⏱️ Histórico de Inatividade (Aging)")
        if not df_aging.empty:
            ordem_faixas = ["07 dias", "08 a 15 dias", "16 a 30 dias", "31 a 45 dias", "46 a 60 dias", "61 a 90 dias",
                            "91 a 120 dias", "Mais de 120 dias"]
            df_agrupado_aging = df_aging.groupby(["FAIXA_SEM_COMPRA", "STATUS_GIRO"])["SKU"].nunique().reset_index()

            fig1 = px.bar(
                df_agrupado_aging,
                x="FAIXA_SEM_COMPRA",
                y="SKU", color="STATUS_GIRO", barmode="stack",
                category_orders={"FAIXA_SEM_COMPRA": ordem_faixas},
                color_discrete_map={"Com Estoque": cores["cor_alerta_verde"],
                                    "Sem Estoque": cores["cor_alerta_vermelho"]},
                text_auto=True
            )

            fig1.update_traces(
                opacity=0.85,
                texttemplate='%{y}',
                textposition='inside',
                insidetextanchor='middle',  # Centraliza o número perfeitamente na barra
                textfont=dict(family="sans-serif", size=11, color=cores["sidebar_texto"])
            )

            fig1.update_layout(
                template="plotly_dark",
               # paper_bgcolor="#1e293b",
               # plot_bgcolor="#1e293b",
                height=450,
                xaxis_title="",
                yaxis_title="",
                margin=dict(b=40, l=15, r=15, t=60),
                xaxis=dict(showgrid=False, tickfont=dict(size=10, color=cores["sidebar_texto"]),),
                yaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False,
                           tickfont=dict(color=cores['sidebar_texto'])),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    xanchor="center",
                    x=0.5,
                    title_text=""
                )
            )
            st.plotly_chart(fig1, use_container_width=True)
        else:
            st.info("Sem dados para cálculo de Aging.")

with g_col2:
    with st.container(border=True, gap="xsmall"):
        st.subheader("🚚 Linha do Tempo: Pedidos a Receber")
        if not df_recebimento.empty:
            df_grafico2 = df_recebimento.groupby("FAIXA_RECEBIMENTO")["LOTE"].nunique().reset_index()
            ordem_recebimento = ["Atrasado > 5 dias", "Atrasado 1 a 4 dias", "Chega Hoje", "Falta 1 a 3 dias",
                                 "Falta 4 a 7 dias", "Falta 10 a 20 dias", "Falta 21 a 30 dias", "Mais de 30 dias"]

            fig2 = px.bar(
                df_grafico2,
                x="LOTE",
                y="FAIXA_RECEBIMENTO",
                orientation="h",
                color="FAIXA_RECEBIMENTO",
                category_orders={"FAIXA_RECEBIMENTO": ordem_recebimento},
                color_continuous_scale=px.colors.sequential.Viridis,
                text_auto=True
            )

            fig2.update_traces(
                opacity=0.85,
                texttemplate='%{x}',
                textposition='inside',
                insidetextanchor='middle',
                textfont=dict(family="sans-serif", size=11, color=cores['sidebar_texto']),
                cliponaxis=False
            )

            fig2.update_layout(
                template="plotly_dark",
               # paper_bgcolor="#1e293b",
               # plot_bgcolor="#1e293b",
                height=450,
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                margin=dict(b=20, l=15, r=20, t=20),
                xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False,
                           tickfont=dict(color=cores['sidebar_texto'])),
                yaxis=dict(showgrid=False, tickfont=dict(size=11, color=cores['sidebar_texto']))
            )
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("Nenhum pedido pendente.")

with g_col3:
    with st.container(border=True, gap="xsmall"):
        st.subheader("📊 Valor Futuro & Risco")

        # Primeiro Gráfico (Top) - Pedidos a Entregar
        if not df_recebimento.empty:
            df_valores_grupo = df_recebimento.copy()
            df_valores_grupo["VALOR_FINANCEIRO"] = df_valores_grupo["VALOR_COMPRA"]
            df_filtrado_futuro = df_valores_grupo[
                ~df_valores_grupo["FAIXA_RECEBIMENTO"].str.contains("Atrasado")].copy()

            if not df_filtrado_futuro.empty:
                df_grupo_final = df_filtrado_futuro.groupby("GRUPO")[
                    "VALOR_FINANCEIRO"].sum().reset_index().sort_values(by="VALOR_FINANCEIRO", ascending=True)
                df_grupo_final = df_grupo_final[df_grupo_final["VALOR_FINANCEIRO"] > 0]

                if not df_grupo_final.empty:
                    fig3_top = px.bar(
                        df_grupo_final,
                        x="VALOR_FINANCEIRO",
                        y="GRUPO",
                        orientation="h",
                        title="Pedidos a Entregar",
                        text_auto=True
                    )

                    fig3_top.update_traces(
                        marker_color=cores["cor_alerta_verde"],
                        opacity=0.85,
                        texttemplate='%{x:,.0f}',
                        textposition='inside',
                        insidetextanchor='middle',
                        textangle=0,
                        textfont=dict(family="sans-serif", size=11, color=cores['sidebar_texto']) # Texto escuro para destacar na barra verde claro
                    )

                    fig3_top.update_layout(
                        template="plotly_dark",
                      #  paper_bgcolor="#1e293b",
                      #  plot_bgcolor="#1e293b",
                        height=210,
                        xaxis_title="",
                        yaxis_title="",
                        margin=dict(b=15, l=15, r=15, t=40),
                        xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False,
                                   tickfont=dict(color=cores['sidebar_texto'])),
                        yaxis=dict(showgrid=False, tickfont=dict(size=11, color=cores['sidebar_texto']))
                    )
                    st.plotly_chart(fig3_top, use_container_width=True)

        # Segundo Gráfico (Bottom) - Lotes por Risco
        if not lotes_filtrados.empty:
            df_lotes_t = lotes_filtrados.copy()
            df_lotes_t["STATUS_VENC"] = df_lotes_t.apply(classificar_lote, axis=1)
            df_status_v = df_lotes_t.groupby("STATUS_VENC")["LOTE"].nunique().reset_index().rename(
                columns={"STATUS_VENC": "STATUS_VENC", "LOTE": "QTD_LOTES"})
            ordem_vencimento = ["Vence até 90 dias", "Vence de 91 a 120 dias", "Vence de 121 a 150 dias",
                                "Mais de 150 dias"]

            fig3_bottom = px.bar(
                df_status_v,
                x="QTD_LOTES",
                y="STATUS_VENC",
                orientation="h",
                title="Lotes por Risco",
                color="STATUS_VENC",
                category_orders={"STATUS_VENC": ordem_vencimento},
                color_discrete_map={
                    "Vence até 90 dias": cores["cor_alerta_vermelho"],
                    "Vence de 91 a 120 dias": cores["cor_alerta_amarelo"],
                    "Vence de 121 a 150 dias": "#3b82f6",
                    "Mais de 150 dias": cores["cor_alerta_verde"]
                },
                text_auto=True
            )

            fig3_bottom.update_traces(
                opacity=0.85,
                texttemplate='%{x}',
                textposition='inside',
                insidetextanchor='middle',
                textangle=0,
                textfont=dict(family="sans-serif", size=11, color="#ffffff")
            )

            fig3_bottom.update_layout(
                template="plotly_dark",
               # paper_bgcolor="#1e293b",
               # plot_bgcolor="#1e293b",
                height=230,
                xaxis_title="",
                yaxis_title="",
                showlegend=False,
                margin=dict(b=20, l=15, r=15, t=40),
                xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False,
                           tickfont=dict(color=cores['sidebar_texto'])),
                yaxis=dict(showgrid=False, tickfont=dict(size=11, color=cores['sidebar_texto']))
            )
            st.plotly_chart(fig3_bottom, use_container_width=True)
# ==========================================
# EVOLUÇÃO E MOVIMENTAÇÕES
# ==========================================
st.markdown("---")
st.header("📦 Movimentações de Estoque")

if not baixas_filtradas.empty:
    df_mov_prep = baixas_filtradas.copy()
    df_mov_prep["QTD_NUMERICA"] = df_mov_prep["QUANTIDADE"].apply(numero_para_float)

    # =========================================================
    # CONTAINER 1: Exclusivo para o Gráfico de Linha (Evolução)
    # =========================================================
    with st.container(border=True, gap="xsmall"):
        st.subheader("📈 Evolução Mensal de Baixas")
        df_mensal = df_mov_prep.groupby("MES")["QTD_NUMERICA"].sum().reset_index().sort_values("MES")
        if not df_mensal.empty:
            fig_m1 = px.line(
                df_mensal,
                x="MES",
                y="QTD_NUMERICA",
                markers=True,
                color_discrete_sequence=[cores["primaria"]]
            )
            fig_m1.update_layout(
                template="plotly_dark",
                height=300,
                xaxis_title="",
                yaxis_title="",
                xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False,
                           tickfont=dict(color=cores['sidebar_texto'])),
                yaxis=dict(showgrid=True, tickfont=dict(size=11, color=cores['sidebar_texto'])),
                margin=dict(b=40, l=50, r=20, t=60),  # Aumentado t=60 para dar espaço à legenda
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    xanchor="center",
                    x=0.5,
                    title_text=""
                )
            )
            st.plotly_chart(fig_m1, use_container_width=True)

    # Adiciona um pequeno espaço antes da linha de colunas
    st.markdown("<br>", unsafe_allow_html=True)

    # Criamos as colunas fora do container de cima
    m_col1, m_col2, m_col3 = st.columns(3)

    # =========================================================
    # COLUNA 1: Top Grupos com Maior Saída
    # =========================================================
    with m_col1:
        with st.container(border=True, gap="xsmall"):
            st.subheader("👑 Top Grupos com Maior Saída")
            df_top_g = df_mov_prep.groupby("GRUPO")["QTD_NUMERICA"].sum().reset_index().sort_values("QTD_NUMERICA",
                                                                                                    ascending=True).tail(
                10)

            if not df_top_g.empty:
                fig_m2 = px.bar(
                    df_top_g,
                    x="QTD_NUMERICA",
                    y="GRUPO",
                    orientation="h",
                    title="",
                    color_discrete_sequence=[cores["cor_alerta_amarelo"]],
                    text_auto=True
                )
                fig_m2.update_layout(
                    template="plotly_dark",
                    height=380,
                    xaxis_title="",
                    yaxis_title="",
                    margin=dict(b=30, l=50, r=40, t=60),  # Aumentado t=60 para manter padrão visual
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    ),
                    xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False,
                           tickfont=dict(color=cores['sidebar_texto'])),
                    yaxis=dict(showgrid=True, tickfont=dict(size=11, color=cores['sidebar_texto'])),
                )
                fig_m2.update_traces(
                    texttemplate='%{x}',
                    textposition='outside',
                    textangle=0,
                    cliponaxis=False
                )
                st.plotly_chart(fig_m2, use_container_width=True)

    # =========================================================
    # COLUNA 2: Distribuição por Canal
    # =========================================================
    with m_col2:
        with st.container(border=True, gap="xsmall"):
            st.subheader("🏢 Distribuição por Canal")
            df_canal_m = df_mov_prep.groupby("NOME_ESTOQUE")["QTD_NUMERICA"].sum().reset_index()

            if not df_canal_m.empty:
                fig_m3 = px.pie(df_canal_m, values="QTD_NUMERICA", names="NOME_ESTOQUE", hole=0.4)
                fig_m3.update_layout(
                    template="plotly_dark",
                    height=380,
                    margin=dict(b=20, l=20, r=20, t=60),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    )
                )
                st.plotly_chart(fig_m3, use_container_width=True)

    # =========================================================
    # COLUNA 3: Top Produtos Mais Ociosos
    # =========================================================
    with m_col3:
        with st.container(border=True, gap="xsmall"):
            st.subheader("⚠️ Top Produtos Mais Ociosos")
            if not df_aging.empty:
                df_parados_90 = df_aging[(df_aging["STATUS_GIRO"] == "Com Estoque") & (
                        (df_aging["DIAS_SEM_COMPRA"] > 90) | (
                    df_aging["FAIXA_SEM_COMPRA"].isin(["91 a 120 dias", "Mais de 120 dias"])))]

                if not df_parados_90.empty:
                    df_grafico_alerta = df_parados_90.sort_values(by="DIAS_SEM_COMPRA", ascending=True).tail(10)
                    fig_alerta = px.bar(
                        df_grafico_alerta,
                        x="DIAS_SEM_COMPRA",
                        y="NOME_PRODUTO",
                        orientation="h",
                        color="DIAS_SEM_COMPRA",
                      #  title="⚠️ Top Produtos Mais Ociosos (Dias Inativo)",  # ← Texto agora fica no topo
                        color_continuous_scale=[cores["cor_alerta_amarelo"],
                                                cores["cor_alerta_vermelho"]],
                        text_auto=True
                    )
                    fig_alerta.update_layout(
                        template="plotly_dark",
                        height=380,
                        xaxis_title="",
                        yaxis_title="",
                        coloraxis_showscale=False,
                        showlegend=False,
                        margin=dict(b=30, l=50, r=40, t=50),
                        xaxis=dict(showgrid=True, gridcolor="rgba(255, 255, 255, 0.05)", zeroline=False,
                           tickfont=dict(color=cores['sidebar_texto'])),
                        yaxis=dict(showgrid=True, tickfont=dict(size=11, color=cores['sidebar_texto'])),
                    )
                    fig_alerta.update_traces(
                        texttemplate='%{x}',
                        textposition='outside',
                        textangle=0,
                        cliponaxis=False
                    )
                    st.plotly_chart(fig_alerta, use_container_width=True)
else:
    st.info("Nenhum registro de movimentação encontrado.")
# ==========================================
# 📋 TABELA ANALÍTICA DE COMPRAS
# ==========================================
st.markdown("---")
st.subheader("📋 Análise de Estoque e Sugestão de Compras")

if not lotes_filtrados.empty and not baixas_filtradas.empty:
    # 1. Processamento Base dos Dados
    estoque_atual = lotes_filtrados.groupby("SKU_MATERIAL").agg({
        "QUANTIDADE": "sum", "VALOR_COMPRA": "sum", "NOME_PRODUTO": "first", "GRUPO": "first", "SUBGRUPO": "first"
    }).reset_index().rename(columns={"SKU_MATERIAL": "SKU"})

    saidas_produtos = baixas_filtradas.groupby("SKU_PRODUTO").agg({
        "QUANTIDADE": "sum", "DATA_MOV": ["count", "max"]
    }).reset_index()
    saidas_produtos.columns = ["SKU", "SAIDAS_TOTAIS", "QTD_MOVIMENTACOES", "ULTIMA_SAIDA"]

    df_analise = estoque_atual.merge(saidas_produtos, on="SKU", how="left")
    df_analise["SAIDAS_TOTAIS"] = df_analise["SAIDAS_TOTAIS"].fillna(0)
    df_analise["QTD_MOVIMENTACOES"] = df_analise["QTD_MOVIMENTACOES"].fillna(0)

    # 2. Cálculo de Média de Consumo (Últimos 90 dias)
    hoje = pd.Timestamp(datetime.now().date())
    baixas_90dias = baixas_filtradas[
        pd.to_datetime(baixas_filtradas["DATA_MOV"]) >= (hoje - pd.Timedelta(days=90))].copy()

    media_consumo = baixas_90dias.groupby("SKU_PRODUTO")["QUANTIDADE"].sum().reset_index().rename(
        columns={"SKU_PRODUTO": "SKU"})
    media_consumo["MEDIA_DIARIA"] = media_consumo["QUANTIDADE"] / 90.0

    df_analise = df_analise.merge(media_consumo[["SKU", "MEDIA_DIARIA"]], on="SKU", how="left").fillna(0)

    # 3. Regras de Negócio: Cobertura e Sugestão de Compra
    df_analise["COBERTURA_DIAS"] = np.where(df_analise["MEDIA_DIARIA"] > 0,
                                            df_analise["QUANTIDADE"] / df_analise["MEDIA_DIARIA"], 999)
    df_analise["SUGESTAO_COMPRA"] = np.where(df_analise["COBERTURA_DIAS"] < 30,
                                             (df_analise["MEDIA_DIARIA"] * 45) - df_analise["QUANTIDADE"], 0)
    df_analise["SUGESTAO_COMPRA"] = df_analise["SUGESTAO_COMPRA"].clip(lower=0).round(0)


    # Criando a coluna de cenários do estoque
    def definir_status_cenario(linha):
        if linha["MEDIA_DIARIA"] == 0 and linha["QUANTIDADE"] > 0:
            return "⚠️ Sem Giro (Estoque Parado)"
        elif linha["QUANTIDADE"] == 0:
            return "🚨 Estoque Zerado"
        elif linha["COBERTURA_DIAS"] < 15:
            return "🔴 Crítico (Menos de 15 dias)"
        elif linha["COBERTURA_DIAS"] < 30:
            return "🟡 Atenção (Abaixo do Mínimo)"
        elif linha["COBERTURA_DIAS"] <= 60:
            return "🟢 Confortável (Dentro do Estimado)"
        else:
            return "🔵 Sobra (Alta Cobertura)"


    df_analise["STATUS_ESTOQUE"] = df_analise.apply(definir_status_cenario, axis=1)

    # =========================================================
    # FILTROS FORA DA TABELA: Dinâmicos e Acumulativos
    # =========================================================
    f_row1_col1, f_row1_col2 = st.columns(2)
    f_row2_col1, f_row2_col2 = st.columns(2)

    df_filtrando = df_analise.copy()

    # 1. Filtro de Grupo
    with f_row1_col1:
        lista_grupos = ["Todos"] + sorted(df_filtrando["GRUPO"].dropna().unique().tolist())
        grupo_selecionado = st.selectbox("1. Filtrar por Grupo:", lista_grupos)
        if grupo_selecionado != "Todos":
            df_filtrando = df_filtrando[df_filtrando["GRUPO"] == grupo_selecionado]

    # 2. Filtro de Status (Cenário)
    with f_row1_col2:
        lista_status = ["Todos"] + sorted(df_filtrando["STATUS_ESTOQUE"].unique().tolist())
        status_selecionado = st.selectbox("2. Filtrar por Cenário do Estoque:", lista_status)
        if status_selecionado != "Todos":
            df_filtrando = df_filtrando[df_filtrando["STATUS_ESTOQUE"] == status_selecionado]

    # 3. Filtro de SKU (A pessoa pode ir digitando)
    with f_row2_col1:
        lista_skus = sorted(df_filtrando["SKU"].dropna().unique().tolist())
        skus_selecionados = st.multiselect("3. Digite ou selecione o SKU:", options=lista_skus,
                                           placeholder="Busque pelo SKU...")
        if skus_selecionados:
            df_filtrando = df_filtrando[df_filtrando["SKU"].isin(skus_selecionados)]

    # 4. Filtro de Produto (A pessoa pode ir digitando o nome)
    with f_row2_col2:
        lista_produtos = sorted(df_filtrando["NOME_PRODUTO"].dropna().unique().tolist())
        produtos_selecionados = st.multiselect("4. Digite ou selecione o Produto:", options=lista_produtos,
                                               placeholder="Busque pelo nome do produto...")
        if produtos_selecionados:
            df_filtrando = df_filtrando[df_filtrando["NOME_PRODUTO"].isin(produtos_selecionados)]

    df_filtrado_tabela = df_filtrando

    # Adiciona um pequeno espaço separando os filtros da tabela
    st.markdown("<br>", unsafe_allow_html=True)

    # =========================================================
    # CONTAINER DA TABELA COM ESTILIZAÇÃO DE CORES DINÂMICAS
    # =========================================================
    with st.container(border=True, gap="xsmall"):
        st.markdown("##### 📊 Detalhamento de Cobertura e Sugestões")

        colunas_exibicao = [
            "SKU", "NOME_PRODUTO", "GRUPO", "STATUS_ESTOQUE",
            "QUANTIDADE", "MEDIA_DIARIA", "COBERTURA_DIAS", "SUGESTAO_COMPRA"
        ]

        # Prepara o DataFrame final apenas com as colunas selecionadas
        df_tabela_final = df_filtrado_tabela[colunas_exibicao].copy()


        # Função interna que mapeia e colore a linha inteira dependendo do cenário
        def aplicar_estilo_cenario(row):
            status = row["STATUS_ESTOQUE"]
            # Estilo padrão nulo (mantém o CSS original do Streamlit)
            estilo = [''] * len(row)

            # Alerta Vermelho: Estoque Zerado ou Crítico
            if "🚨 Estoque Zerado" in status or "🔴 Crítico" in status:
                return [
                    f'background-color: {cores["cor_alerta_vermelho"]}; color: #ffffff; font-weight: bold;'] * len(
                    row)

            # Alerta Amarelo: Sem Giro ou Cobertura em Atenção
            elif "⚠️ Sem Giro" in status or "🟡 Atenção" in status:
                return [
                    f'background-color: {cores["cor_alerta_amarelo"]}; color: #000000; font-weight: bold;'] * len(
                    row)

            return estilo


        # Aplica a estilização construída linha por linha (axis=1)
        df_estilizado = df_tabela_final.style.apply(aplicar_estilo_cenario, axis=1)

        st.dataframe(
            df_estilizado,
            column_config={
                "SKU": st.column_config.TextColumn("SKU"),
                "NOME_PRODUTO": st.column_config.TextColumn("Produto"),
                "GRUPO": st.column_config.TextColumn("Grupo"),
                "STATUS_ESTOQUE": st.column_config.TextColumn("Cenário do Estoque"),
                "QUANTIDADE": st.column_config.NumberColumn("Qtd. Atual", format="%d"),
                "MEDIA_DIARIA": st.column_config.NumberColumn("Média Diária", format="%.2f"),
                "COBERTURA_DIAS": st.column_config.NumberColumn("Cobertura (Dias)", format="%d"),
                "SUGESTAO_COMPRA": st.column_config.NumberColumn("Sugestão Compra", format="%d")
            },
            use_container_width=True,
            hide_index=True
        )
else:
    st.info("Dados insuficientes de lotes ou baixas para gerar a análise de sugestão de compras.")