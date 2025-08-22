import pandas as pd
import glob
import os
import streamlit as st
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import subprocess
import zipfile
import io




st.set_page_config(page_title="Reporte de Abasto Comercial", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Abasto comercial 🏪")
st.markdown("✅ Arrastra aquí tu archivo de inventarios")
st.markdown("✅ Esta app analiza rápidamente las coberturas de todo el catálogo de tu categoría")
st.markdown("✅ Puedes hacer preguntas a la IA y ayudarte a identificar los productos en desabasto y con oportunidades. " \
"Además de limpiar aquellos artículos con poco UPTD, con el fin de seguir el proceso de plan de choque")




# --- TU FUNCIÓN: Déjala idéntica ---
@st.cache_data
def Inventarios(archivo_zip):
    if archivo_zip is None:
        return None

    with zipfile.ZipFile(io.BytesIO(archivo_zip.getvalue())) as z:
        csvs = [f for f in z.namelist() if f.lower().endswith(".csv")]
        if not csvs:
            st.error("El ZIP no contiene CSV.")
            st.stop()
        with z.open(csvs[0]) as f:
            df = pd.read_csv(f, encoding='ISO-8859-1')

    combined_df = df.copy()

    cols_drop = ['NOMBRE_TIENDA','VALOR_VENTA_4SEM','VALOR_COMPRAS_4SEM','GMROI']
    combined_df = combined_df.drop(columns=[c for c in cols_drop if c in combined_df.columns], errors='ignore')

    if 'PLAZA' in combined_df.columns:
        combined_df['PLAZA'] = combined_df['PLAZA'].astype(str).str[:3]
    if 'MERCADO' in combined_df.columns:
        combined_df['MERCADO'] = combined_df['MERCADO'].astype(str).str[1:]
    if 'VALOR_INVENTARIO' in combined_df.columns:
        combined_df['VENTA_PERDIDA_PESOS'] = combined_df['VALOR_INVENTARIO'].round(0).astype('int64')

    rename_map = {'UDS_INVENTARIO': 'Unidades', 'VALOR_INVENTARIO': 'Valor Inventario', 'VENTA_PTD': 'Venta PTD'}
    combined_df = combined_df.rename(columns={k: v for k, v in rename_map.items() if k in combined_df.columns})

    map_plaza = {
        "100":"Tamaulipas (Reynosa)","110":"Tamaulipas (Matamoros)","200":"México","300":"Jalisco",
        "400":"Coahuila (Saltillo)","410":"Coahuila (Torreón)","500":"Nuevo León",
        "600":"Baja California (Tijuana)","610":"Baja California (Mexicali)","620":"Baja California (Ensenada)",
        "650":"Sonora (Hermosillo)","700":"Puebla","720":"Morelos","800":"Yucatán","890":"Quintana Roo",
    }
    if 'PLAZA' in combined_df.columns:
        combined_df['PLAZA'] = combined_df['PLAZA'].map(map_plaza).fillna(combined_df['PLAZA'])

    map_division = {
        "Tamaulipas (Reynosa)":"Coahuila - Tamaulipas","Tamaulipas (Matamoros)":"Coahuila - Tamaulipas",
        "México":"México - Península","Jalisco":"Pacífico","Coahuila (Saltillo)":"Coahuila - Tamaulipas",
        "Coahuila (Torreón)":"Coahuila - Tamaulipas","Nuevo León":"Nuevo León",
        "Baja California (Tijuana)":"Pacífico","Baja California (Mexicali)":"Pacífico","Baja California (Ensenada)":"Pacífico",
        "Sonora (Hermosillo)":"Pacífico","Puebla":"México - Península","Morelos":"México - Península",
        "Yucatán":"México - Península","Quintana Roo":"México - Península",
    }
    if 'PLAZA' in combined_df.columns:
        combined_df['Division'] = combined_df['PLAZA'].map(map_division).fillna(combined_df.get('Division', pd.Series(index=combined_df.index)))

    return combined_df

# --- AQUÍ defines el uploader y llamas a tu función ---
st.title("Inventarios")
archivo_zip = st.file_uploader("Sube tu .zip con un CSV adentro", type=["zip"])

INV = Inventarios(archivo_zip)  # <- como querías

if INV is None:
    st.stop()

st.success("CSV cargado y procesado.")


# Paso 1: Crear una lista de opciones para el filtro, incluyendo "Ninguno"

opciones_division = ['Ninguno'] + list(INV['Division'].unique())
division = st.sidebar.selectbox('Seleccione la División', opciones_division)

opciones_plaza = ['Ninguno'] + list(INV['PLAZA'].unique())
plaza = st.sidebar.selectbox('Seleccione la Plaza', opciones_plaza)

opciones_mercado = ['Ninguno'] + list(INV['MERCADO'].unique())
mercado = st.sidebar.selectbox('Seleccione el Mercado', opciones_mercado)

opciones_categoria = ['Ninguno'] + list(INV['SUBCATEGORIA'].unique())
categoria = st.sidebar.selectbox('Seleccione la Categoria', opciones_categoria)



# Filtrar por Proveedor
if division == 'Ninguno':
    df_venta_perdida_filtrada = INV
else:
    df_venta_perdida_filtrada = INV[INV['Division'] == division]

# Filtrar por Plaza
if plaza != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['PLAZA'] == plaza]

# Filtrar por Mercado
if mercado != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['MERCADO'] == mercado]

# Filtrar por Categoria
if categoria != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['SUBCATEGORIA'] == categoria]


@st.cache_data
def graficar_top_uptd(df_venta_perdida_filtrada):
    # Requisitos mínimos
    req = {"ARTICULO", "PLAZA", "UPTD"}
    if not req.issubset(df_venta_perdida_filtrada.columns):
        st.error(f"Faltan columnas: {sorted(req - set(df_venta_perdida_filtrada.columns))}")
        return None

    df = df_venta_perdida_filtrada.copy()
    df["ARTICULO"] = df["ARTICULO"].astype(str)
    df["PLAZA"] = df["PLAZA"].astype(str)
    df["UPTD"] = pd.to_numeric(df["UPTD"], errors="coerce")
    df = df.dropna(subset=["UPTD"])

    # Top 10 por UPTD promedio global (artículo)
    ranking = (
        df.groupby("ARTICULO", as_index=False)["UPTD"].mean()
          .sort_values("UPTD", ascending=False)
          .head(10)
    )
    top_art = ranking["ARTICULO"].tolist()

    # Agregar por PLAZA y ARTÍCULO (UPTD promedio) y ordenar según ranking
    df_top = (
        df[df["ARTICULO"].isin(top_art)]
        .groupby(["PLAZA", "ARTICULO"], as_index=False)["UPTD"].mean()
    )
    df_top["ARTICULO"] = pd.Categorical(df_top["ARTICULO"], categories=top_art, ordered=True)

    # Gráfica bonita (barras agrupadas por PLAZA)
    fig = px.bar(
        df_top, x="ARTICULO", y="UPTD", color="PLAZA", barmode="group",
        text="UPTD", title="🔝 Top 10 artículos por UPTD (promedio) • por Plaza",
        template="plotly_white", hover_data={"UPTD":":.2f"}
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        xaxis_title="Artículo", yaxis_title="UPTD promedio",
        margin=dict(l=10,r=10,t=60,b=10), height=520, legend_title_text="PLAZA"
    )
    fig.update_xaxes(tickangle=-25)

    return fig

# Uso:
fig_top_uptd = graficar_top_uptd(df_venta_perdida_filtrada)
if fig_top_uptd:
    st.plotly_chart(fig_top_uptd, use_container_width=True)


@st.cache_data
def calcular_cobertura_tabla(df, totales_por_plaza: dict):
    """
    Calcula la cobertura y devuelve una tabla tipo Excel estilizada.
    Cobertura % = tiendas únicas con el artículo / tiendas totales de la plaza * 100
    """
    # Columnas esperadas (toma la que exista)
    articulo = "Artículo" if "Artículo" in df.columns else "ARTICULO"
    plaza    = "Plaza"    if "Plaza"    in df.columns else "PLAZA"
    tienda   = "NUM_TIENDA" if "NUM_TIENDA" in df.columns else ("TIENDA" if "TIENDA" in df.columns else "Tienda")

    # Tiendas con el artículo por (Artículo, Plaza)
    g = (df[[articulo, plaza, tienda]].astype(str)
           .groupby([articulo, plaza])[tienda].nunique()
           .reset_index(name="Tiendas_con_art"))

    # Totales por plaza
    tot = pd.DataFrame({plaza:list(totales_por_plaza.keys()), "Tiendas_totales":list(totales_por_plaza.values())})
    base = g.merge(tot, on=plaza, how="left")

    # % Cobertura
    base["Cobertura %"] = (base["Tiendas_con_art"] / base["Tiendas_totales"] * 100).round(0).clip(0,100)

    # Pivot: filas=Artículo, columnas=Plaza
    pivot = base.pivot(index=articulo, columns=plaza, values="Cobertura %")

    # Semáforo
    def color(val):
        if pd.isna(val): return ""
        if val >= 95:    return "background-color: #B9F6CA; text-align:center"
        if val >= 85:    return "background-color: #FFF59D; text-align:center"
        return "background-color: #EF9A9A; text-align:center"
    return pivot.style.format("{:.0f}%").applymap(color)


def grafico_cobertura_mercado(df, totales_por_plaza: dict):
    """
    Gráfica de barras: % cobertura por Mercado (si no existe, por Plaza).
    """
    articulo = "Artículo" if "Artículo" in df.columns else "ARTICULO"
    plaza    = "Plaza"    if "Plaza"    in df.columns else "PLAZA"
    tienda   = "NUM_TIENDA" if "NUM_TIENDA" in df.columns else ("TIENDA" if "TIENDA" in df.columns else "Tienda")
    mercado  = "Mercado" if "Mercado" in df.columns else ("MERCADO" if "MERCADO" in df.columns else None)

    g = (df[[plaza, articulo, tienda] + ([mercado] if mercado else [])].astype(str)
           .groupby([plaza, articulo])[tienda].nunique()
           .reset_index(name="Tiendas_con_art"))
    tot = pd.DataFrame({plaza:list(totales_por_plaza.keys()), "Tiendas_totales":list(totales_por_plaza.values())})
    base = g.merge(tot, on=plaza, how="left")
    base["Cobertura %"] = (base["Tiendas_con_art"] / base["Tiendas_totales"] * 100).clip(0,100)

    if mercado:
        m = df[[plaza, mercado]].drop_duplicates()
        base = base.merge(m, on=plaza, how="left")
        res = base.groupby(mercado)["Cobertura %"].mean().reset_index()
        x = mercado
    else:
        res = base.groupby(plaza)["Cobertura %"].mean().reset_index()
        x = plaza

    fig = px.bar(res.sort_values("Cobertura %", ascending=False), x=x, y="Cobertura %",
                 color="Cobertura %", color_continuous_scale=["#EF9A9A","#FFF59D","#B9F6CA"],
                 range_color=(0,100), title="Cobertura promedio por " + x)
    fig.update_layout(showlegend=False, yaxis_title="Cobertura (%)", xaxis_tickangle=-30)
    return fig


styled = calcular_cobertura_tabla(df_venta_perdida_filtrada, totales)
st.dataframe(styled, use_container_width=True)
