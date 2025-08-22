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




st.set_page_config(page_title="Reporte de Abasto", page_icon="🏪", layout="wide", initial_sidebar_state="expanded")
st.title("📊 Reporte de Abasto comercial 🏪")
st.markdown("La intención de esta pagina es dar agilidad y poder garantizar tener el 100% de nuestros productos en cada Punto de venta")
st.markdown("Arrastra aquí tu archivo de inventarios")
st.markdown("Puedes hacer preguntas a la IA y ayudarte a identificar los productos en desabasto y con oportunidades. " \
"Además de limpiar aquellos artículos con poco UPTD, con el fin de seguir el proceso de plan de choque")



# 1) Subir .zip
archivo_zip = st.file_uploader("Arrastra aquí tu .zip (con 1 CSV adentro)", type=["zip"])
if not archivo_zip:
    st.stop()

# 2) Abrir ZIP y leer el primer CSV que encuentre
with zipfile.ZipFile(io.BytesIO(archivo_zip.getvalue())) as z:
    csvs = [f for f in z.namelist() if f.lower().endswith(".csv")]
    if not csvs:
        st.error("El ZIP no contiene CSV.")
        st.stop()
    with z.open(csvs[0]) as f:
        df = pd.read_csv(f, encoding="ISO-8859-1")

st.success(f"CSV leído: {csvs[0]}")
st.write("Columnas disponibles:", list(df.columns))
st.dataframe(df.head(), use_container_width=True)

# 3) Gráfica de prueba (deja aquí tus columnas)
X_COL = "TIENDA"  # ← pon aquí la columna para eje X (ej. "Tienda")
Y_COL = "UDS_INVENTARIO"  # ← pon aquí la columna para eje Y (ej. "Ventas")

if X_COL and Y_COL and X_COL in df.columns and Y_COL in df.columns:
    fig = px.bar(df, x=X_COL, y=Y_COL, title=f"{Y_COL} por {X_COL}")
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Define X_COL y Y_COL arriba con nombres de columnas válidos para ver la gráfica.")
