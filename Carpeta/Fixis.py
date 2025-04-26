import pandas as pd
import os
import streamlit as st
import plotly.express as px
import numpy as np
import plotly.graph_objects as go
from io import BytesIO
import requests 
import plotly.io as pio

st.set_page_config(page_title="Reporte de Coberturas Cigarros", page_icon="🚬", layout="wide", initial_sidebar_state="expanded")
st.title("🚦 Reporte de Coberturas Cigarros🚬")
