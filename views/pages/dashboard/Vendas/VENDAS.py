import os
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
from datetime import datetime

from helpers.formata import normalizar_coluna_data
import re
import warnings
from controller.empresaController import EmpresaController
from controller.loginController import LoginController
from controller.token_controller import TokenController
from helpers.formata import converter_para_float_seguro, reais
from helpers.tema import obter_cor_alerta, obter_tema_empresa
warnings.filterwarnings('ignore')

load_dotenv()

# Arquivo de origem (sua base de dados original)
caminho_base = Path(os.getenv("PATH_TESTES_ARQUIVOS"))
arquivo_origem = caminho_base / "TESTES GUSTAVO.xlsx"
def render_page(login_controller=None):
    login_ctrl = LoginController()
    empresa_ctrl = EmpresaController()
    token_ctrl = TokenController()
    tema_completo = obter_tema_empresa()
    """Busca e retorna as cores configuradas para o tema da empresa."""
    tema_completo = obter_tema_empresa()
    if not st.session_state.get("auth_token"):
        st.session_state.pagina_atual = "login"
        st.rerun()
        st.stop()
    return {
        "primaria": tema_completo['tema_primario'],
        "secundaria": tema_completo['tema_secundario'],
        "sidebar_fundo": tema_completo['sidebar_fundo'],
        "sidebar_texto": tema_completo['sidebar_texto'],
        "cor_alerta_alerta_vermelho": obter_cor_alerta("vermelho"),
        "cor_alerta_alerta_amarelo": obter_cor_alerta("amarelo"),
        "cor_alerta_alerta_verde": obter_cor_alerta("verde")
    }


def listar_abas() -> list[str]:
    xl = pd.ExcelFile(arquivo_origem)
    return xl.sheet_names


def aplicar_trim_em_texto(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica trim em todas as colunas de texto do DataFrame
    Remove espaços no início, fim e espaços duplicados internos
    """
    for col in df.columns:
        if df[col].dtype == 'object':  # Colunas de texto
            # Converte para string, remove espaços nas pontas e espaços duplicados
            df[col] = df[col].astype(str).str.strip().str.replace(r'\s+', ' ', regex=True)
            # Substitui 'nan' por NaN
            df[col] = df[col].replace('nan', pd.NA)
            # Remove linhas que ficaram vazias
            df[col] = df[col].replace('', pd.NA)
    return df


def ler_aba(indice: int, aplicar_trim: bool = True) -> pd.DataFrame:
    """Lê uma aba do Excel e opcionalmente aplica trim nas colunas de texto"""
    abas = listar_abas()
    aba = abas[indice]
    df = pd.read_excel(arquivo_origem, sheet_name=aba)
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    df = df.dropna(how="all")

    if aplicar_trim:
        df = aplicar_trim_em_texto(df)

    return df


def build_dim_planoContas() -> pd.DataFrame:
    return ler_aba(13)


def build_dim_CentroCusto() -> pd.DataFrame:
    """Constrói a dimensão de Centro de Custo com TRIM"""
    df = ler_aba(9)

    # Renomear colunas e aplicar trim
    df = df.rename(columns={
        "ID_CENTRO_CUSTO": "COD_CC",
        "CENTRO_DE_CUSTO": "NOME_CENTRO_CUSTO"
    })

    # Aplicar trim específico nas colunas de interesse
    if "COD_CC" in df.columns:
        df["COD_CC"] = df["COD_CC"].astype(str).str.strip()
        # Padronizar formato CC-XXX
        df["COD_CC"] = df["COD_CC"].str.replace(
            r"CC-(\d+)",
            lambda m: f"CC-{int(m.group(1)):03d}",
            regex=True
        )

    if "NOME_CENTRO_CUSTO" in df.columns:
        df["NOME_CENTRO_CUSTO"] = df["NOME_CENTRO_CUSTO"].astype(str).str.strip()

    return df


def build_dim_Empresa() -> pd.DataFrame:
    """Constrói a dimensão de Empresa com TRIM"""
    d_estoque = ler_aba(4)
    estoque_filial = ler_aba(5)
    d_filial = ler_aba(6)
    empresa_filial = ler_aba(7)
    d_empresa = ler_aba(8)
    d_centro_custo = build_dim_CentroCusto()  # Usa a dimensão já com trim

    # Renomear colunas
    d_estoque = d_estoque.rename(columns={"COD-ESTOQUE": "COD_ESTOQUE"})
    d_filial = d_filial.rename(columns={"ID": "COD_FILIAL", "NOME_FILIAL": "NOME_FILIAL"})
    d_empresa = d_empresa.rename(columns={"ID": "COD_EMPRESA", "EMPRESA": "NOME_EMPRESA"})

    # Aplicar trim nas colunas chave
    for df_temp in [estoque_filial, d_estoque, empresa_filial, d_filial, d_empresa]:
        for col in ["COD_ESTOQUE", "COD_FILIAL", "COD_EMPRESA", "COD_CC"]:
            if col in df_temp.columns:
                df_temp[col] = df_temp[col].astype(str).str.strip()

    # Realizar merges
    dim = estoque_filial.merge(d_estoque, on="COD_ESTOQUE", how="left")
    dim = dim.merge(empresa_filial, on="COD_FILIAL", how="left")
    dim = dim.merge(d_filial, on="COD_FILIAL", how="left")
    dim = dim.merge(d_empresa, on="COD_EMPRESA", how="left")

    # Merge com centro de custo
    if "COD_CC" in dim.columns:
        dim["COD_CC"] = dim["COD_CC"].astype(str).str.strip()
        dim = dim.merge(d_centro_custo, on="COD_CC", how="left")
    else:
        dim = dim.merge(d_centro_custo, how="cross")  # Fallback

    # Padronizar códigos
    if "COD_ESTOQUE" in dim.columns:
        dim["COD_ESTOQUE"] = dim["COD_ESTOQUE"].astype(str).str.replace(
            r"EST-(\d+)", lambda m: f"EST-{int(m.group(1)):03d}", regex=True
        )

    if "COD_CC" in dim.columns:
        dim["COD_CC"] = dim["COD_CC"].astype(str).str.replace(
            r"CC-(\d+)", lambda m: f"CC-{int(m.group(1)):03d}", regex=True
        )

    return dim


def build_dim_produto() -> pd.DataFrame:
    """Constrói a dimensão de Produto com TRIM"""
    df = ler_aba(0)

    # Aplicar trim nas colunas de texto
    for col in ["SKU", "NOME_PRODUTO", "GRUPO", "SUBGRUPO"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()

    return df


def build_fato_vendas(dim_produto: pd.DataFrame, dim_empresa: pd.DataFrame) -> pd.DataFrame:
    """Constrói a fato de vendas com TRIM em todas as colunas de texto"""
    fato_vendas = ler_aba(10)

    # Aplicar trim específico nas colunas chave
    if "SKU_PRODUTO" in fato_vendas.columns:
        fato_vendas["SKU_PRODUTO"] = fato_vendas["SKU_PRODUTO"].astype(str).str.strip()

    if "CENTRO_CUSTO" in fato_vendas.columns:
        fato_vendas["CENTRO_CUSTO"] = fato_vendas["CENTRO_CUSTO"].astype(str).str.strip()

    # Merge com produto
    if "SKU" in dim_produto.columns:
        dim_produto["SKU"] = dim_produto["SKU"].astype(str).str.strip()

        fato_vendas = fato_vendas.merge(
            dim_produto[["SKU", "GRUPO", "SUBGRUPO"]],
            left_on="SKU_PRODUTO",
            right_on="SKU",
            how="left"
        )
        fato_vendas = fato_vendas.drop(columns=["SKU"], errors='ignore')


    # Merge com centro de custo e empresa via NOME_CENTRO_CUSTO
    if "CENTRO_CUSTO" in fato_vendas.columns and "NOME_CENTRO_CUSTO" in dim_empresa.columns:
        dim_empresa["NOME_CENTRO_CUSTO"] = dim_empresa["NOME_CENTRO_CUSTO"].astype(str).str.strip()
        fato_vendas["CENTRO_CUSTO"] = fato_vendas["CENTRO_CUSTO"].astype(str).str.strip()

        colunas_para_trazer = ["NOME_CENTRO_CUSTO", "COD_CC", "NOME_FILIAL", "NOME_EMPRESA", "COD_FILIAL", "COD_EMPRESA"]
        colunas_existentes = [col for col in colunas_para_trazer if col in dim_empresa.columns]

        fato_vendas = fato_vendas.merge(
            dim_empresa[colunas_existentes].drop_duplicates(subset=["NOME_CENTRO_CUSTO"]),
            left_on="CENTRO_CUSTO",
            right_on="NOME_CENTRO_CUSTO",
            how="left"
        )

    # Converter valores financeiros
    colunas_financeiras = [
        "PRECO_CUSTO_UNITARIO",
        "PRECO_VENDA_UNITARIO",
        "TOTAL_CUSTO",
        "TOTAL_VENDA",
        "QUANTIDADE"
    ]

    for coluna in colunas_financeiras:
        if coluna in fato_vendas.columns:
            fato_vendas[coluna] = fato_vendas[coluna].apply(converter_para_float_seguro)

    # Converter data
    if "DATA_VENDA" in fato_vendas.columns:
        fato_vendas["DATA_VENDA"] = normalizar_coluna_data(fato_vendas["DATA_VENDA"])

    # Preencher valores ausentes
    colunas_padrao = {
        "COD_CC": "CC-000",
        "NOME_CENTRO_CUSTO": "Sem Centro Custo",
        "NOME_FILIAL": "Sem Filial",
        "NOME_EMPRESA": "Sem Empresa"
    }

    for col, valor_padrao in colunas_padrao.items():
        if col not in fato_vendas.columns:
            fato_vendas[col] = valor_padrao
        else:
            fato_vendas[col] = fato_vendas[col].fillna(valor_padrao)

    # Garantir que NOME_CENTRO_CUSTO existe
    if "NOME_CENTRO_CUSTO" not in fato_vendas.columns:
        if "CENTRO_CUSTO" in fato_vendas.columns:
            fato_vendas["NOME_CENTRO_CUSTO"] = fato_vendas["CENTRO_CUSTO"]
        else:
            fato_vendas["NOME_CENTRO_CUSTO"] = "Sem Centro Custo"

    return fato_vendas

@st.cache_data
def carregar_dados_completos():
    """Carrega todos os dados com cache"""
    with st.spinner("🔄 Carregando dados..."):
        dim_produto = build_dim_produto()
        dim_empresa = build_dim_Empresa()
        fato_vendas = build_fato_vendas(dim_produto, dim_empresa)

    return fato_vendas


# ==========================================
# FUNÇÕES AUXILIARES PARA FILTROS
# ==========================================

def get_coluna_segura(df: pd.DataFrame, coluna: str, valor_padrao="Todos"):
    """Retorna lista única de valores de uma coluna, tratando erros"""
    if coluna in df.columns and not df[coluna].empty:
        valores = df[coluna].dropna().unique().tolist()
        # Filtrar valores vazios
        valores = [v for v in valores if str(v).strip() and str(v) not in ['nan', 'None', '']]
        if valores:
            return [valor_padrao] + sorted(valores)
    return [valor_padrao]


def aplicar_filtro_seguro(df: pd.DataFrame, coluna: str, valor: str, valor_padrao="Todos"):
    """Aplica filtro de forma segura"""
    if valor != valor_padrao and coluna in df.columns:
        return df[df[coluna] == valor]
    return df


# ==========================================
# FUNÇÕES DE MÉTRICAS
# ==========================================

def calcular_margem_lucro(df: pd.DataFrame) -> float:
    if df.empty or "TOTAL_VENDA" not in df.columns or "TOTAL_CUSTO" not in df.columns:
        return 0.0

    total_vendas = df["TOTAL_VENDA"].sum()
    total_custo = df["TOTAL_CUSTO"].sum()

    if total_vendas == 0:
        return 0.0

    return ((total_vendas - total_custo) / total_vendas) * 100


def calcular_ticket_medio(df: pd.DataFrame) -> float:
    if df.empty or "TOTAL_VENDA" not in df.columns:
        return 0.0

    total_vendas = df["TOTAL_VENDA"].sum()
    num_vendas = len(df)

    return total_vendas / num_vendas if num_vendas > 0 else 0.0


def get_top_produtos(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if df.empty or "NOME_PRODUTO" not in df.columns or "TOTAL_VENDA" not in df.columns:
        return pd.DataFrame()

    top = df.groupby("NOME_PRODUTO")["TOTAL_VENDA"].sum().reset_index()
    top = top.sort_values("TOTAL_VENDA", ascending=False).head(top_n)
    return top


def get_vendas_por_periodo(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "DATA_VENDA" not in df.columns or "TOTAL_VENDA" not in df.columns:
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy["MES_ANO"] = df_copy["DATA_VENDA"].dt.strftime("%Y-%m")
    vendas_periodo = df_copy.groupby("MES_ANO")["TOTAL_VENDA"].sum().reset_index()
    return vendas_periodo.sort_values("MES_ANO")


def formatar_reais(valor, com_simbolo=True, casas_decimais=2):
    if casas_decimais == 2:
        return reais(valor, simbolo=com_simbolo)

    try:
        if isinstance(valor, str):
            valor = re.sub(r'[^\d,.-]', '', valor)
            valor = valor.replace(',', '.')

        num = float(valor)

        formatado = f"{num:,.{casas_decimais}f}"
        formatado = formatado.replace(",", "X").replace(".", ",").replace("X", ".")

        if com_simbolo:
            return f"R$ {formatado}"
        return formatado

    except (ValueError, TypeError):
        return "R$ 0,00" if com_simbolo else "0,00"

def get_vendas_comparativo_periodo(
    df_filtrado: pd.DataFrame,
    df_completo: pd.DataFrame,
    data_inicio: pd.Timestamp,
    data_fim: pd.Timestamp
) -> pd.DataFrame:
    if df_filtrado.empty or "DATA_VENDA" not in df_filtrado.columns:
        return pd.DataFrame()

    data_inicio_anterior = data_inicio - pd.DateOffset(years=1)
    data_fim_anterior = data_fim - pd.DateOffset(years=1)

    df_anterior = df_completo[
        (df_completo["DATA_VENDA"] >= data_inicio_anterior) &
        (df_completo["DATA_VENDA"] <= data_fim_anterior)
    ].copy()

    df_atual = df_filtrado.copy()
    df_atual["MES"] = df_atual["DATA_VENDA"].dt.strftime("%m")
    df_atual["MES_LABEL"] = df_atual["DATA_VENDA"].dt.strftime("%b")
    df_atual["ANO"] = df_atual["DATA_VENDA"].dt.strftime("%Y")

    df_anterior["MES"] = df_anterior["DATA_VENDA"].dt.strftime("%m")
    df_anterior["MES_LABEL"] = df_anterior["DATA_VENDA"].dt.strftime("%b")
    df_anterior["ANO"] = df_anterior["DATA_VENDA"].dt.strftime("%Y")

    df_union = pd.concat([df_atual, df_anterior], ignore_index=True)
    vendas = df_union.groupby(["ANO", "MES", "MES_LABEL"])["TOTAL_VENDA"].sum().reset_index()
    vendas = vendas.sort_values(["ANO", "MES"])

    # Calcular variação % entre anos por mês
    anos = sorted(vendas["ANO"].unique())
    if len(anos) >= 2:
        ano_atual = anos[-1]
        ano_anterior = anos[-2]

        pivot = vendas.pivot(index="MES", columns="ANO", values="TOTAL_VENDA").reset_index()
        pivot["VARIACAO_PCT"] = ((pivot[ano_atual] - pivot[ano_anterior]) / pivot[ano_anterior] * 100).round(1)
        vendas = vendas.merge(pivot[["MES", "VARIACAO_PCT"]], on="MES", how="left")
    else:
        vendas["VARIACAO_PCT"] = None

    # Formatar variação como string para o hover
    def formatar_variacao(v):
        if pd.isna(v):
            return ""
        sinal = "+" if v > 0 else ""
        return f"Variação vs ano ant.: {sinal}{v:.1f}%"

    vendas["VARIACAO_PCT"] = vendas["VARIACAO_PCT"].apply(formatar_variacao)

    return vendas
def get_top_produtos_quantidade(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if df.empty or "NOME_PRODUTO" not in df.columns or "QUANTIDADE" not in df.columns:
        return pd.DataFrame()

    top = df.groupby("NOME_PRODUTO")["QUANTIDADE"].sum().reset_index()
    top = top[top["QUANTIDADE"] > 0]
    top = top.sort_values("QUANTIDADE", ascending=True).tail(top_n)
    return top


def get_top_produtos_lucro(df: pd.DataFrame, top_n: int = 10) -> pd.DataFrame:
    if df.empty or "NOME_PRODUTO" not in df.columns or "TOTAL_VENDA" not in df.columns or "TOTAL_CUSTO" not in df.columns:
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy["LUCRO"] = df_copy["TOTAL_VENDA"] - df_copy["TOTAL_CUSTO"]

    top = df_copy.groupby("NOME_PRODUTO").agg(
        LUCRO=("LUCRO", "sum"),
        TOTAL_VENDA=("TOTAL_VENDA", "sum"),
        TOTAL_CUSTO=("TOTAL_CUSTO", "sum")
    ).reset_index()

    top["MARGEM_PCT"] = (top["LUCRO"] / top["TOTAL_VENDA"] * 100).round(1)
    top = top[top["LUCRO"] > 0]
    top = top.sort_values("LUCRO", ascending=True).tail(top_n)
    return top
# ==========================================
# INTERFACE PRINCIPAL
# ==========================================
cor_verde = '#10b981'
cor_vermelho = '#ef4444'
st.set_page_config(page_title="Dashboard de Vendas", layout="wide")

st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        .stDataFrame { font-size: 12px; }
    </style>
""", unsafe_allow_html=True)

cores = render_page()
st.title("📊 Painel Executivo de Vendas & Faturamento")

# Carregar dados
fato_vendas = carregar_dados_completos()

if fato_vendas.empty:
    st.error("❌ Nenhum dado de vendas foi carregado. Verifique o arquivo Excel.")
    st.stop()

# ==========================================
# FILTROS INTERATIVOS
# ==========================================

st.markdown("### 🔎 Parâmetros de Busca")


# Primeira linha de filtros
col1, col2, col3 = st.columns(3)

with col1:
    opcoes_empresa = get_coluna_segura(fato_vendas, "NOME_EMPRESA")
    empresa_sel = st.selectbox("🏢 Empresa", opcoes_empresa)

with col2:
    opcoes_filial = get_coluna_segura(fato_vendas, "NOME_FILIAL")
    filial_sel = st.selectbox("🏪 Filial", opcoes_filial)

with col3:
    opcoes_cc = get_coluna_segura(fato_vendas, "NOME_CENTRO_CUSTO")
    cc_sel = st.selectbox("📌 Centro de Custo", opcoes_cc)

# Segunda linha de filtros
col4, col5, col6 = st.columns(3)

with col4:
    opcoes_grupo = get_coluna_segura(fato_vendas, "GRUPO")
    grupo_sel = st.selectbox("📦 Grupo de Produto", opcoes_grupo)

with col5:
    opcoes_subgrupo = get_coluna_segura(fato_vendas, "SUBGRUPO")
    subgrupo_sel = st.selectbox("🔖 Subgrupo", opcoes_subgrupo)

with col6:
    if "DATA_VENDA" in fato_vendas.columns:
        data_min = fato_vendas["DATA_VENDA"].min()
        data_max = fato_vendas["DATA_VENDA"].max()

        periodo_sel = st.date_input(
            "📅 Período de Vendas",
            value=[data_min, data_max],
            min_value=data_min,
            max_value=data_max
        )
    else:
        periodo_sel = []
        st.warning("⚠️ Coluna 'DATA_VENDA' não encontrada")

# Terceira linha - Pesquisa avançada
st.markdown("---")
# Usando alinhamento vertical 'bottom' para o botão não ficar desalinhado com o topo do select
col7, col8 = st.columns([3, 1], vertical_alignment="bottom")

with col7:
    if "NOME_PRODUTO" in fato_vendas.columns and "SKU_PRODUTO" in fato_vendas.columns:
        # Criando a string combinada garantindo que nulos virem texto vazio antes da concatenação
        fato_vendas["PRODUTO_DISPLAY"] = (
                fato_vendas["NOME_PRODUTO"].fillna("").astype(str) +
                " (" +
                fato_vendas["SKU_PRODUTO"].fillna("").astype(str) + ")"
        )
        # Filtra strings vazias residuais de registros corrompidos antes de listar
        lista_produtos = sorted([p for p in fato_vendas["PRODUTO_DISPLAY"].unique() if p and p != " ()"])

        produtos_selecionados = st.multiselect(
            "🔍 Pesquisa Avançada por Produto",
            options=lista_produtos,
            placeholder="Digite ou selecione os produtos..."
        )
    else:
        produtos_selecionados = []
        st.info("ℹ️ Dados de produto não disponíveis para busca avançada")

with col8:
    # Cria um espaçador visual sutil caso o layout precise de um ajuste extra de respiro
    st.markdown('<div style="margin-top: 1px;"></div>', unsafe_allow_html=True)
    if st.button("🧹 Limpar Filtros", use_container_width=True, type="secondary"):
        st.cache_data.clear()
        st.columns  # Apenas garante contexto limpo se necessário
        st.rerun()
# ==========================================
# APLICAÇÃO DOS FILTROS
# ==========================================

vendas_filtradas = fato_vendas.copy()

# Aplicar filtros
vendas_filtradas = aplicar_filtro_seguro(vendas_filtradas, "NOME_EMPRESA", empresa_sel)
vendas_filtradas = aplicar_filtro_seguro(vendas_filtradas, "NOME_FILIAL", filial_sel)
vendas_filtradas = aplicar_filtro_seguro(vendas_filtradas, "NOME_CENTRO_CUSTO", cc_sel)
vendas_filtradas = aplicar_filtro_seguro(vendas_filtradas, "GRUPO", grupo_sel)
vendas_filtradas = aplicar_filtro_seguro(vendas_filtradas, "SUBGRUPO", subgrupo_sel)

# Aplicar filtro de período
if "DATA_VENDA" in vendas_filtradas.columns and len(periodo_sel) == 2:
    data_inicio = pd.to_datetime(periodo_sel[0])
    data_fim = pd.to_datetime(periodo_sel[1])
    vendas_filtradas = vendas_filtradas[
        (vendas_filtradas["DATA_VENDA"] >= data_inicio) &
        (vendas_filtradas["DATA_VENDA"] <= data_fim)
        ]

# Aplicar filtro de produtos
if produtos_selecionados and "PRODUTO_DISPLAY" in vendas_filtradas.columns:
    vendas_filtradas = vendas_filtradas[vendas_filtradas["PRODUTO_DISPLAY"].isin(produtos_selecionados)]

# ==========================================
# CARDS DE MÉTRICAS
# ==========================================

# Calcular métricas
total_vendas = vendas_filtradas[
    "TOTAL_VENDA"].sum() if "TOTAL_VENDA" in vendas_filtradas.columns and not vendas_filtradas.empty else 0
total_custo = vendas_filtradas[
    "TOTAL_CUSTO"].sum() if "TOTAL_CUSTO" in vendas_filtradas.columns and not vendas_filtradas.empty else 0
margem_lucro = calcular_margem_lucro(vendas_filtradas)
ticket_medio = calcular_ticket_medio(vendas_filtradas)
num_vendas = len(vendas_filtradas) if not vendas_filtradas.empty else 0
num_produtos = vendas_filtradas[
    "SKU_PRODUTO"].nunique() if "SKU_PRODUTO" in vendas_filtradas.columns and not vendas_filtradas.empty else 0

st.markdown("---")

# Layout dos cards
card_col1, card_col2, card_col3, card_col4 = st.columns(4)

html_card_template = """
<div class="card-style"style=" border-top: 4px solid {color}; color: white; min-height: 135px; box-shadow: 0 4px 15px rgba(0,0,0,0.25);">
    <div style="font-size: 13px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 8px;">{title}</div>
    <div style="font-size: 32px; font-weight: 700; color: #f8fafc; line-height: 1.1; margin-bottom: 6px;">{value}</div>
    <div style="font-size: 12px; color: {subcolor};">{subtext}</div>
</div>
"""

with card_col1:
    st.markdown(html_card_template.format(
        title="Faturamento Total",
        value=formatar_reais(total_vendas),
        subtext=f"💰 {num_vendas:,} vendas realizadas".replace(",", "."),
        color="#3b82f6",
        subcolor="#60a5fa"
    ), unsafe_allow_html=True)

with card_col2:
    st.markdown(html_card_template.format(
        title="Margem de Lucro",
        value=f"{margem_lucro:.1f}%",
        subtext=f"📊 Custo total: {formatar_reais(total_custo)}",
        color="#10b981",
        subcolor="#34d399"
    ), unsafe_allow_html=True)

with card_col3:
    st.markdown(html_card_template.format(
        title="Ticket Médio",
        value=formatar_reais(ticket_medio),
        subtext=f"🎫 Média por venda",
        color="#f59e0b",
        subcolor="#fbbf24"
    ), unsafe_allow_html=True)

with card_col4:
    st.markdown(html_card_template.format(
        title="Portfólio Ativo",
        value=f"{num_produtos:,}".replace(",", "."),
        subtext=f"📦 Produtos comercializados",
        color="#8b5cf6",
        subcolor="#a78bfa"
    ), unsafe_allow_html=True)

# ==========================================
# GRÁFICOS
# ==========================================

st.markdown("---")
st.header("📈 Análise de Vendas")

g_col1, g_col2,g_col3 = st.columns(3)
with g_col1:
    with st.container(border=True, gap="xsmall"):
        vendas_sem_data = fato_vendas.copy()
        vendas_sem_data = aplicar_filtro_seguro(vendas_sem_data, "NOME_EMPRESA", empresa_sel)
        vendas_sem_data = aplicar_filtro_seguro(vendas_sem_data, "NOME_FILIAL", filial_sel)
        vendas_sem_data = aplicar_filtro_seguro(vendas_sem_data, "NOME_CENTRO_CUSTO", cc_sel)
        vendas_sem_data = aplicar_filtro_seguro(vendas_sem_data, "GRUPO", grupo_sel)
        vendas_sem_data = aplicar_filtro_seguro(vendas_sem_data, "SUBGRUPO", subgrupo_sel)

        if len(periodo_sel) == 2:
            data_inicio = pd.to_datetime(periodo_sel[0])
            data_fim = pd.to_datetime(periodo_sel[1])
        else:
            data_inicio = fato_vendas["DATA_VENDA"].min()
            data_fim = fato_vendas["DATA_VENDA"].max()

        vendas_comp = get_vendas_comparativo_periodo(
            vendas_filtradas, vendas_sem_data, data_inicio, data_fim
        )

        if not vendas_comp.empty:
            # 🔥 CORREÇÃO: Garante que o DataFrame esteja estritamente ordenado pelo número do mês
            vendas_comp = vendas_comp.sort_values("MES")

            fig_vendas = px.line(
                vendas_comp,
                x="MES_LABEL",
                y="TOTAL_VENDA",
                color="ANO",
                markers=True,
                title="Faturamento Mensal Comparativo com Ano Anterior",
                color_discrete_sequence=["#3b82f6", "#f59e0b"],
                custom_data=["VARIACAO_PCT", "ANO"]
            )

            fig_vendas.update_traces(
                hovertemplate=(
                    "<b>%{x} — %{customdata[1]}</b><br>"
                    "Faturamento: R$ %{y:,.2f}<br>"
                    "%{customdata[0]}"
                    "<extra></extra>"
                )
            )

            fig_vendas.update_layout(
                template="plotly_dark",
                height=400,
                # 🔥 CORREÇÃO: 'categoryarray' força o eixo X a seguir a ordem exata das linhas do DataFrame
                xaxis=dict(
                    title=None,
                    showgrid=False,
                    tickfont=dict(color=cores["sidebar_texto"]),
                    type='category',
                    categoryorder='array',
                    categoryarray=vendas_comp["MES_LABEL"].unique()
                ),
                yaxis=dict(title=None, showgrid=True, gridcolor="#94a3b8", tickfont=dict(color=cores["sidebar_texto"])),
                legend_title="Ano"
            )

            st.plotly_chart(fig_vendas, use_container_width=True)
        else:
            st.info("Sem dados para exibir o gráfico de evolução")
with g_col2:
    with st.container(border=True, gap="xsmall"):
      #  st.subheader("💳 Vendas por Forma de Pagamento")

        if not vendas_filtradas.empty and "FORMA_PAGAMENTO" in vendas_filtradas.columns:
            vendas_pgto = (
                vendas_filtradas
                .dropna(subset=["FORMA_PAGAMENTO"])
                .groupby("FORMA_PAGAMENTO")["TOTAL_VENDA"]
                .sum()
                .reset_index()
            )
            vendas_pgto = vendas_pgto[vendas_pgto["TOTAL_VENDA"] > 0]

            if not vendas_pgto.empty:
                total_geral = vendas_pgto["TOTAL_VENDA"].sum()
                vendas_pgto["PCT"] = (vendas_pgto["TOTAL_VENDA"] / total_geral * 100).round(1)
                vendas_pgto["LABEL"] = vendas_pgto.apply(
                    lambda r: f"{r['PCT']}% — R$ {r['TOTAL_VENDA']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
                    axis=1
                )

                fig_pgto = px.pie(
                    vendas_pgto,
                    values="TOTAL_VENDA",
                    names="FORMA_PAGAMENTO",
                    title="Participação por Forma de Pagamento",
                    hole=0.4,
                    custom_data=["PCT", "LABEL"],
                    color_discrete_sequence=px.colors.qualitative.Pastel
                )
                fig_pgto.update_traces(
                    textinfo="percent+label",
                    hovertemplate=(
                        "<b>%{label}</b><br>"
                        "Valor: R$ %{value:,.2f}<br>"
                        "Participação: %{percent}<br>"
                        "<extra></extra>"
                    )
                )
                fig_pgto.update_layout(
                    template="plotly_dark",
                    height=400
                )
                st.plotly_chart(fig_pgto, use_container_width=True)
            else:
                st.info("Sem dados para exibir formas de pagamento")
        else:
            st.info("Sem dados para exibir formas de pagamento")
with g_col3:
    with st.container(border=True, gap="xsmall"):
        # st.subheader("🏆 Top 10 Produtos Mais Vendidos")
        top_produtos = get_top_produtos(vendas_filtradas, 10)

        if not top_produtos.empty:
            # Ordena para que o maior produto fique no topo
            top_produtos = top_produtos.sort_values("TOTAL_VENDA", ascending=True)

            # 🔥 Criamos uma coluna temporária com o valor formatado para usar de rótulo
            top_produtos["ROTULO"] = top_produtos["TOTAL_VENDA"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

            fig_top = px.bar(
                top_produtos,
                x="TOTAL_VENDA",
                y="NOME_PRODUTO",
                orientation="h",
                title="Ranking por Faturamento",
                color="TOTAL_VENDA",
                text="ROTULO",  # 🔥 Define a coluna que será o rótulo de texto
                color_continuous_scale=["#f59e0b", "#ef4444"]
            )

            fig_top.update_traces(
                textfont=dict(family="sans-serif", size=11,                         color=cores["sidebar_texto"], weight="bold"),
                    textposition="auto",
                hovertemplate=(
                    "<b>Produto:</b> %{y}<br>"
                    "<b>Faturamento:</b> R$ %{x:,.2f}<br>"
                    "<extra></extra>"
                )
            )

            fig_top.update_layout(
                template="plotly_dark",
                height=400,
                legend_title_text="",
                xaxis=dict(title=None, visible=False,showgrid=False, tickfont=dict(color=cores["sidebar_texto"])),
                yaxis=dict(title=None,automargin=True, showgrid=False, tickfont=dict(color=cores["sidebar_texto"])),
                coloraxis_showscale=False,
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.05,
                    xanchor="center",
                    x=0.5,
                )
            )
            st.plotly_chart(fig_top, use_container_width=True)
        else:
            st.info("Sem dados para exibir o ranking de produtos")
# Segunda linha de gráficos
g_col4, g_col5,g_col6 = st.columns(3)

with g_col4:
    with st.container(border=True, gap="xsmall"):
        # st.subheader("🏢 Vendas por Filial")

        if not vendas_filtradas.empty and "NOME_FILIAL" in vendas_filtradas.columns:
            vendas_filial = vendas_filtradas.groupby("NOME_FILIAL")["TOTAL_VENDA"].sum().reset_index()
            vendas_filial = vendas_filial.sort_values("TOTAL_VENDA", ascending=True)

            # 🔥 1. CRIAR O RÓTULO (Faltava isso aqui!)
            vendas_filial["ROTULO"] = vendas_filial["TOTAL_VENDA"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

            fig_filial = px.bar(
                vendas_filial,
                x="TOTAL_VENDA",
                y="NOME_FILIAL",
                orientation="h",
                title="Faturamento por Filial",
                # 🔥 2. PASSAR O TEXTO PRO GRÁFICO (E faltava isso aqui também!)
                text="ROTULO",
                color_discrete_sequence=["#10b981"]
            )

            fig_filial.update_traces(
                textfont=dict(family="sans-serif", size=11, color=cores["sidebar_texto"], weight="bold"),
                textposition="auto",
                texttemplate="%{text}",
                hovertemplate=(
                    "<b>Filial:</b> %{y}<br>"
                    "<b>Faturamento:</b> R$ %{x:,.2f}<br>"
                    "<extra></extra>"
                )
            )

            fig_filial.update_layout(
                template="plotly_dark",
                legend_title_text="",
                height=400,
                xaxis=dict(title=None, visible=False, showgrid=False, zeroline=False,
                           tickfont=dict(color=cores["sidebar_texto"])),
                yaxis=dict(
                    title=None,
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color=cores["sidebar_texto"]),
                    automargin=True
                ),
            )
            st.plotly_chart(fig_filial, use_container_width=True)
        else:
            st.info("Sem dados para exibir vendas por filial")
with g_col5:
    with st.container(border=True, gap="xsmall"):
        #  st.subheader("📦 Distribuição por Grupo de Produto")

        if not vendas_filtradas.empty and "GRUPO" in vendas_filtradas.columns:
            vendas_grupo = vendas_filtradas.groupby("GRUPO")["TOTAL_VENDA"].sum().reset_index()
            vendas_grupo = vendas_grupo[vendas_grupo["TOTAL_VENDA"] > 0]
            vendas_grupo = vendas_grupo.sort_values("TOTAL_VENDA", ascending=True)

            if not vendas_grupo.empty:
                # 1. Cria o rótulo formatado em R$ para ficar fixo nas barras
                vendas_grupo["ROTULO"] = vendas_grupo["TOTAL_VENDA"].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )

                # 2. Passa a coluna 'ROTULO' para o parâmetro text
                fig_grupo = px.bar(
                    vendas_grupo,
                    x="TOTAL_VENDA",
                    y="GRUPO",
                    orientation="h",
                    title="Participação por Grupo",
                    color="TOTAL_VENDA",
                    text="ROTULO",
                    color_continuous_scale=["#10b981", "#059669"]
                )

                # 3. Configura o visual do texto interno e do balão do mouse
                fig_grupo.update_traces(
                    textfont=dict(family="sans-serif", size=11, color=cores["sidebar_texto"], weight="bold"),
                    textposition="auto",
                    texttemplate="%{text}",
                    hovertemplate=(
                        "<b>Grupo:</b> %{y}<br>"
                        "<b>Faturamento:</b> R$ %{x:,.2f}<br>"
                        "<extra></extra>"
                    )
                )

                # 4. Remove o eixo de baixo e a barra lateral em pé
                fig_grupo.update_layout(
                    template="plotly_dark",
                    height=400,
                    xaxis=dict(title=None, visible=False, showgrid=False, zeroline=False),
                    yaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(color=cores["sidebar_texto"]),
                        automargin=True
                    ),
                    coloraxis_showscale=False  # Remove a barra colorida em pé
                )
                st.plotly_chart(fig_grupo, use_container_width=True)
            else:
                st.info("Sem dados para exibir distribuição por grupo")
        else:
            st.info("Sem dados para exibir distribuição por grupo")

with g_col6:
    with st.container(border=True, gap="xsmall"):
       # st.subheader("📦 Distribuição por Subgrupo")

        if not vendas_filtradas.empty and "SUBGRUPO" in vendas_filtradas.columns:
            vendas_subgrupo = (
                vendas_filtradas
                .dropna(subset=["SUBGRUPO"])
                .groupby("SUBGRUPO")["TOTAL_VENDA"]
                .sum()
                .reset_index()
            )
            vendas_subgrupo = vendas_subgrupo[vendas_subgrupo["TOTAL_VENDA"] > 0]
            vendas_subgrupo = vendas_subgrupo.sort_values("TOTAL_VENDA", ascending=True)

            if not vendas_subgrupo.empty:
                # 1. Cria o rótulo formatado em R$ para fixar nas barras
                vendas_subgrupo["ROTULO"] = vendas_subgrupo["TOTAL_VENDA"].apply(
                    lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
                )

                # 2. Passa a coluna 'ROTULO' para o parâmetro text
                fig_subgrupo = px.bar(
                    vendas_subgrupo,
                    x="TOTAL_VENDA",
                    y="SUBGRUPO",
                    orientation="h",
                    title="Participação por Subgrupo",
                    color="TOTAL_VENDA",
                    text="ROTULO",
                    color_continuous_scale=["#8b5cf6", "#6d28d9"]
                )

                # 3. Configura o visual do texto na barra e do balão do mouse (hover)
                fig_subgrupo.update_traces(
                    textfont=dict(family="sans-serif", size=11, color=cores["sidebar_texto"], weight="bold"),
                    textposition="auto",
                    texttemplate="%{text}",
                    hovertemplate=(
                        "<b>Subgrupo:</b> %{y}<br>"
                        "<b>Faturamento:</b> R$ %{x:,.2f}<br>"
                        "<extra></extra>"
                    )
                )

                # 4. Remove o eixo redundante de baixo e a barra lateral de cores
                fig_subgrupo.update_layout(
                    template="plotly_dark",
                    height=400,
                    xaxis=dict(title=None, visible=False, showgrid=False, zeroline=False),
                    yaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(color=cores["sidebar_texto"]),
                        automargin=True
                    ),
                    coloraxis_showscale=False  # Some com a barra de cores vertical
                )
                st.plotly_chart(fig_subgrupo, use_container_width=True)
            else:
                st.info("Sem dados para exibir distribuição por subgrupo")
        else:
            st.info("Sem dados para exibir distribuição por subgrupo")
st.markdown("---")
st.header("🔬 Análise de Produtos")

p_col1, p_col2 = st.columns(2)

with p_col1:
    with st.container(border=True, gap="xsmall"):
      #  st.subheader("📦 Top 10 Produtos por Quantidade Vendida")
        top_qtd = get_top_produtos_quantidade(vendas_filtradas, 10)

        if not top_qtd.empty:
            # Garante a ordenação correta para o maior ficar no topo
            top_qtd = top_qtd.sort_values("QUANTIDADE", ascending=True)

            # 🔥 Cria o rótulo formatado como número inteiro (ex: 1.250)
            top_qtd["ROTULO"] = top_qtd["QUANTIDADE"].apply(lambda x: f"{int(x):,}".replace(",", "."))

            fig_qtd = px.bar(
                top_qtd,
                x="QUANTIDADE",
                y="NOME_PRODUTO",
                orientation="h",
                title="Ranking por Quantidade",
                color="QUANTIDADE",
                text="ROTULO",  # 🔥 Vincula o texto do rótulo
                color_continuous_scale=["#3b82f6", "#1d4ed8"]
            )

            fig_qtd.update_traces(
                textfont=dict(family="sans-serif", size=11, color=cores["sidebar_texto"], weight="bold"),
                textposition="auto",
                texttemplate="%{text}",
                hovertemplate=(
                    "<b>Produto:</b> %{y}<br>"
                    "<b>Quantidade:</b> %{text}<br>"
                    "<extra></extra>"
                )
            )

            fig_qtd.update_layout(
                template="plotly_dark",
                height=400,
                xaxis=dict(title=None, visible=False, showgrid=False, zeroline=False),
                yaxis=dict(
                    title=None,
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color=cores["sidebar_texto"]),
                    automargin=True
                ),
                coloraxis_showscale=False  # Remove a barra lateral em pé
            )
            st.plotly_chart(fig_qtd, use_container_width=True)
        else:
            st.info("Sem dados para exibir ranking por quantidade")

with p_col2:
    with st.container(border=True, gap="xsmall"):
       # st.subheader("💰 Top 10 Produtos por Lucro")
        top_lucro = get_top_produtos_lucro(vendas_filtradas, 10)

        if not top_lucro.empty:
            # Garante a ordenação correta para o maior ficar no topo
            top_lucro = top_lucro.sort_values("LUCRO", ascending=True)

            # 🔥 Cria o rótulo formatado em R$ para a barra
            top_lucro["ROTULO"] = top_lucro["LUCRO"].apply(
                lambda x: f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            )

            fig_lucro = px.bar(
                top_lucro,
                x="LUCRO",
                y="NOME_PRODUTO",
                orientation="h",
                title="Ranking por Lucro",
                color="MARGEM_PCT",
                text="ROTULO",  # 🔥 Vincula o texto do faturamento/lucro
                color_continuous_scale=["#f59e0b", "#10b981"],
                custom_data=["MARGEM_PCT", "TOTAL_VENDA", "TOTAL_CUSTO"]
            )

            fig_lucro.update_traces(
                textfont=dict(family="sans-serif", size=11, color=cores["sidebar_texto"], weight="bold"),
                textposition="auto",
                texttemplate="%{text}",
                hovertemplate=(
                    "<b>Produto:</b> %{y}<br>"
                    "<b>Lucro:</b> R$ %{x:,.2f}<br>"
                    "<b>Margem:</b> %{customdata[0]:.1f}%<br>"
                    "<b>Faturamento:</b> R$ %{customdata[1]:,.2f}<br>"
                    "<b>Custo:</b> R$ %{customdata[2]:,.2f}<br>"
                    "<extra></extra>"
                )
            )

            fig_lucro.update_layout(
                template="plotly_dark",
                height=400,
                xaxis=dict(title=None, visible=False, showgrid=False, zeroline=False),
                yaxis=dict(
                    title=None,
                    showgrid=False,
                    zeroline=False,
                    tickfont=dict(color=cores["sidebar_texto"]),
                    automargin=True
                ),
                coloraxis_showscale=False  # Remove a barra lateral em pé
            )
            st.plotly_chart(fig_lucro, use_container_width=True)
        else:
            st.info("Sem dados para exibir ranking por lucro")
# ==========================================
# TABELA DETALHADA
# ==========================================

st.markdown("---")
st.header("📋 Detalhamento das Vendas")

if not vendas_filtradas.empty:
    # Selecionar colunas para exibir
    colunas_tabela = [
        "DATA_VENDA", "SKU_PRODUTO", "NOME_PRODUTO", "GRUPO", "SUBGRUPO",
        "QUANTIDADE", "PRECO_VENDA_UNITARIO", "TOTAL_VENDA",
        "NOME_FILIAL", "NOME_EMPRESA", "NOME_CENTRO_CUSTO"
    ]

    # Filtrar colunas que existem
    colunas_existentes = [col for col in colunas_tabela if col in vendas_filtradas.columns]

    # Criar cópia para exibição
    df_tabela = vendas_filtradas[colunas_existentes].copy()

    # Formatar valores
    if "DATA_VENDA" in df_tabela.columns:
        df_tabela["DATA_VENDA"] = pd.to_datetime(df_tabela["DATA_VENDA"]).dt.strftime("%d/%m/%Y")

    if "PRECO_VENDA_UNITARIO" in df_tabela.columns:
        df_tabela["PRECO_VENDA_UNITARIO"] = df_tabela["PRECO_VENDA_UNITARIO"].apply(
            lambda x: formatar_reais(x, com_simbolo=False)
        )

    if "TOTAL_VENDA" in df_tabela.columns:
        df_tabela["TOTAL_VENDA"] = df_tabela["TOTAL_VENDA"].apply(formatar_reais)

    if "QUANTIDADE" in df_tabela.columns:
        df_tabela["QUANTIDADE"] = df_tabela["QUANTIDADE"].apply(
            lambda x: f"{int(x):,}".replace(",", ".") if pd.notna(x) and x > 0 else "0"
        )

    # Renomear colunas
    mapeamento_colunas = {
        "DATA_VENDA": "Data",
        "SKU_PRODUTO": "SKU",
        "NOME_PRODUTO": "Produto",
        "GRUPO": "Grupo",
        "SUBGRUPO": "Subgrupo",
        "QUANTIDADE": "Qtd",
        "PRECO_VENDA_UNITARIO": "Preço Unitário",
        "TOTAL_VENDA": "Total Venda",
        "NOME_FILIAL": "Filial",
        "NOME_EMPRESA": "Empresa",
        "NOME_CENTRO_CUSTO": "Centro Custo"
    }

    df_tabela = df_tabela.rename(columns=mapeamento_colunas)

    # Exibir tabela
    st.dataframe(
        df_tabela,
        use_container_width=True,
        height=400,
        hide_index=True
    )
else:
    st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")

# ==========================================
# RODAPÉ
# ==========================================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 12px;'>"
    "📊 Dashboard desenvolvido com Streamlit | Dados atualizados em tempo real"
    "</div>",
    unsafe_allow_html=True
)