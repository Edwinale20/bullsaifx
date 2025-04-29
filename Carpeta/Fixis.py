import pandas as pd
import glob
import os
import streamlit as st
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
import plotly.io as pio
import subprocess


@st.cache_data(ttl=3600)
def list_files_in_github_folder(folder_url):
    response = requests.get(folder_url)
    response.raise_for_status()
    files_info = response.json()
    raw_urls = [file_info['download_url'] for file_info in files_info if file_info['type'] == 'file']
    return raw_urls

@st.cache_data(ttl=3600)
def download_file_from_github(url):
    response = requests.get(url)
    response.raise_for_status()
    return BytesIO(response.content)

@st.cache_data
def master(excel):
    df = pd.read_excel(excel)
    df['ARTICULO'] = df['ARTICULO'].astype('str')
    df = df.drop(columns=['UPC', 'SABOR'], errors='ignore')
    return df
# ================================

# ================================
# DESPUÉS defines tus URLs
xlsx_file = 'https://api.github.com/repos/Edwinale20/bullsaifx/contents/Coberturas'
excel = 'https://raw.githubusercontent.com/Edwinale20/bullsaifx/main/MASTER.xlsx'

# ================================
# AHORA ya puedes usar tus funciones

file_urls = list_files_in_github_folder(xlsx_file)

VENTA = pd.DataFrame()

for url in file_urls:
    file_content = download_file_from_github(url)
    df = pd.read_excel(file_content)
    VENTA = pd.concat([VENTA, df], ignore_index=True)

MASTER = master(excel)


st.set_page_config(page_title="Coberturas Cigarros y RRPS", page_icon="🚦", layout="wide", initial_sidebar_state="expanded")
st.title("🚦 Coberturas Cigarros y RRPS 🚬")


# Definir paleta de colores global 
pio.templates["colors"] = pio.templates["plotly"]
pio.templates["colors"].layout.colorway = ['#2C7865', '#EE2526', '#FF9800', '#000000']
pio.templates["colors2"] = pio.templates["plotly"]
pio.templates["colors2"].layout.colorway = ['#2C7865', '#EE2526', '#FF9800', '#000000']
# Aplicar plantilla personalizada por defecto
pio.templates.default = "colors"
pio.templates.default2 = "colors2"

#--------------------------------------------------------------------------------------------------------------
@st.cache_data
def venta(venta_semanal):
    concat_venta = pd.DataFrame()

    for xlsx_file in venta_semanal:
        try:
            df = pd.read_excel(xlsx_file)
            
            # Verificar si ya existe la columna 'Semana Transacción'
            if 'Semana Transacción' not in df.columns:
                print(f"Advertencia: La columna 'Semana Transacción' no existe en {xlsx_file}.")
                continue  # Salta este archivo si no tiene la columna necesaria
            
            # Asegúrate de que la columna 'Semana Transacción' sea de tipo object
            df['Semana Transacción'] = df['Semana Transacción'].astype(str)
            
            # Concatenar los datos
            concat_venta = pd.concat([concat_venta, df], ignore_index=True)
        
        except Exception as e:
            print(f"Error al procesar el archivo {xlsx_file}: {e}")
    
    # Eliminar columnas específicas no deseadas
    concat_venta = concat_venta.drop(columns=['Metrics'], errors='ignore')
    concat_venta['Semana Transacción'] = concat_venta['Semana Transacción'].astype(str)
    concat_venta['Unidades Inventario'] = concat_venta['Unidades Inventario'].astype(str)
    concat_venta['Mercado'] = concat_venta['Mercado'].astype('str')
    concat_venta['Unidades Inventario'] = concat_venta['Unidades Inventario'].str.replace('(', '-', regex=False)
    concat_venta['Unidades Inventario'] = concat_venta['Unidades Inventario'].str.replace(')', '', regex=False)
    concat_venta['Unidades Inventario'] = pd.to_numeric(concat_venta['Unidades Inventario'], errors='coerce').fillna(0)
    concat_venta['Unnamed: 7'] = concat_venta['Unnamed: 7'].astype('str')
    concat_venta = concat_venta.rename(columns={
        'Artículo': 'Desc',
        'Unnamed: 7': 'ARTICULO',
    }) 

    return concat_venta
#--------------------------------------------------------------------------------------------------------------

@st.cache_data
def master(excel):
    df = pd.read_excel(excel)
    df['ARTICULO'] = df['ARTICULO'].astype('str')
    df = df.drop(columns=['UPC', 'SABOR'], errors='ignore')
    return df
#--------------------------------------------------------------------------------------------------------------

excel = 'https://raw.githubusercontent.com/Edwinale20/bullsaifx/main/MASTER.xlsx'
MASTER = master(excel)
VENTA = venta(xlsx_file)
#--------------------------------------------------------------------------------------------------------------

# 🗂️ Función para unir los DataFrames correctamente
@st.cache_data
def merge_data():
    if 'ARTICULO' in VENTA.columns and 'ARTICULO' in MASTER.columns:
        return VENTA.merge(MASTER, on='ARTICULO', how='left')
    else:
        print("⚠️ No se encontró la columna 'ARTICULO' en ambos DataFrames. Se usará VENTA solo.")
        return VENTA

MAESTRO = merge_data()




#--------------------------------------------------------------------------------------------------------------

st.sidebar.title("Filtros 🔠")


# Paso 1: Crear una lista de opciones para el filtro, incluyendo "Ninguno"
opciones_proveedor = ['Ninguno'] + list(MAESTRO['PROVEEDOR'].unique())
proveedor = st.sidebar.selectbox('Seleccione el Proveedor', opciones_proveedor)

opciones_division = ['Ninguno'] + list(MAESTRO['División'].unique())
division = st.sidebar.selectbox('Seleccione la División', opciones_division)

opciones_plaza = ['Ninguno'] + list(MAESTRO['Plaza'].unique())
plaza = st.sidebar.selectbox('Seleccione la Plaza', opciones_plaza)

opciones_mercado = ['Ninguno'] + list(MAESTRO['Mercado'].unique())
mercado = st.sidebar.selectbox('Seleccione el Mercado', opciones_mercado)

opciones_semana = ['Ninguno'] + list(MAESTRO['Semana Transacción'].unique())
semana = st.sidebar.selectbox('Seleccione la semana', opciones_semana)

opciones_familia = ['Ninguno'] + list(MAESTRO['FAMILIA'].unique())
familia = st.sidebar.selectbox('Seleccione la Familia', opciones_familia)

opciones_categoria = ['Ninguno'] + list(MAESTRO['SUBCATEGORIA'].unique())
categoria = st.sidebar.selectbox('Seleccione la Categoria', opciones_categoria)



df_venta_filtrada = MAESTRO.copy()

if proveedor != 'Ninguno':
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['PROVEEDOR'] == proveedor]

# Filtrar por División
if division != 'Ninguno':
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['División'] == division]

# Filtrar por Plaza
if plaza != 'Ninguno':
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['Plaza'] == plaza]


# Filtrar por Mercado
if mercado != 'Ninguno':
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['Mercado'] == mercado]

# Filtrar por Semana
if semana != 'Ninguno':
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['Semana Transacción'] == semana]

# Filtrar por Familia
if familia != 'Ninguno':
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['FAMILIA'] == familia]

# Filtrar por Categoria
if categoria != 'Ninguno':
    df_venta_filtrada = df_venta_filtrada[df_venta_filtrada['SUBCATEGORIA'] == categoria]


df_venta_filtrada = df_venta_filtrada[
    (df_venta_filtrada['FAMILIA'] != 'BYE') & (df_venta_filtrada['PROVEEDOR'] != 'BYE')]
#Visualizr la tabla
#st.write(df_venta_filtrada)	

#--------------------------------------------------------------------------------------------------------------
def calcular_cobertura_tabla(df):
    """
    Calcula la cobertura y devuelve una tabla tipo Excel estilizada.
    """

    # Crear columna de cobertura
    df['Cobertura'] = df['Unidades Inventario'].apply(lambda x: 1 if float(x) > 3 else 0)

    # Agrupar por Artículo y Plaza
    tabla_cobertura = df.groupby(['Artículo', 'Plaza']).agg(
        Total_Registros=('Cobertura', 'count'),
        Cobertura_Suma=('Cobertura', 'sum')
    ).reset_index()

    # Calcular porcentaje
    tabla_cobertura['Cobertura %'] = (tabla_cobertura['Cobertura_Suma'] / tabla_cobertura['Total_Registros']) * 100
    tabla_cobertura['Cobertura %'] = tabla_cobertura['Cobertura %'].round(2)

    # Pivot para poner artículos como filas y plazas como columnas
    pivot = tabla_cobertura.pivot(index='Artículo', columns='Plaza', values='Cobertura %')

    # Aplicar formato de colores tipo semáforo
    def color_format(val):
        if pd.isna(val):
            return ''
        elif val >= 90:
            return 'background-color: lightgreen; text-align: center'
        elif val >= 80:
            return 'background-color: yellow; text-align: center'
        else:
            return 'background-color: red; color: white; text-align: center'

    styled = pivot.style.format("{:.0f}%").applymap(color_format)

    return styled


def grafico_cobertura_mercado(df):
    """
    Gráfica de barras: % cobertura por mercado.
    """

    df['Cobertura'] = df['Unidades Inventario'].apply(lambda x: 1 if float(x) > 3 else 0)

    resumen = df.groupby('Mercado').agg(
        Total=('Cobertura', 'count'),
        Cobertura_Suma=('Cobertura', 'sum')
    ).reset_index()

    resumen['Cobertura %'] = (resumen['Cobertura_Suma'] / resumen['Total']) * 100
    resumen['Cobertura %'] = resumen['Cobertura %'].round(2)

    fig = px.bar(
        resumen.sort_values('Cobertura %', ascending=False),
        x='Mercado',
        y='Cobertura %',
        color='Cobertura %',
        color_continuous_scale=["red", "yellow", "lightgreen"],
        title="Cobertura Promedio por Mercado"
    )

    fig.update_layout(
        xaxis_title="Mercado",
        yaxis_title="Cobertura (%)",
        xaxis_tickangle=-45,
        showlegend=False
    )

    return fig


#---------------------------------------------------------------------
# Divisor y encabezado

st.divider()
st.subheader(':orange[Comparación de Ventas por Semana y Categoria]')

figura1 = calcular_cobertura_tabla(df_venta_filtrada)
figura_mercado = grafico_cobertura_mercado(df_venta_filtrada)

col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.dataframe(figura1, use_container_width=True)
with col2:
    st.plotly_chart(figura_mercado, use_container_width=True)    
  
