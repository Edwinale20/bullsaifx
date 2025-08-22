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
def grafico_cobertura(df_venta_perdida_filtrada, tiendas_por_plaza: dict | None = None, orden_columnas: list[str] | None = None):
    # -------- Config interna: totales por plaza (edítalo si quieres aquí mismo) --------
    default_totales = {
        "Coahuila (Saltillo)":150, "Coahuila (Torreón)":95, "Morelos":120, "México":800,
        "Nuevo León":650, "Puebla":200, "Quintana Roo":160, "Tamaulipas (Matamoros)":90,
        "Tamaulipas (Reynosa)":130, "Baja California (Tijuana)":300, "Baja California (Mexicali)":110,
        "Baja California (Ensenada)":70, "Jalisco":400, "Yucatán":180, "Sonora (Hermosillo)":140
    }
    totales_dict = tiendas_por_plaza or default_totales

    # -------- Validaciones mínimas --------
    tienda_col = "NUM_TIENDA" if "NUM_TIENDA" in df_venta_perdida_filtrada.columns else ("TIENDA" if "TIENDA" in df_venta_perdida_filtrada.columns else None)
    need = {"PLAZA","ARTICULO", tienda_col}
    if None in need or not need.issubset(df_venta_perdida_filtrada.columns):
        st.error("Se requieren columnas: PLAZA, ARTICULO y NUM_TIENDA/TIENDA.")
        return

    df = df_venta_perdida_filtrada[["PLAZA","ARTICULO",tienda_col]].astype(str).copy()

    # -------- Numerador: tiendas únicas con el artículo por plaza/artículo --------
    num = df.groupby(["PLAZA","ARTICULO"])[tienda_col].nunique().reset_index(name="TIENDAS_CON_ART")

    # -------- Denominador: totales por plaza --------
    tot = pd.DataFrame({"PLAZA": list(totales_dict.keys()), "TIENDAS_TOTALES": list(totales_dict.values())})
    base = num.merge(tot, on="PLAZA", how="left")

    # Fallback: si alguna plaza quedó sin total, usa el máximo de tiendas únicas observadas en esa plaza
    faltantes = base["PLAZA"][base["TIENDAS_TOTALES"].isna()].unique()
    if len(faltantes):
        obs = df.groupby("PLAZA")[tienda_col].nunique().rename("OBS_TOTALES").reset_index()
        base = base.merge(obs, on="PLAZA", how="left")
        base["TIENDAS_TOTALES"] = base["TIENDAS_TOTALES"].fillna(base["OBS_TOTALES"])
        base = base.drop(columns=["OBS_TOTALES"])

    # -------- % Cobertura --------
    base["COBERTURA"] = (base["TIENDAS_CON_ART"] / base["TIENDAS_TOTALES"] * 100).clip(0,100)

    # -------- Pivot para heatmap --------
    pv = base.pivot_table(index="ARTICULO", columns="PLAZA", values="COBERTURA", aggfunc="mean")
    if orden_columnas:
        pv = pv.reindex(columns=[c for c in orden_columnas if c in pv.columns])

    # Texto por celda
    text = pv.applymap(lambda v: "" if pd.isna(v) else f"{v:.0f}%").values
    z = (pv/100.0).values  # 0–1

    # Umbrales fijos (rojo <85, amarillo 85–94, verde ≥95) y look de “cuadritos”
    colorscale = [[0.00,"#EF9A9A"],[0.85,"#EF9A9A"],[0.85,"#FFF59D"],[0.95,"#FFF59D"],[0.95,"#B9F6CA"],[1.00,"#B9F6CA"]]
    fig = go.Figure(go.Heatmap(
        z=z, x=pv.columns.tolist(), y=pv.index.tolist(),
        zmin=0, zmax=1, colorscale=colorscale, showscale=False,
        text=text, texttemplate="%{text}", textfont=dict(size=11),
        hovertemplate="<b>%{y}</b><br>%{x}<br>%{text}<extra></extra>",
        xgap=1, ygap=1
    ))
    fig.update_layout(
        title="📊 Cobertura por Artículo y Plaza",
        xaxis_title="Plaza", yaxis_title="Artículo", yaxis=dict(autorange="reversed"),
        margin=dict(l=10,r=10,t=50,b=10), height=650, plot_bgcolor="white", paper_bgcolor="white"
    )
    return fig

fig = grafico_cobertura(df_venta_perdida_filtrada)  # todo interno; edita los totales dentro si quieres
st.plotly_chart(fig, use_container_width=True)
