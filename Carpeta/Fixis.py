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
@st.cache_data
def cobertura_tabla_y_grafica(df):
    TOTALES = {
        "Coahuila (Saltillo)":85,"Coahuila (Torreón)":54,"Morelos":12,"México":393,
        "Nuevo León":751,"Puebla":22,"Quintana Roo":103,"Tamaulipas (Matamoros)":59,
        "Tamaulipas (Reynosa)":168,"Baja California (Tijuana)":86,"Baja California (Mexicali)":61,
        "Baja California (Ensenada)":24,"Jalisco":181,"Yucatán":30,"Sonora (Hermosillo)":21,
    }
    ART = "ARTICULO" if "ARTICULO" in df.columns else "Artículo"
    PLZ = "PLAZA" if "PLAZA" in df.columns else "Plaza"
    TND = "NUM_TIENDA" if "NUM_TIENDA" in df.columns else ("TIENDA" if "TIENDA" in df.columns else "Tienda")
    MRD = "MERCADO" if "MERCADO" in df.columns else ("Mercado" if "Mercado" in df.columns else None)

    g = (df[[ART,PLZ,TND]].astype(str).groupby([ART,PLZ])[TND].nunique().reset_index(name="Tiendas_con_art"))
    tot = pd.DataFrame({PLZ:list(TOTALES.keys()), "Tiendas_totales":list(TOTALES.values())})
    base = g.merge(tot, on=PLZ, how="left")
    if base["Tiendas_totales"].isna().any():
        obs = df.groupby(PLZ)[TND].nunique().rename("obs").reset_index()
        base = base.merge(obs, on=PLZ, how="left")
        base["Tiendas_totales"] = base["Tiendas_totales"].fillna(base["obs"])
    base["Cobertura %"] = (base["Tiendas_con_art"] / base["Tiendas_totales"] * 100).clip(0,100)

    pivot = base.pivot(index=ART, columns=PLZ, values="Cobertura %")  # <- DataFrame (sí se cachea)

    if MRD:
        m = df[[PLZ,MRD]].drop_duplicates()
        b2 = base.merge(m, on=PLZ, how="left")
        res = b2.groupby(MRD)["Cobertura %"].mean().reset_index(); xlab = MRD
    else:
        res = base.groupby(PLZ)["Cobertura %"].mean().reset_index(); xlab = PLZ

    fig = px.bar(res.sort_values("Cobertura %", ascending=False), x=xlab, y="Cobertura %",
                 color="Cobertura %", color_continuous_scale=["#EF9A9A","#FFF59D","#B9F6CA"],
                 range_color=(0,100), title="Cobertura promedio por " + xlab)
    fig.update_layout(showlegend=False, yaxis_title="Cobertura (%)", xaxis_tickangle=-30)

    return pivot, fig

pivot, fig = cobertura_tabla_y_grafica(df_venta_perdida_filtrada)

def color(v):
    if pd.isna(v): return ""
    if v >= 95: return "background-color:#B9F6CA; text-align:center"
    if v >= 85: return "background-color:#FFF59D; text-align:center"
    return "background-color:#EF9A9A; text-align:center"

st.dataframe(pivot.style.format("{:.0f}%").applymap(color), use_container_width=True)
st.plotly_chart(fig, use_container_width=True)
