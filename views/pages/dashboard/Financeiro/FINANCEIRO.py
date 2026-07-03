import os
import re
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from controller.empresaController import EmpresaController
from controller.loginController import LoginController
from controller.token_controller import TokenController
from helpers.formata import converter_para_float_seguro, reais
from helpers.tema import obter_cor_alerta, obter_tema_empresa

warnings.filterwarnings('ignore')

load_dotenv()

hoje = pd.Timestamp(datetime.now().date())
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
        st.stop
    return {
        "primaria": tema_completo['tema_primario'],
        "secundaria": tema_completo['tema_secundario'],
        "sidebar_fundo": tema_completo['sidebar_fundo'],
        "sidebar_texto": tema_completo['sidebar_texto'],
        "cor_alerta_alerta_vermelho": obter_cor_alerta("vermelho"),
        "cor_alerta_alerta_amarelo": obter_cor_alerta("amarelo"),
        "cor_alerta_alerta_verde": obter_cor_alerta("verde")
    }


# ==========================================
# FUNÇÕES DE LEITURA
# ==========================================

def listar_abas() -> list[str]:
    xl = pd.ExcelFile(arquivo_origem)
    return xl.sheet_names


def ler_aba(indice: int) -> pd.DataFrame:
    abas = listar_abas()
    aba = abas[indice]
    df = pd.read_excel(arquivo_origem, sheet_name=aba)
    df.columns = df.columns.str.strip().str.upper().str.replace(" ", "_")
    df = df.dropna(how="all")
    return df


def tratar_colunas_strings(df: pd.DataFrame, colunas: list) -> pd.DataFrame:
    for col in colunas:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip()
    return df


def formatar_reais(valor, com_simbolo=True, casas_decimais=2):
    if casas_decimais == 2:
        return reais(valor, simbolo=com_simbolo)

    try:
        if isinstance(valor, str):
            valor = re.sub(r'[^\d,.-]', '', valor).replace(',', '.')
        num = float(valor)
        formatado = f"{num:,.{casas_decimais}f}"
        formatado = formatado.replace(",", "X").replace(".", ",").replace("X", ".")
        return f"R$ {formatado}" if com_simbolo else formatado
    except (ValueError, TypeError):
        return "R$ 0,00" if com_simbolo else "0,00"


def definir_status(data_pagamento):
    if pd.isna(data_pagamento):
        return "Projetado"
    elif pd.Timestamp(data_pagamento) > hoje:
        return "A Vencer"
    else:
        return "Pago"


def get_saldo_dia(df: pd.DataFrame, data: pd.Timestamp) -> dict:
    """Calcula entradas, saídas e saldo do dia"""
    df_dia = df[df["DATA_EMISSAO"].dt.date == data.date()]

    entradas_dia = df_dia[df_dia["TIPO_FLUXO"] == "Entrada"]["VALOR_ABS"].sum()
    saidas_dia = df_dia[df_dia["TIPO_FLUXO"] == "Saída"]["VALOR_ABS"].sum()
    saldo_dia = entradas_dia - saidas_dia

    return {
        "entradas": entradas_dia,
        "saidas": saidas_dia,
        "saldo": saldo_dia
    }


# ==========================================
# DIMENSÕES
# ==========================================

def build_dim_planoContas() -> pd.DataFrame:
    df = ler_aba(13)
    df = tratar_colunas_strings(df, ["PLANO_DE_CONTA_ID"])
    return df


def build_dim_CentroCusto() -> pd.DataFrame:
    df = ler_aba(9)
    df = df.rename(columns={"ID_CENTRO_CUSTO": "COD_CC", "CENTRO_DE_CUSTO": "NOME_CENTRO_CUSTO"})
    df = tratar_colunas_strings(df, ["COD_CC"])
    return df


def build_dim_Empresa() -> pd.DataFrame:
    d_estoque = ler_aba(4)
    estoque_filial = ler_aba(5)
    d_filial = ler_aba(6)
    empresa_filial = ler_aba(7)
    d_empresa = ler_aba(8)
    d_centro_custo = build_dim_CentroCusto()

    d_estoque = d_estoque.rename(columns={"COD-ESTOQUE": "COD_ESTOQUE"})
    d_filial = d_filial.rename(columns={"ID": "COD_FILIAL", "EMPRESA": "NOME_FILIAL"})
    d_empresa = d_empresa.rename(columns={"ID": "COD_EMPRESA", "EMPRESA": "NOME_EMPRESA"})

    dim = estoque_filial.merge(d_estoque, on="COD_ESTOQUE", how="left")
    dim = dim.merge(empresa_filial, on="COD_FILIAL", how="left")
    dim = dim.merge(d_filial, on="COD_FILIAL", how="left")
    dim = dim.merge(d_empresa, on="COD_EMPRESA", how="left")
    dim = dim.merge(d_centro_custo, on="COD_CC", how="left")

    dim["COD_ESTOQUE"] = dim["COD_ESTOQUE"].astype(str).str.replace(
        r"EST-(\d+)", lambda m: f"EST-{int(m.group(1)):03d}", regex=True
    )
    dim["COD_CC"] = dim["COD_CC"].astype(str).str.replace(
        r"CC-(\d+)", lambda m: f"CC-{int(m.group(1)):03d}", regex=True
    )
    return dim


# ==========================================
# FATO MOVIMENTAÇÕES
# ==========================================

def fato_movimentacoes(dim_plano_contas: pd.DataFrame, dim_empresa: pd.DataFrame,
                       dim_centro_custo: pd.DataFrame) -> pd.DataFrame:
    fato = ler_aba(11)

    colunas_tratar = ["NOTA", "PLANO_DE_CONTA_ID", "PLANO_DE_CONTAS", "ID_CENTRO_CUSTO", "CENTRO_DE_CUSTO"]
    fato = tratar_colunas_strings(fato, colunas_tratar)

    # Merge com plano de contas
    if not dim_plano_contas.empty and "PLANO_DE_CONTA_ID" in fato.columns:
        fato = fato.merge(dim_plano_contas, on="PLANO_DE_CONTA_ID", how="left", suffixes=("", "_PC"))

    # Merge com centro de custo
    if not dim_centro_custo.empty and "ID_CENTRO_CUSTO" in fato.columns:
        fato = fato.merge(dim_centro_custo, left_on="ID_CENTRO_CUSTO", right_on="COD_CC", how="left",
                          suffixes=("", "_CC"))

    # Merge com empresa
    if not dim_empresa.empty and "ID_CENTRO_CUSTO" in fato.columns:
        colunas_empresa = [c for c in ["COD_CC", "NOME_FILIAL", "NOME_EMPRESA", "COD_FILIAL", "COD_EMPRESA"]
                           if c in dim_empresa.columns]
        fato = fato.merge(
            dim_empresa[colunas_empresa].drop_duplicates(subset=["COD_CC"]),
            left_on="ID_CENTRO_CUSTO",
            right_on="COD_CC",
            how="left",
            suffixes=("", "_EMP")
        )

    # Converter datas
    for col_data in ["DATA_EMISSAO", "DATA_PAGAMENTO"]:
        if col_data in fato.columns:
            fato[col_data] = pd.to_datetime(fato[col_data], errors="coerce")

    # Converter valor preservando sinal
    if "VALOR" in fato.columns:
        fato["VALOR"] = fato["VALOR"].apply(converter_para_float_seguro)

    # Colunas calculadas
    fato["STATUS"] = fato["DATA_PAGAMENTO"].apply(definir_status)
    fato["TIPO_FLUXO"] = fato["VALOR"].apply(lambda v: "Entrada" if v >= 0 else "Saída")
    fato["VALOR_ABS"] = fato["VALOR"].abs()

    return fato


# ==========================================
# CACHE
# ==========================================

@st.cache_data
def carregar_dados_completos():
    with st.spinner("🔄 Carregando dados..."):
        dim_planoContas = build_dim_planoContas()
        dim_CentroCusto = build_dim_CentroCusto()
        dim_empresa = build_dim_Empresa()
        fato = fato_movimentacoes(dim_planoContas, dim_empresa, dim_CentroCusto)
    return fato


# ==========================================
# FUNÇÕES AUXILIARES
# ==========================================

def get_coluna_segura(df: pd.DataFrame, coluna: str, valor_padrao="Todos"):
    if coluna in df.columns and not df[coluna].empty:
        valores = df[coluna].dropna().unique().tolist()
        valores = [v for v in valores if str(v).strip() and str(v) not in ['nan', 'None', '']]
        if valores:
            return [valor_padrao] + sorted(valores)
    return [valor_padrao]


def aplicar_filtro_seguro(df: pd.DataFrame, coluna: str, valor: str, valor_padrao="Todos"):
    if valor != valor_padrao and coluna in df.columns:
        return df[df[coluna] == valor]
    return df


def build_waterfall_filial(df: pd.DataFrame) -> go.Figure:
    """Waterfall de entrada, saída e saldo por filial"""
    if df.empty or "NOME_FILIAL" not in df.columns:
        return None

    # Agrupa por filial
    resumo = (
        df.groupby("NOME_FILIAL").agg(
            ENTRADA=("VALOR_ABS", lambda x: x[df.loc[x.index, "TIPO_FLUXO"] == "Entrada"].sum()),
            SAIDA=("VALOR_ABS", lambda x: x[df.loc[x.index, "TIPO_FLUXO"] == "Saída"].sum()),
        ).reset_index()
    )
    resumo["SALDO"] = resumo["ENTRADA"] - resumo["SAIDA"]
    resumo = resumo.sort_values("SALDO", ascending=False)

    # Montar traces do waterfall — uma filial por vez
    x_labels = []
    y_values = []
    texto = []
    cores = []
    medidas = []

    for _, row in resumo.iterrows():
        filial = row["NOME_FILIAL"]

        # Entrada
        x_labels.append(f"{filial}<br>Entrada")
        y_values.append(row["ENTRADA"])
        texto.append(formatar_reais(row["ENTRADA"]))
        cores.append("#10b981")
        medidas.append("absolute")

        # Saída
        x_labels.append(f"{filial}<br>Saída")
        y_values.append(-row["SAIDA"])
        texto.append(formatar_reais(row["SAIDA"]))
        cores.append("#ef4444")
        medidas.append("relative")

        # Saldo
        x_labels.append(f"{filial}<br>Saldo")
        y_values.append(row["SALDO"])
        texto.append(formatar_reais(row["SALDO"]))
        cor_saldo = "#3b82f6" if row["SALDO"] >= 0 else "#f59e0b"
        cores.append(cor_saldo)
        medidas.append("total")

    fig = go.Figure(go.Waterfall(
        x=x_labels,
        y=y_values,
        measure=medidas,
        text=texto,
        textposition="outside",
        connector={"line": {"color": "#334155", "width": 1}},
        decreasing={"marker": {"color": "#ef4444"}},
        increasing={"marker": {"color": "#10b981"}},
        totals={"marker": {"color": "#3b82f6"}},
    ))

    fig.update_layout(
        template="plotly_dark",
        height=500,
        title="💧 Waterfall — Entrada, Saída e Saldo por Filial",
        xaxis_title="",
        yaxis_title="Valor (R$)",
        showlegend=False,
        xaxis={"tickangle": -30}
    )

    return fig


def build_tabela_saldo_mensal_filial(df: pd.DataFrame) -> pd.DataFrame:
    """Monta tabela de saldo mensal por filial"""
    if df.empty or "NOME_FILIAL" not in df.columns:
        return pd.DataFrame()

    df_copy = df.copy()
    df_copy["MES"] = df_copy["DATA_EMISSAO"].dt.strftime("%b/%y")
    df_copy["MES_ORD"] = df_copy["DATA_EMISSAO"].dt.to_period("M")

    meses_ord = (
        df_copy[["MES", "MES_ORD"]]
        .drop_duplicates()
        .sort_values("MES_ORD")["MES"]
        .tolist()
    )

    filiais = sorted(df_copy["NOME_FILIAL"].dropna().unique())

    rows = []
    for filial in filiais:
        df_fil = df_copy[df_copy["NOME_FILIAL"] == filial]
        row = {"Filial": filial}

        saldos = []
        for mes in meses_ord:
            df_mes = df_fil[df_fil["MES"] == mes]
            entrada = df_mes[df_mes["TIPO_FLUXO"] == "Entrada"]["VALOR_ABS"].sum()
            saida = df_mes[df_mes["TIPO_FLUXO"] == "Saída"]["VALOR_ABS"].sum()
            saldo = entrada - saida
            saldos.append(saldo)
            row[mes] = saldo

        row["TOTAL"] = sum(saldos)
        rows.append(row)

    # Linha de totais
    row_total = {"Filial": "TOTAL GERAL"}
    for mes in meses_ord:
        row_total[mes] = sum(r[mes] for r in rows)
    row_total["TOTAL"] = sum(r["TOTAL"] for r in rows)
    rows.append(row_total)

    return pd.DataFrame(rows).set_index("Filial"), meses_ord


def estilo_saldo(val):
    """Colore célula conforme saldo positivo/negativo"""
    try:
        num = float(str(val).replace("R$", "").replace(".", "").replace(",", ".").replace(" ", "").replace("−", "-"))
        if num > 0:
            return "background-color: #064e3b; color: #6ee7b7; font-weight: 600"
        elif num < 0:
            return "background-color: #7f1d1d; color: #fca5a5; font-weight: 600"
        else:
            return "color: #94a3b8"
    except:
        return ""


def build_tabela_resultado_filial(df: pd.DataFrame) -> pd.DataFrame:
    """Monta tabela de resultado por filial com tendência"""
    if df.empty or "NOME_FILIAL" not in df.columns:
        return pd.DataFrame()

    # Agrupa por filial e mês para calcular tendência
    df_copy = df.copy()
    df_copy["MES_ORD"] = df_copy["DATA_EMISSAO"].dt.to_period("M")

    # Tendência: compara último mês com penúltimo mês do período
    meses = sorted(df_copy["MES_ORD"].dropna().unique())

    resultado = []
    for filial in sorted(df_copy["NOME_FILIAL"].dropna().unique()):
        df_fil = df_copy[df_copy["NOME_FILIAL"] == filial]

        entrada = df_fil[df_fil["TIPO_FLUXO"] == "Entrada"]["VALOR_ABS"].sum()
        saida = df_fil[df_fil["TIPO_FLUXO"] == "Saída"]["VALOR_ABS"].sum()
        saldo = entrada - saida

        # Calcular tendência do saldo (último vs penúltimo mês)
        if len(meses) >= 2:
            mes_atual = meses[-1]
            mes_ant = meses[-2]

            saldo_atual = (
                df_fil[df_fil["MES_ORD"] == mes_atual]["VALOR"].sum()
            )
            saldo_ant = (
                df_fil[df_fil["MES_ORD"] == mes_ant]["VALOR"].sum()
            )

            if saldo_ant != 0:
                var_pct = ((saldo_atual - saldo_ant) / abs(saldo_ant)) * 100
                if var_pct > 5:
                    tendencia = "📈 Alta"
                    cor_tend = "#10b981"
                elif var_pct < -5:
                    tendencia = "📉 Queda"
                    cor_tend = "#ef4444"
                else:
                    tendencia = "➡️ Estável"
                    cor_tend = "#f59e0b"
                var_fmt = f"{'+' if var_pct > 0 else ''}{var_pct:.1f}%"
            else:
                tendencia = "➡️ Estável"
                cor_tend = "#f59e0b"
                var_fmt = "—"
        else:
            tendencia = "—"
            cor_tend = "#94a3b8"
            var_fmt = "—"

        resultado.append({
            "NOME_FILIAL": filial,
            "ENTRADA": entrada,
            "SAIDA": saida,
            "SALDO": saldo,
            "TENDENCIA": tendencia,
            "VAR_PCT": var_fmt,
            "COR_TEND": cor_tend,
        })

    return pd.DataFrame(resultado)


def build_dre(df: pd.DataFrame) -> pd.DataFrame:
    """Monta o mini DRE mensal com total"""
    if df.empty or "DATA_EMISSAO" not in df.columns:
        return pd.DataFrame()

    df_copy = df[df["TIPO_PLANO_DE_CONTA"] != "Transferência"].copy()
    df_copy["MES"] = df_copy["DATA_EMISSAO"].dt.strftime("%b/%y")
    df_copy["MES_ORD"] = df_copy["DATA_EMISSAO"].dt.to_period("M")

    # Ordenar meses cronologicamente
    meses_ord = (
        df_copy[["MES", "MES_ORD"]]
        .drop_duplicates()
        .sort_values("MES_ORD")["MES"]
        .tolist()
    )

    # Mapeamento de grupos para linhas do DRE
    mapa_dre = {
        "Receitas Operacionais": ("1. Receita Bruta", 1),
        "Deduções de Receita": ("2. (-) Deduções", 2),
        "Custos e Infraestrutura Fixa": ("4. (-) Custos", 4),
        "Despesas Administrativas": ("5. (-) Desp. Administrativas", 5),
        "Recursos Humanos": ("6. (-) Recursos Humanos", 6),
        "Despesas Comerciais": ("7. (-) Desp. Comerciais", 7),
    }

    # Agrupa por grupo e mês
    agrupado = (
        df_copy.groupby(["GRUPO", "MES"])["VALOR"]
        .sum()
        .reset_index()
    )

    linhas = {}
    for grupo, (label, ordem) in mapa_dre.items():
        row = {"OPERAÇÃO": label, "_ORDEM": ordem}
        for mes in meses_ord:
            val = agrupado[(agrupado["GRUPO"] == grupo) & (agrupado["MES"] == mes)]["VALOR"].sum()
            row[mes] = val
        row["TOTAL"] = sum(row[m] for m in meses_ord)
        linhas[label] = row

    # Linhas calculadas
    def linha_calculada(label, ordem, fn):
        row = {"OPERAÇÃO": label, "_ORDEM": ordem}
        for mes in meses_ord:
            row[mes] = fn(mes)
        row["TOTAL"] = fn("TOTAL")
        return row

    rec_liq = linha_calculada(
        "3. = Receita Líquida", 3,
        lambda m: linhas["1. Receita Bruta"].get(m, 0) + linhas["2. (-) Deduções"].get(m, 0)
    )

    ebitda = linha_calculada(
        "8. = EBITDA", 8,
        lambda m: (
                rec_liq.get(m, 0)
                + linhas["4. (-) Custos"].get(m, 0)
                + linhas["5. (-) Desp. Administrativas"].get(m, 0)
                + linhas["6. (-) Recursos Humanos"].get(m, 0)
                + linhas["7. (-) Desp. Comerciais"].get(m, 0)
        )
    )

    todas_linhas = sorted(
        list(linhas.values()) + [rec_liq, ebitda],
        key=lambda x: x["_ORDEM"]
    )

    df_dre = pd.DataFrame(todas_linhas).drop(columns=["_ORDEM"])
    df_dre = df_dre.set_index("OPERAÇÃO")

    return df_dre, meses_ord


def formatar_dre(val, base_receita_liq=None, mostrar_pct=True, mostrar_var=True, mes_ant_val=None):
    """Formata célula do DRE com valor + % + variação"""
    if pd.isna(val) or val == 0:
        return "—"

    valor_fmt = formatar_reais(val)
    partes = [valor_fmt]

    if mostrar_pct and base_receita_liq and base_receita_liq != 0:
        pct = (val / base_receita_liq) * 100
        partes.append(f"{pct:.1f}%")

    if mostrar_var and mes_ant_val is not None and mes_ant_val != 0:
        var = ((val - mes_ant_val) / abs(mes_ant_val)) * 100
        sinal = "+" if var > 0 else ""
        partes.append(f"{sinal}{var:.1f}% vs ant.")

    return " | ".join(partes)


# ==========================================
# INTERFACE
# ==========================================

st.set_page_config(page_title="Fluxo de Caixa", layout="wide")
cores = render_page()
cor_verde = '#10b981'
cor_vermelho = '#ef4444'
st.markdown("""
        <style>
            .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        </style>
    """, unsafe_allow_html=True)

st.title("💰 Fluxo de Caixa")

fato = carregar_dados_completos()

if fato.empty:
    st.error("❌ Nenhum dado foi carregado. Verifique o arquivo Excel.")
    st.stop()

# ==========================================
# FILTROS
# ==========================================

st.markdown("### 🔎 Parâmetros de Busca")

col1, col2, col3, col4 = st.columns(4)

with col1:
    filial_sel = st.selectbox("🏪 Filial", get_coluna_segura(fato, "NOME_FILIAL"))

with col2:
    cc_sel = st.selectbox("📌 Centro de Custo", get_coluna_segura(fato, "NOME_CENTRO_CUSTO"))

with col3:
    status_sel = st.selectbox("✅ Status", ["Todos", "Pago", "A Vencer", "Projetado"])

with col4:
    tipo_sel = st.selectbox("📊 Tipo", ["Todos", "Entrada", "Saída"])

col5, col6, col7, col8 = st.columns(4)

with col5:
    plano_sel = st.selectbox("📂 Plano de Contas", get_coluna_segura(fato, "PLANO_DE_CONTAS"))

with col6:
    empresa_sel = st.selectbox("🏢 Empresa", get_coluna_segura(fato, "NOME_EMPRESA"))

with col7:
    if "DATA_EMISSAO" in fato.columns:
        data_min_e = fato["DATA_EMISSAO"].min()
        data_max_e = fato["DATA_EMISSAO"].max()
        periodo_emissao = st.date_input(
            "📅 Período de Emissão",
            value=[data_min_e, data_max_e],
            min_value=data_min_e, max_value=data_max_e,
            key="periodo_emissao"
        )
    else:
        periodo_emissao = []

with col8:
    if "DATA_PAGAMENTO" in fato.columns:
        datas_pgto = fato["DATA_PAGAMENTO"].dropna()
        if not datas_pgto.empty:
            data_min_p = datas_pgto.min()
            data_max_p = datas_pgto.max()
            periodo_pagamento = st.date_input(
                "📅 Período de Pagamento",
                value=[data_min_p, data_max_p],
                min_value=data_min_p, max_value=data_max_p,
                key="periodo_pagamento"
            )
        else:
            periodo_pagamento = []
    else:
        periodo_pagamento = []

st.markdown("---")
_, col_btn = st.columns([5, 1])
with col_btn:
    if st.button("🧹 Limpar Filtros", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# ==========================================
# APLICAR FILTROS
# ==========================================

df_filtrado = fato.copy()

df_filtrado = aplicar_filtro_seguro(df_filtrado, "NOME_FILIAL", filial_sel)
df_filtrado = aplicar_filtro_seguro(df_filtrado, "NOME_CENTRO_CUSTO", cc_sel)
df_filtrado = aplicar_filtro_seguro(df_filtrado, "STATUS", status_sel)
df_filtrado = aplicar_filtro_seguro(df_filtrado, "TIPO_FLUXO", tipo_sel)
df_filtrado = aplicar_filtro_seguro(df_filtrado, "PLANO_DE_CONTAS", plano_sel)
df_filtrado = aplicar_filtro_seguro(df_filtrado, "NOME_EMPRESA", empresa_sel)

if len(periodo_emissao) == 2 and "DATA_EMISSAO" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        (df_filtrado["DATA_EMISSAO"] >= pd.to_datetime(periodo_emissao[0])) &
        (df_filtrado["DATA_EMISSAO"] <= pd.to_datetime(periodo_emissao[1]))
        ]

if len(periodo_pagamento) == 2 and "DATA_PAGAMENTO" in df_filtrado.columns:
    df_filtrado = df_filtrado[
        (df_filtrado["DATA_PAGAMENTO"] >= pd.to_datetime(periodo_pagamento[0])) &
        (df_filtrado["DATA_PAGAMENTO"] <= pd.to_datetime(periodo_pagamento[1]))
        ]

# ==========================================
# CARDS
# ==========================================

html_card = """
    <div class="card-style"style="background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); padding: 20px; border-radius: 12px; border-top: 4px solid {color}; color: white; min-height: 120px; box-shadow: 0 4px 15px rgba(0,0,0,0.25); margin-bottom: 8px;">
        <div style="font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; color: #94a3b8; margin-bottom: 6px;">{title}</div>
        <div style="font-size: 22px; font-weight: 700; color: #f8fafc; line-height: 1.1; margin-bottom: 4px;">{value}</div>
        <div style="font-size: 11px; color: {subcolor};">{subtext}</div>
    </div>
    """

entradas = df_filtrado[df_filtrado["TIPO_FLUXO"] == "Entrada"]
saidas = df_filtrado[df_filtrado["TIPO_FLUXO"] == "Saída"]

total_entradas = entradas["VALOR_ABS"].sum()
recebido = entradas[entradas["STATUS"] == "Pago"]["VALOR_ABS"].sum()
proj_entrada = entradas[entradas["STATUS"] == "Projetado"]["VALOR_ABS"].sum()

total_saidas = saidas["VALOR_ABS"].sum()
pago = saidas[saidas["STATUS"] == "Pago"]["VALOR_ABS"].sum()
proj_saida = saidas[saidas["STATUS"] == "Projetado"]["VALOR_ABS"].sum()

saldo = total_entradas - total_saidas
cor_saldo = "#10b981" if saldo >= 0 else "#ef4444"
cor_saldo_sub = "#6ee7b7" if saldo >= 0 else "#fca5a5"

inadimplentes = fato[
    (fato["TIPO_FLUXO"] == "Entrada") &
    (fato["STATUS"] == "Projetado") &
    (fato["DATA_EMISSAO"] < hoje)
    ]

a_vencer = df_filtrado[df_filtrado["STATUS"] == "A Vencer"]["VALOR_ABS"].sum()

c1, c2, c3, c4, c5, c6 = st.columns(6)
st.markdown("---")
saldo_hoje = get_saldo_dia(df_filtrado, hoje)
cor_dia = "#10b981" if saldo_hoje["saldo"] >= 0 else "#ef4444"
cor_dia_sub = "#6ee7b7" if saldo_hoje["saldo"] >= 0 else "#fca5a5"
with c1:
    st.markdown(html_card.format(
        title="A Receber",
        value=formatar_reais(total_entradas),
        subtext=f"✅ Recebido: {formatar_reais(recebido)} | 🔜 Proj.: {formatar_reais(proj_entrada)}",
        color="#10b981", subcolor="#6ee7b7"
    ), unsafe_allow_html=True)

with c2:
    st.markdown(html_card.format(
        title="A Pagar",
        value=formatar_reais(total_saidas),
        subtext=f"✅ Pago: {formatar_reais(pago)} | 🔜 Proj.: {formatar_reais(proj_saida)}",
        color="#ef4444", subcolor="#fca5a5"
    ), unsafe_allow_html=True)

with c3:
    st.markdown(html_card.format(
        title="Saldo do Período",
        value=formatar_reais(saldo),
        subtext="✅ Resultado positivo" if saldo >= 0 else "⚠️ Resultado negativo",
        color=cor_saldo, subcolor=cor_saldo_sub
    ), unsafe_allow_html=True)

with c4:
    st.markdown(html_card.format(
        title="Inadimplência",
        value=formatar_reais(inadimplentes["VALOR_ABS"].sum()),
        subtext=f"📋 {len(inadimplentes)} títulos em aberto",
        color="#f59e0b", subcolor="#fbbf24"
    ), unsafe_allow_html=True)

with c5:
    st.markdown(html_card.format(
        title="A Vencer",
        value=formatar_reais(a_vencer),
        subtext="📅 No período filtrado",
        color="#8b5cf6", subcolor="#a78bfa"
    ), unsafe_allow_html=True)
with c6:
    st.markdown(html_card.format(
        title=f"Saldo Hoje — {hoje.strftime('%d/%m/%Y')}",
        value=formatar_reais(saldo_hoje["saldo"]),
        subtext="✅ Positivo" if saldo_hoje["saldo"] >= 0 else "⚠️ Negativo",
        color=cor_dia, subcolor=cor_dia_sub
    ), unsafe_allow_html=True)
# ==========================================
# GRÁFICOS
# ==========================================

st.markdown("---")
st.subheader("📈 Evolução do Fluxo")
with st.container(border=True, gap="xsmall"):
    gran_col, _ = st.columns([1, 3])
    with gran_col:
        granularidade = st.radio("Visualizar por", ["Mensal", "Semanal", "Diário"], horizontal=True)

    df_graf = df_filtrado.copy()

    if granularidade == "Mensal":
        df_graf["PERIODO"] = df_graf["DATA_EMISSAO"].dt.strftime("%m/%Y")
    elif granularidade == "Semanal":
        df_graf["PERIODO"] = df_graf["DATA_EMISSAO"].dt.strftime("%Y-W%W")
    else:
        df_graf["PERIODO"] = df_graf["DATA_EMISSAO"].dt.strftime("%Y-%m-%d")

    evolucao = (
        df_graf.groupby(["PERIODO", "TIPO_FLUXO", "STATUS"])["VALOR_ABS"]
        .sum().reset_index()
        .sort_values("PERIODO")
    )

    if not evolucao.empty:
        fig_evolucao = px.bar(
            evolucao,
            x="PERIODO", y="VALOR_ABS",
            color="TIPO_FLUXO", barmode="group",
            pattern_shape="STATUS",

            pattern_shape_map={"Pago": "", "A Vencer": ".", "Projetado": "/"},
            title="Entradas vs Saídas",
            text_auto=True,

            color_discrete_map={"Entrada": cores['cor_alerta_alerta_verde'],
                                "Saída": cores['cor_alerta_alerta_vermelho']},
        )
        fig_evolucao.update_traces(
            text=evolucao["VALOR_ABS"].apply(lambda v: formatar_reais(v)),
            texttemplate='%{text}',
           # textposition='inside',
           # insidetextanchor='middle',
            textfont=dict(family="sans-serif", size=11, color="#ffffff", weight="bold")
        )
        fig_evolucao.update_layout(
            template="plotly_dark",
            height=400,
            legend_title_text="",
            # xaxis_title="Período",
            # yaxis_title="Valor (R$)",
            xaxis=dict(title=None, showgrid=False, tickfont=dict(color=cores["sidebar_texto"])),
            yaxis=dict(title=None, showgrid=True, gridcolor="#94a3b8", tickfont=dict(color=cores["sidebar_texto"])),
            #  legend_title="Tipo"
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.05,
                xanchor="center",
                x=0.5,
               # title_text="Entradas vs Saídas"
            )
        )
        st.plotly_chart(fig_evolucao, use_container_width=True)
    else:
        st.info("Sem dados para o período selecionado")
st.markdown("---")
#st.subheader("📂 Por Plano de Contas")
g1, g2 = st.columns(2)

with g1:
    with st.container(border=True, gap="xsmall"):
        if "PLANO_DE_CONTAS" in df_filtrado.columns:
            fluxo_pc = (
                df_filtrado.dropna(subset=["PLANO_DE_CONTAS"])
                .groupby(["PLANO_DE_CONTAS", "TIPO_FLUXO"])["VALOR_ABS"].sum()
                .reset_index()
                .sort_values("VALOR_ABS", ascending=True)
            )
            if not fluxo_pc.empty:
                # 1. Criamos a coluna formatada com o seu .apply antes do gráfico
                fluxo_pc["VALOR_FORMATADO"] = fluxo_pc["VALOR_ABS"].apply(lambda v: formatar_reais(v))

                fig_pc = px.bar(
                    fluxo_pc,
                    x="VALOR_ABS",
                    y="PLANO_DE_CONTAS",
                    color="TIPO_FLUXO",
                    orientation="h", barmode="group",
                    title="Fluxo por Plano de Contas",
                    color_discrete_map={"Entrada": cores['cor_alerta_alerta_verde'],
                                        "Saída": cores['cor_alerta_alerta_vermelho']},
                )
                fig_pc.update_traces(

                    text=fluxo_pc["VALOR_FORMATADO"],
                    texttemplate='%{text}',
                    textposition='outside',
                    cliponaxis=False,


                    textfont=dict(
                        family="sans-serif",
                        size=12,
                        color=cores['sidebar_texto'],
                        weight="bold"
                    ),


                    customdata=list(zip(fluxo_pc["TIPO_FLUXO"], fluxo_pc["VALOR_FORMATADO"])),
                    hovertemplate=(
                        "<b>Plano de Contas:</b> %{y}<br>"
                        "<b>Tipo:</b> %{customdata[0]}<br>"
                        "<b>Valor:</b> %{customdata[1]}<br>"
                        "<extra></extra>"
                    )
                )
                fig_pc.update_layout(
                    template="plotly_dark",
                    legend_title_text="",
                    height=450, # Altura padrão excelente para telas sem precisar de scroll
                    yaxis_title="",
                    margin=dict(b=40, l=15, r=25, t=60),

                    xaxis=dict(title=None, showgrid=False, zeroline=False, tickfont=dict(color=cores["sidebar_texto"])),
                    yaxis=dict(showgrid=False,automargin=True, zeroline=False, tickfont=dict(color=cores["sidebar_texto"])),

                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    )
                )
                st.plotly_chart(fig_pc, use_container_width=True)
            else:
                st.info("Sem dados de plano de contas")
with g2:
    with st.container(border=True, gap="xsmall"):
        if "NOME_CENTRO_CUSTO" in df_filtrado.columns:
            fluxo_cc = (
                df_filtrado.dropna(subset=["NOME_CENTRO_CUSTO"])
                .groupby(["NOME_CENTRO_CUSTO", "TIPO_FLUXO"])["VALOR_ABS"].sum()
                .reset_index()
                .sort_values("VALOR_ABS", ascending=True)
            )
            if not fluxo_cc.empty:
                # 1. Criamos a coluna formatada direto no DataFrame para travar o valor na barra certa
                fluxo_cc["VALOR_FORMATADO"] = fluxo_cc["VALOR_ABS"].apply(lambda v: formatar_reais(v))

                # 2. Criamos o gráfico mapeando a coluna text direto aqui dentro
                fig_cc = px.bar(
                    fluxo_cc,
                    x="VALOR_ABS",
                    y="NOME_CENTRO_CUSTO",
                    color="TIPO_FLUXO",
                    orientation="h",
                    barmode="group",  # 👈 Deixa as barras pareadas/lado a lado
                    title="Fluxo por Centro de Custo",
                    text="VALOR_FORMATADO", # 👈 Amarra o valor correto a cada barra
                    color_discrete_map={
                        "Entrada": cores['cor_alerta_alerta_verde'],
                        "Saída": cores['cor_alerta_alerta_vermelho']
                    }
                )

                # 3. Aplicamos a cor vermelha que você configurou nos rótulos externos
                fig_cc.update_traces(
                    texttemplate='%{text}',
                    textposition='outside',
                    cliponaxis=False,
                    textfont=dict(
                        family="sans-serif",
                        size=12,
                        color=cores["sidebar_texto"]    ,
                        weight="bold"
                    ),
                    customdata=fluxo_cc["TIPO_FLUXO"],
                    hovertemplate=(
                        "<b>Centro de Custo:</b> %{y}<br>"
                        "<b>Tipo:</b> %{customdata}<br>"
                        "<b>Valor:</b> %{text}<br>"
                        "<extra></extra>"
                    )
                )

                fig_cc.update_layout(
                    template="plotly_dark",
                    legend_title_text="",
                    height=450,
                    yaxis_title="",
                    margin=dict(b=40, l=15, r=120, t=60), # Dá espaço na direita para o R$ não sumir

                    xaxis=dict(title=None, showgrid=False, zeroline=False, tickfont=dict(color=cores["sidebar_texto"])),
                    yaxis=dict(
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(color=cores["sidebar_texto"]),
                        automargin=True # Faz o nome da Loja aparecer inteiro sem cortar
                    ),
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    )
                )

                st.plotly_chart(fig_cc, use_container_width=True)
            else:
                st.info("Sem dados de centro de custo")




g3, g4 = st.columns(2)

with g3:
    with st.container(border=True, gap="xsmall"):
       # st.subheader("📤 Saídas por Plano de Contas")
        if "PLANO_DE_CONTAS" in df_filtrado.columns:
            saidas_pc = (
                df_filtrado[df_filtrado["TIPO_FLUXO"] == "Saída"]
                .dropna(subset=["PLANO_DE_CONTAS"])
                .groupby("PLANO_DE_CONTAS")["VALOR_ABS"].sum()
                .reset_index()
                .sort_values("VALOR_ABS", ascending=True)
            )
            if not saidas_pc.empty:
                # 1. Cria a coluna de texto amarrada ao DataFrame para não duplicar dados
                saidas_pc["VALOR_FORMATADO"] = saidas_pc["VALOR_ABS"].apply(lambda v: formatar_reais(v))

                # 2. Monta o gráfico passando o texto formatado direto aqui dentro
                fig_saidas_pc = px.bar(
                    saidas_pc,
                    x="VALOR_ABS",
                    y="PLANO_DE_CONTAS",
                    orientation="h",
                    title="Saídas por Plano de Contas",
                    color="VALOR_ABS",
                    text="VALOR_FORMATADO",  # 👈 Trava o valor correto para cada barra correspondente
                    color_continuous_scale=["#ef4444", "#991b1b"]
                )

                # 3. Ajustes nos rótulos e direções dos textos (Travados na horizontal por fora)
                fig_saidas_pc.update_traces(
                    texttemplate='%{text}',
                    textposition='outside',  # 👈 Joga o texto para fora da barra
                    cliponaxis=False,
                    textangle=0,
                    textfont=dict(
                        family="sans-serif",
                        size=12,
                        color=cores['sidebar_texto'],  # Branco para destacar bem no fundo escuro
                        weight="bold"
                    ),
                    # Mantém o padrão de hover minimalista e limpo
                    hovertemplate=(
                        "<b>Plano de Contas:</b> %{y}<br>"
                        "<b>Valor:</b> %{text}<br>"
                        "<extra></extra>"
                    )
                )

                # 4. Ajuste completo de layout e margens idêntico aos anteriores
                fig_saidas_pc.update_layout(
                    template="plotly_dark",
                    height=450,  # Altura padronizada
                    margin=dict(b=40, l=200, r=150, t=60),  # Margens generosas para os textos horizontais

                    # Oculta a linha do eixo X para focar nos rótulos de fora das barras
                    xaxis=dict(title=None, showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(color=cores["sidebar_texto"]),
                        automargin=True,
                        ticklabelstandoff=20
                    ),
                    coloraxis_showscale=False,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    )
                )
                st.plotly_chart(fig_saidas_pc, use_container_width=True)
            else:
                st.info("Sem saídas no período filtrado")
with g4:
    with st.container(border=True, gap="xsmall"):
       # st.subheader("📥 Entradas por Plano de Contas")
        if "PLANO_DE_CONTAS" in df_filtrado.columns:
            entradas_pc = (
                df_filtrado[df_filtrado["TIPO_FLUXO"] == "Entrada"]
                .dropna(subset=["PLANO_DE_CONTAS"])
                .groupby("PLANO_DE_CONTAS")["VALOR_ABS"].sum()
                .reset_index()
                .sort_values("VALOR_ABS", ascending=True)
            )
            if not entradas_pc.empty:
                # 1. Cria a coluna de texto amarrada ao DataFrame para evitar que os dados embaralhem
                entradas_pc["VALOR_FORMATADO"] = entradas_pc["VALOR_ABS"].apply(lambda v: formatar_reais(v))

                # 2. Monta o gráfico passando a coluna de texto diretamente no construtor
                fig_entradas_pc = px.bar(
                    entradas_pc,
                    x="VALOR_ABS",
                    y="PLANO_DE_CONTAS",
                    orientation="h",
                    title="Entradas por Plano de Contas",
                    color="VALOR_ABS",
                    text="VALOR_FORMATADO",  # 👈 Trava o valor correto na ponta de cada barra
                    color_continuous_scale=["#10b981", "#065f46"]
                )

                # 3. Ajustes de posição, ângulo e cor dos rótulos
                fig_entradas_pc.update_traces(
                    texttemplate='%{text}',
                    textposition='outside',  # 👈 Joga o texto para fora da barra
                    cliponaxis=False,
                    textangle=0,  # 👈 Garante o texto 100% deitado na horizontal
                    textfont=dict(
                        family="sans-serif",
                        size=12,
                        color=cores['sidebar_texto'],  # Letra branca bem visível no fundo escuro
                        weight="bold"
                    ),
                    hovertemplate=(
                        "<b>Plano de Contas:</b> %{y}<br>"
                        "<b>Valor:</b> %{text}<br>"
                        "<extra></extra>"
                    )
                )

                # 4. Alinhamento de layout e margens idêntico aos blocos g1, g2 e g3
                fig_entradas_pc.update_layout(
                    template="plotly_dark",
                    height=450,
                    margin=dict(b=40, l=200, r=150, t=60),  # Margens amplas para os rótulos horizontais caberem

                    # Limpa as escalas numéricas do eixo X para focar no rótulo da barra
                    xaxis=dict(title=None, showgrid=False, zeroline=False, showticklabels=False),
                    yaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(color=cores["sidebar_texto"]),
                        automargin=True,
                        ticklabelstandoff=20  # 👈 Distância segura para o texto não encostar no nome do plano
                    ),
                    coloraxis_showscale=False,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    )
                )
                st.plotly_chart(fig_entradas_pc, use_container_width=True)
            else:
                st.info("Sem entradas no período filtrado")

g5, g6 = st.columns(2)

with g5:
    with st.container(border=True, gap="xsmall"):

        if "TIPO_PLANO_DE_CONTA" in df_filtrado.columns:

            fluxo_tipo_pc = (
                df_filtrado
                .dropna(subset=["TIPO_PLANO_DE_CONTA"])
                .groupby(["TIPO_PLANO_DE_CONTA", "TIPO_FLUXO"])["VALOR_ABS"]
                .sum()
                .reset_index()
                .sort_values("VALOR_ABS", ascending=True)
            )

            if not fluxo_tipo_pc.empty:

                fluxo_tipo_pc["VALOR_FORMATADO"] = fluxo_tipo_pc["VALOR_ABS"].apply(formatar_reais)

                fig_tipo_pc = px.bar(
                    fluxo_tipo_pc,
                    x="VALOR_ABS",
                    y="TIPO_PLANO_DE_CONTA",
                    color="TIPO_FLUXO",
                    orientation="h",
                    text="VALOR_FORMATADO",
                    barmode="group",
                    title="Entradas vs Saídas por Tipo de Plano",
                    color_discrete_map={
                        "Entrada": cores['cor_alerta_alerta_verde'],
                        "Saída": cores['cor_alerta_alerta_vermelho']
                    },
                    custom_data=["TIPO_FLUXO"]
                )

                fig_tipo_pc.update_traces(
                    texttemplate="%{text}",
                    textposition="outside",
                    cliponaxis=False,
                    textangle=0,
                    textfont=dict(
                        family="sans-serif",
                        size=12,
                        color=cores["sidebar_texto"]
                    ),
                    hovertemplate=(
                        "<b>Tipo de Plano:</b> %{y}<br>"
                        "<b>Fluxo:</b> %{customdata[0]}<br>"
                        "<b>Valor:</b> %{text}<br>"
                        "<extra></extra>"
                    )
                )
                min_valor = fluxo_tipo_pc["VALOR_ABS"].min()
                max_valor = fluxo_tipo_pc["VALOR_ABS"].max()
                fig_tipo_pc.update_layout(
                    template="plotly_dark",
                    height=450,
                    margin=dict(b=40, l=100, r=150, t=60),

                    xaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        showticklabels=False,
                        range=[min_valor * 0.8, max_valor * 1.15]
                    ),

                    yaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(color=cores["sidebar_texto"]),
                        automargin=True,
                        ticklabelstandoff=20
                    ),

                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=0.99,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    )
                )

                st.plotly_chart(fig_tipo_pc, use_container_width=True)

            else:
                st.info("Sem dados de tipo de plano de conta")

        else:
            st.info("Coluna TIPO_PLANO_DE_CONTA não encontrada")
with g6:
    with st.container(border=True, gap="xsmall"):

        if "GRUPO" in df_filtrado.columns:

            fluxo_grupo_pc = (
                df_filtrado
                .dropna(subset=["GRUPO"])
                .groupby(["GRUPO", "TIPO_FLUXO"])["VALOR_ABS"]
                .sum()
                .reset_index()
                .sort_values("VALOR_ABS", ascending=True)
            )

            if not fluxo_grupo_pc.empty:

                fluxo_grupo_pc["VALOR_FORMATADO"] = fluxo_grupo_pc["VALOR_ABS"].apply(formatar_reais)

                fig_grupo_pc = px.bar(
                    fluxo_grupo_pc,
                    x="VALOR_ABS",
                    y="GRUPO",
                    color="TIPO_FLUXO",
                    orientation="h",
                    text="VALOR_FORMATADO",
                    barmode="group",
                    title="Entradas vs Saídas por Grupo",
                    color_discrete_map={
                        "Entrada": cores['cor_alerta_alerta_verde'],
                        "Saída": cores['cor_alerta_alerta_vermelho']
                    },
                    custom_data=["TIPO_FLUXO"]
                )

                fig_grupo_pc.update_traces(
                    texttemplate="%{text}",
                    textposition="outside",
                    cliponaxis=False,
                    textangle=0,
                    textfont=dict(
                        family="sans-serif",
                        size=12,
                        color=cores["sidebar_texto"]
                    ),
                    hovertemplate=(
                        "<b>Grupo:</b> %{y}<br>"
                        "<b>Fluxo:</b> %{customdata[0]}<br>"
                        "<b>Valor:</b> %{text}<br>"
                        "<extra></extra>"
                    )
                )

                fig_grupo_pc.update_layout(
                    template="plotly_dark",
                    height=450,
                    margin=dict(b=40, l=200, r=150, t=60),

                    xaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        showticklabels=False
                    ),

                    yaxis=dict(
                        title=None,
                        showgrid=False,
                        zeroline=False,
                        tickfont=dict(color=cores["sidebar_texto"]),
                        automargin=True,
                        ticklabelstandoff=20
                    ),

                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.05,
                        xanchor="center",
                        x=0.5,
                        title_text=""
                    )
                )

                st.plotly_chart(fig_grupo_pc, use_container_width=True)

            else:
                st.info("Sem dados de grupo de plano de conta")

        else:
            st.info("Coluna GRUPO não encontrada")
st.markdown("---")
st.subheader("💧 Resultado por Filial")

# Agrupa o gráfico Waterfall dentro de um container com borda
with st.container(border=True):
    fig_wf = build_waterfall_filial(df_filtrado)
    if fig_wf:
        st.plotly_chart(fig_wf, use_container_width=True)
    else:
        st.info("Sem dados suficientes para o gráfico")

st.markdown("---")
st.subheader("🏪 Resultado por Filial")

df_resultado_filial = build_tabela_resultado_filial(df_filtrado)

# Agrupa a lista de cards das filiais dentro de um container com borda
with st.container(border=True):
    if not df_resultado_filial.empty:
        for _, row in df_resultado_filial.iterrows():
            cor_saldo = "#10b981" if row["SALDO"] >= 0 else "#ef4444"
            icone_saldo = "✅" if row["SALDO"] >= 0 else "⚠️"

            st.markdown(f"""
                <div style="
                    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
                    border-radius: 12px;
                    border-left: 5px solid {cor_saldo};
                    padding: 16px 24px;
                    margin-bottom: 10px;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.2);
                ">
                    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
                        <div style="font-size: 16px; font-weight: 700; color: #f8fafc; min-width: 180px;">
                            🏪 {row['NOME_FILIAL']}
                        </div>
                        <div style="display: flex; gap: 32px; flex-wrap: wrap;">
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 2px;">Entrada</div>
                                <div style="font-size: 15px; font-weight: 600; color: #10b981;">{formatar_reais(row['ENTRADA'])}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 2px;">Saída</div>
                                <div style="font-size: 15px; font-weight: 600; color: #ef4444;">{formatar_reais(row['SAIDA'])}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 2px;">Saldo</div>
                                <div style="font-size: 15px; font-weight: 700; color: {cor_saldo};">{icone_saldo} {formatar_reais(row['SALDO'])}</div>
                            </div>
                            <div style="text-align: center;">
                                <div style="font-size: 11px; color: #94a3b8; text-transform: uppercase; margin-bottom: 2px;">Tendência</div>
                                <div style="font-size: 14px; font-weight: 600; color: {row['COR_TEND']};">
                                    {row['TENDENCIA']} <span style="font-size: 12px;">({row['VAR_PCT']})</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("Sem dados suficientes para exibir resultado por filial")

st.markdown("---")
st.subheader("📅 Saldo Mensal por Filial")

resultado_mensal = build_tabela_saldo_mensal_filial(df_filtrado)

if resultado_mensal and not resultado_mensal[0].empty:
    df_saldo_mensal, meses_ord_fil = resultado_mensal

    # Formatar valores
    df_saldo_fmt = df_saldo_mensal.copy().astype(object)
    for col in df_saldo_mensal.columns:
        for idx in df_saldo_mensal.index:
            val = df_saldo_mensal.loc[idx, col]
            if val > 0:
                df_saldo_fmt.loc[idx, col] = f"✅ {formatar_reais(val)}"
            elif val < 0:
                df_saldo_fmt.loc[idx, col] = f"⚠️ {formatar_reais(val)}"
            else:
                df_saldo_fmt.loc[idx, col] = "—"


    # Estilo linha total geral
    def estilo_linha(row):
        if row.name == "TOTAL GERAL":
            return ["background-color: #1e3a5f; font-weight: bold; color: #60a5fa"] * len(row)
        return [""] * len(row)


    st.dataframe(
        df_saldo_fmt.style.apply(estilo_linha, axis=1),
        use_container_width=True,
        height=min(100 + len(df_saldo_mensal) * 40, 500)
    )

    _, btn_col, _ = st.columns(3)
    #with btn_col:
   #     if st.button("📥 Exportar Saldo Mensal (CSV)", use_container_width=True):
   #         csv = df_saldo_mensal.to_csv()
   #         st.download_button(
   #             label="Clique para baixar",
   #             data=csv,
   #             file_name=f"saldo_filial_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
   #             mime="text/csv"
   #        )
else:
    st.info("Sem dados suficientes para a tabela mensal")
st.markdown("---")
st.subheader("📊 DRE — Demonstrativo de Resultado")

opcoes_dre = st.columns([1, 1, 2])
with opcoes_dre[0]:
    mostrar_pct = st.checkbox("% sobre Receita Líquida", value=True)
with opcoes_dre[1]:
    mostrar_var = st.checkbox("Variação vs mês anterior", value=True)

resultado_dre = build_dre(df_filtrado)

if resultado_dre and not resultado_dre[0].empty:
    df_dre, meses_ord = resultado_dre

    linhas_destaque = ["3. = Receita Líquida", "8. = EBITDA"]

    # Montar df expandido com colunas separadas por mês
    colunas_finais = {"OPERAÇÃO": []}
    for i, mes in enumerate(meses_ord):
        colunas_finais[mes] = []
        if mostrar_pct:
            colunas_finais[f"% {mes}"] = []
        if mostrar_var and i > 0:
            colunas_finais[f"∆ {mes}"] = []
    colunas_finais["TOTAL"] = []
    if mostrar_pct:
        colunas_finais["% TOTAL"] = []

    rec_liq_row = df_dre.loc["3. = Receita Líquida"] if "3. = Receita Líquida" in df_dre.index else None

    for linha in df_dre.index:
        colunas_finais["OPERAÇÃO"].append(linha)

        for i, mes in enumerate(meses_ord):
            val = df_dre.loc[linha, mes]
            val_fmt = formatar_reais(val) if val != 0 else "—"
            colunas_finais[mes].append(val_fmt)

            if mostrar_pct:
                base = rec_liq_row[mes] if rec_liq_row is not None and rec_liq_row[mes] != 0 else None
                pct_fmt = f"{(val / base * 100):.1f}%" if base else "—"
                colunas_finais[f"% {mes}"].append(pct_fmt)

            if mostrar_var and i > 0:
                val_ant = df_dre.loc[linha, meses_ord[i - 1]]
                if val_ant != 0:
                    var = ((val - val_ant) / abs(val_ant)) * 100
                    sinal = "+" if var > 0 else ""
                    colunas_finais[f"∆ {mes}"].append(f"{sinal}{var:.1f}%")
                else:
                    colunas_finais[f"∆ {mes}"].append("—")

        # Total
        total = df_dre.loc[linha, "TOTAL"]
        colunas_finais["TOTAL"].append(formatar_reais(total) if total != 0 else "—")

        if mostrar_pct:
            base_total = rec_liq_row["TOTAL"] if rec_liq_row is not None and rec_liq_row["TOTAL"] != 0 else None
            pct_total = f"{(total / base_total * 100):.1f}%" if base_total else "—"
            colunas_finais["% TOTAL"].append(pct_total)

    df_dre_fmt = pd.DataFrame(colunas_finais).set_index("OPERAÇÃO")


    # Estilo
    def estilo_dre(row):
        if row.name in linhas_destaque:
            return ["background-color: #1e3a5f; font-weight: bold; color: #60a5fa"] * len(row)
        return [""] * len(row)


    st.dataframe(
        df_dre_fmt.style.apply(estilo_dre, axis=1),
        use_container_width=True,
        height=350
    )

    _, btn_dre, _ = st.columns(3)
  #  with btn_dre:
  #     if st.button("📥 Exportar DRE (CSV)", use_container_width=True):
  #          csv_dre = df_dre.to_csv()
  #          st.download_button(
  #              label="Clique para baixar",
  #              data=csv_dre,
  #              file_name=f"dre_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
  #              mime="text/csv"
  #         )
else:
    st.info("Sem dados suficientes para montar o DRE")
# ==========================================
# TABELA INADIMPLENTES
# ==========================================

st.markdown("---")
st.subheader("⚠️ Títulos em Aberto (Inadimplência)")

if not inadimplentes.empty:
    cols_inad = ["DATA_EMISSAO", "DATA_PAGAMENTO", "DESCRICAO", "PLANO_DE_CONTAS", "NOME_CENTRO_CUSTO", "VALOR_ABS"]
    cols_inad = [c for c in cols_inad if c in inadimplentes.columns]
    df_inad = inadimplentes[cols_inad].copy()

    for col_dt in ["DATA_EMISSAO", "DATA_PAGAMENTO"]:
        if col_dt in df_inad.columns:
            df_inad[col_dt] = df_inad[col_dt].dt.strftime("%d/%m/%Y")

    if "VALOR_ABS" in df_inad.columns:
        df_inad["VALOR_ABS"] = df_inad["VALOR_ABS"].apply(formatar_reais)

    df_inad = df_inad.rename(columns={
        "DATA_EMISSAO": "Emissão", "DATA_PAGAMENTO": "Vencimento",
        "DESCRICAO": "Descrição", "PLANO_DE_CONTAS": "Plano de Contas",
        "NOME_CENTRO_CUSTO": "Centro Custo", "VALOR_ABS": "Valor"
    })
    st.dataframe(df_inad, use_container_width=True, height=300, hide_index=True)
else:
    st.success("✅ Nenhum título em aberto vencido")

# ==========================================
# TABELA DETALHADA
# ==========================================

st.markdown("---")
st.subheader("📋 Detalhamento")

t_col1, t_col2 = st.columns([3, 1])
with t_col1:
    busca = st.text_input("🔍 Buscar na tabela", placeholder="Filtrar qualquer coluna...")

if not df_filtrado.empty:
    cols_tabela = ["DATA_EMISSAO", "DATA_PAGAMENTO", "TIPO_FLUXO", "STATUS",
                   "DESCRICAO", "PLANO_DE_CONTAS", "FORMA_DE_PAGAMENTO",
                   "NOME_CENTRO_CUSTO", "NOME_FILIAL", "VALOR"]
    cols_tabela = [c for c in cols_tabela if c in df_filtrado.columns]
    df_tabela = df_filtrado[cols_tabela].copy()

    for col_dt in ["DATA_EMISSAO", "DATA_PAGAMENTO"]:
        if col_dt in df_tabela.columns:
            df_tabela[col_dt] = pd.to_datetime(df_tabela[col_dt], errors="coerce").dt.strftime("%d/%m/%Y")

    if "VALOR" in df_tabela.columns:
        df_tabela["VALOR"] = df_tabela["VALOR"].apply(formatar_reais)

    df_tabela = df_tabela.rename(columns={
        "DATA_EMISSAO": "Emissão", "DATA_PAGAMENTO": "Pagamento",
        "TIPO_FLUXO": "Tipo", "STATUS": "Status", "DESCRICAO": "Descrição",
        "PLANO_DE_CONTAS": "Plano de Contas", "FORMA_DE_PAGAMENTO": "Forma Pgto",
        "NOME_CENTRO_CUSTO": "Centro Custo", "NOME_FILIAL": "Filial", "VALOR": "Valor"
    })

    if busca:
        mask = df_tabela.apply(
            lambda col: col.astype(str).str.contains(busca, case=False, na=False)
        ).any(axis=1)
        df_tabela = df_tabela[mask]

    # Totalizador
    linha_total = {col: "" for col in df_tabela.columns}
    linha_total["Emissão"] = "TOTAL"
    linha_total["Valor"] = formatar_reais(df_filtrado["VALOR"].sum())
    df_tabela = pd.concat([df_tabela, pd.DataFrame([linha_total])], ignore_index=True)

    st.dataframe(df_tabela, use_container_width=True, height=400, hide_index=True)

    _, btn_col, _ = st.columns(3)
   # with btn_col:
   #     if st.button("📥 Exportar CSV", use_container_width=True):
   #         csv = df_filtrado.to_csv(index=False)
   #         st.download_button(
   #             label="Clique para baixar",
   #             data=csv,
   #             file_name=f"fluxo_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
   #             mime="text/csv"
   #         )
else:
    st.warning("⚠️ Nenhum dado encontrado com os filtros selecionados.")

# ==========================================
# RODAPÉ
# ==========================================

st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #666; font-size: 12px;'>"
    "💰 Fluxo de Caixa | Desenvolvido com Streamlit"
    "</div>",
    unsafe_allow_html=True
)
