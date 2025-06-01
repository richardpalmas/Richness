import streamlit as st
from datetime import date
import pandas as pd

def filtro_data(df, key_prefix="default"):
    """
    Componente reutilizável para filtro de data em dataframes.

    Parameters:
    - df: DataFrame pandas com coluna 'Data' em formato datetime
    - key_prefix: Prefixo para chaves do streamlit, necessário quando o componente é usado várias vezes na mesma página

    Returns:
    - start_date: Data de início selecionada
    - end_date: Data de fim selecionada
    """
    if "Data" not in df.columns or df.empty:
        return date.today(), date.today()

    # Converter para datetime se ainda não estiver
    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"])

    min_date = df["Data"].min().date()
    max_date = df["Data"].max().date()

    selected_period = st.sidebar.date_input(
        "Selecione o Período",
        value=(min_date, max_date),
        key=f"{key_prefix}_date_filter"
    )

    if isinstance(selected_period, tuple):
        if len(selected_period) == 2:
            start_date, end_date = selected_period
        else:
            start_date = end_date = selected_period[0]
    else:
        start_date = end_date = selected_period

    return start_date, end_date

def filtro_categorias(df, titulo="Filtrar por Categorias", key_prefix="default"):
    """
    Componente reutilizável para filtro de categorias em dataframes.

    Parameters:
    - df: DataFrame pandas com coluna 'Categoria'
    - titulo: Título do filtro
    - key_prefix: Prefixo para chaves do streamlit

    Returns:
    - categorias_selecionadas: Lista de categorias selecionadas
    """
    if "Categoria" not in df.columns or df.empty:
        return []

    categorias = sorted(df["Categoria"].dropna().unique().tolist())
    categorias_selecionadas = st.sidebar.multiselect(
        titulo,
        categorias,
        default=categorias,
        key=f"{key_prefix}_cat_filter"
    )

    return categorias_selecionadas

def filtro_cartoes(df, key_prefix="default"):
    """
    Componente reutilizável para filtro de cartões em dataframes.

    Parameters:
    - df: DataFrame pandas com coluna 'Cartão'
    - key_prefix: Prefixo para chaves do streamlit

    Returns:
    - cartoes_selecionados: Lista de cartões selecionados
    """
    if "Cartão" not in df.columns or df.empty:
        return []

    cartoes = sorted(df["Cartão"].dropna().unique().tolist())
    cartoes_selecionados = st.sidebar.multiselect(
        "Filtrar por Cartão",
        cartoes,
        default=cartoes,
        key=f"{key_prefix}_card_filter"
    )

    return cartoes_selecionados

def aplicar_filtros(df, start_date, end_date, categorias_selecionadas=None, cartoes_selecionados=None):
    """
    Aplica filtros de data e categoria a um dataframe.

    Parameters:
    - df: DataFrame pandas com coluna 'Data' em formato datetime
    - start_date: Data de início para filtragem
    - end_date: Data de fim para filtragem
    - categorias_selecionadas: Lista de categorias para filtrar (opcional)
    - cartoes_selecionados: Lista de cartões para filtrar (opcional)

    Returns:
    - df_filtrado: DataFrame filtrado
    """
    # Converter para datetime se ainda não estiver
    if not pd.api.types.is_datetime64_any_dtype(df["Data"]):
        df["Data"] = pd.to_datetime(df["Data"])

    # Filtro por data
    mask = (df["Data"].dt.date >= start_date) & (df["Data"].dt.date <= end_date)
    df_filtrado = df[mask]

    # Filtro por categoria
    if categorias_selecionadas:
        df_filtrado = df_filtrado[df_filtrado["Categoria"].isin(categorias_selecionadas)]

    # Filtro por cartão
    if cartoes_selecionados and "Cartão" in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado["Cartão"].isin(cartoes_selecionados)]

    return df_filtrado
