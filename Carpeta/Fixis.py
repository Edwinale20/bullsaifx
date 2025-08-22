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

#----------------------------------------------------------------------------------------

   
st.set_page_config(page_title="Reporte de Abasto y Clientes Comercial", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Abasto y Clientes comercial 🏪")
st.markdown("✅ Arrastra aquí tu archivo de inventarios")
st.markdown("✅ Esta app analiza en menos de 30 segundos las coberturas de todo el catálogo de tu categoría. Te ahorramos hasta 5 horas de trabajo semanales!")
st.markdown("✅ Puedes identificar los productos en desabasto, y aquellos con oportunidades." "Además de limpiar aquellos artículos con pocas UPTD, con el fin de seguir el plan APT")
kpi_top = st.container()


#----------------------------------------------------------------------------------------   

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
        "600":"Baja California (Tijuana)","610":"Baja California (Ensenada)","620":"Baja California (Mexicali)",
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

#---------------------------------------------------------------------------------------- AQUÍ defines el uploader y llamas a tu función ---
# Placeholder
uploader_placeholder = st.empty()

# El uploader vive dentro del placeholder
archivo_zip = uploader_placeholder.file_uploader("📤 Sube tu archivo de Inventarios (312 de BI)", type=["zip"])

if archivo_zip is not None:
    # Quitar uploader
    uploader_placeholder.empty()
    
#----------------------------------------------------------------------------------------    



INV = Inventarios(archivo_zip)  # <- como querías

if INV is None:
    st.stop()

st.success("✅Los inventarios de tu categoría fueron cargados con éxito.")

#----------------------------------------------------------------------------------------


st.sidebar.image("https://raw.githubusercontent.com/Edwinale20/bullsaifx/main/Carpeta/el-logo.png", width=170)
st.sidebar.title("Filtros 🔠")
# Paso 1: Crear una lista de opciones para el filtro, incluyendo "Ninguno"

opciones_division = ['Ninguno'] + list(INV['Division'].unique())
division = st.sidebar.selectbox('Seleccione la División', opciones_division)

opciones_plaza = ['Ninguno'] + list(INV['PLAZA'].unique())
plaza = st.sidebar.selectbox('Seleccione la Plaza', opciones_plaza)

opciones_mercado = ['Ninguno'] + list(INV['MERCADO'].unique())
mercado = st.sidebar.selectbox('Seleccione el Mercado', opciones_mercado)

opciones_categoria = ['Ninguno'] + list(INV['SUBCATEGORIA'].unique())
categoria = st.sidebar.selectbox('Seleccione la Categoria', opciones_categoria)

opciones_proveedor = ['Ninguno'] + list(INV['PROVEEDOR'].unique())
proveedor = st.sidebar.selectbox('Seleccione el Proveedor', opciones_proveedor)

articulo_busqueda = st.sidebar.text_input("Buscar Artículo:")


umbral_uptd = st.sidebar.slider(
    'Filtrar artículos por rango de UPTD:',
    min_value=0,
    max_value=int(INV['UPTD'].max()),
    value=(0, int(INV['UPTD'].max())),  # rango inicial
    step=1
)


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

# Filtrar por Proveedor
if proveedor != 'Ninguno':
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[df_venta_perdida_filtrada['PROVEEDOR'] == proveedor]

if articulo_busqueda:
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[
        df_venta_perdida_filtrada['ARTICULO'].str.contains(
            articulo_busqueda, case=False, na=False
        )
    ]


if articulo_busqueda:
    df_venta_perdida_filtrada = df_venta_perdida_filtrada[
        df_venta_perdida_filtrada['ARTICULO'].str.contains(articulo_busqueda, case=False, na=False)]
    

#----------------------------------------------------------------------------------------




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

#----------------------------------------------------------------------------------------
@st.cache_data
def cobertura_tabla(df):
    TOTALES = {
        "Coahuila (Saltillo)":85,"Coahuila (Torreón)":54,"Morelos":12,"México":390,
        "Nuevo León":751,"Puebla":22,"Quintana Roo":79,"Tamaulipas (Matamoros)":59,
        "Tamaulipas (Reynosa)":168,"Baja California (Tijuana)":86,"Baja California (Mexicali)":61,
        "Baja California (Ensenada)":24,"Jalisco":181,"Yucatán":54,"Sonora (Hermosillo)":21,
    }
    ART = "ARTICULO" if "ARTICULO" in df.columns else "Artículo"
    PLZ = "PLAZA" if "PLAZA" in df.columns else "Plaza"
    TND = "NUM_TIENDA" if "NUM_TIENDA" in df.columns else ("TIENDA" if "TIENDA" in df.columns else "Tienda")

    g = (df[[ART,PLZ,TND]].astype(str)
         .groupby([ART,PLZ])[TND]
         .nunique()
         .reset_index(name="Tiendas_con_art"))

    tot = pd.DataFrame({PLZ:list(TOTALES.keys()), "Tiendas_totales":list(TOTALES.values())})
    base = g.merge(tot, on=PLZ, how="left")

    if base["Tiendas_totales"].isna().any():
        obs = df.groupby(PLZ)[TND].nunique().rename("obs").reset_index()
        base = base.merge(obs, on=PLZ, how="left")
        base["Tiendas_totales"] = base["Tiendas_totales"].fillna(base["obs"])

    base["Cobertura %"] = (base["Tiendas_con_art"] / base["Tiendas_totales"] * 100).clip(0,100)

    pivot = base.pivot(index=ART, columns=PLZ, values="Cobertura %")

    # Guardar versión numérica para estilo
    numeric = pivot.copy()

    # Formato porcentaje bonito
    pivot = pivot.round(0).astype("Int64").astype(str) + "%"
    pivot = pivot.replace({"<NA>%": "Sin abasto"})

    return pivot, numeric

# === USO ===
# === USO CORRECTO ===
pivot, numeric = cobertura_tabla(df_venta_perdida_filtrada)

# Función para aplicar colores
def color_sem(serie):
    colors = []
    for v in serie:
        if pd.isna(v):  # Sin abasto
            colors.append("background-color: lightgray; color: black;")
        elif v < 40:
            colors.append("background-color: #ff4d4d; color: white;")  # Rojo
        elif v < 70:
            colors.append("background-color: #ffd633; color: black;")  # Amarillo
        else:
            colors.append("background-color: #5cd65c; color: black;")  # Verde
    return colors

# Estilo sobre numeric
styled = numeric.style.apply(color_sem, axis=0).format("{:.0f}%", na_rep="Sin abasto")

# 👇 Mostrar con colores en Streamlit
st.markdown(styled.to_html(), unsafe_allow_html=True)
# === 1) Cobertura por artículo (global) ======================================
def cobertura_por_articulo(df, totales_por_plaza: dict, umbral_inv: int = 3):
    pick = lambda names: next((c for c in names if c in df.columns), None)
    ART = pick(["ARTICULO","Artículo","Articulo"])
    PLZ = pick(["PLAZA","Plaza"])
    TND = pick(["NUM_TIENDA","TIENDA","Tienda"])
    INV = pick(["Unidades Inventario","UDS_INVENTARIO","Unidades","INVENTARIO_UNIDADES"])

    d = df[[ART,PLZ,TND] + ([INV] if INV else [])].copy().astype({PLZ:str, TND:str, ART:str})
    d["_pres"] = (pd.to_numeric(d[INV], errors="coerce").fillna(0) > umbral_inv) if INV else True
    pres = d.groupby([ART,PLZ,TND], as_index=False)["_pres"].max()
    num = pres.groupby([ART,PLZ])["_pres"].sum().reset_index(name="Tiendas_con_art")

    tot = pd.DataFrame({PLZ:list(totales_por_plaza.keys()), "Tiendas_totales":list(totales_por_plaza.values())})
    base = num.merge(tot, on=PLZ, how="left")

    # Fallback si falta total para alguna plaza → usa tiendas observadas
    if base["Tiendas_totales"].isna().any():
        obs = pres.groupby(PLZ)[TND].nunique().rename("obs").reset_index()
        base = base.merge(obs, on=PLZ, how="left")
        base["Tiendas_totales"] = base["Tiendas_totales"].fillna(base["obs"])

    # Cobertura GLOBAL del artículo (sumando plazas)
    art = (base.groupby(ART)
           .agg(Tiendas_con_art=("Tiendas_con_art","sum"),
                Tiendas_totales=("Tiendas_totales","sum"))
           .reset_index())
    art["Cobertura_%"] = (art["Tiendas_con_art"]/art["Tiendas_totales"]*100).clip(0,100)
    return art  # columnas: [ARTICULO, Tiendas_con_art, Tiendas_totales, Cobertura_%]

# === 2) KPIs rápidos: (UPTD>0) y (UPTD>10 & cobertura=0) =====================
def kpis_basicos(df, totales_por_plaza: dict, umbral_inv: int = 3):
    pick = lambda names: next((c for c in names if c in df.columns), None)
    ART = pick(["ARTICULO","Artículo","Articulo"])
    UPT = pick(["UPTD","UPT"])
    if UPT is None:  # si no hay UPTD, devuelve 0 y 0
        return 0, 0
    # UPTD promedio por artículo
    upt = df[[ART,UPT]].copy()
    upt[UPT] = pd.to_numeric(upt[UPT], errors="coerce")
    uptd_art = upt.groupby(ART)[UPT].mean().reset_index().rename(columns={UPT:"UPTD_mean"})
    # Cobertura por artículo
    cov = cobertura_por_articulo(df, totales_por_plaza, umbral_inv)
    m = cov.merge(uptd_art, on=ART, how="left").fillna({"UPTD_mean":0})
    kpi1 = int((m["UPTD_mean"] > 0).sum())
    kpi2 = int(((m["UPTD_mean"] > 5) & (m["Cobertura_%"] == 0)).sum())
    return kpi1, kpi2

# === 3) Top UPTD con baja cobertura (<umbral) =================================
def top_uptd_baja_cobertura(df, totales_por_plaza: dict, umbral_inv: int = 3, cov_thresh: float = 85.0):
    pick = lambda names: next((c for c in names if c in df.columns), None)
    ART = pick(["ARTICULO","Artículo","Articulo"])
    UPT = pick(["UPTD","UPT"])
    if UPT is None:  # sin UPTD
        return ("—", float("nan"), float("nan"))
    cov = cobertura_por_articulo(df, totales_por_plaza, umbral_inv)
    upt = df[[ART,UPT]].copy()
    upt[UPT] = pd.to_numeric(upt[UPT], errors="coerce")
    uptd_art = upt.groupby(ART)[UPT].mean().reset_index().rename(columns={UPT:"UPTD_mean"})
    m = cov.merge(uptd_art, on=ART, how="left").dropna(subset=["UPTD_mean"])
    m = m[m["Cobertura_%"] < cov_thresh].sort_values("UPTD_mean", ascending=False)
    if m.empty: return ("—", float("nan"), float("nan"))
    r = m.iloc[0]
    return (str(r[ART]), float(r["UPTD_mean"]), float(r["Cobertura_%"]))


TOTALES_PLAZA = {
    "Coahuila (Saltillo)":85, "Coahuila (Torreón)":54, "Morelos":12, "México":390,
    "Nuevo León":751, "Puebla":22, "Quintana Roo":79, "Tamaulipas (Matamoros)":59,
    "Tamaulipas (Reynosa)":168, "Baja California (Tijuana)":86, "Baja California (Mexicali)":61,
    "Baja California (Ensenada)":24, "Jalisco":181, "Yucatán":54, "Sonora (Hermosillo)":21,
}




# KPI 1 y 2
k1, k2 = kpis_basicos(df_venta_perdida_filtrada, TOTALES_PLAZA, umbral_inv=3)
# KPI 3
name, uptd, covp = top_uptd_baja_cobertura(df_venta_perdida_filtrada, TOTALES_PLAZA, umbral_inv=3, cov_thresh=85)

with kpi_top:
    c6, c7, c8 = st.columns([4, 3, 4])
    with c6:
        st.metric("🐌 Artículos con UPTD > 0", f"{k1}")
    with c7:
        st.metric("UPTD > 5 con 0% cobertura", f"{k2}")
    with c8:
        delta_txt = f"UPTD {uptd:.2f} • Cobertura {covp:.0f}%" if pd.notna(uptd) else "—"
        st.metric("⚠️ Mayor UPTD con baja cobertura", name, delta=delta_txt)
