import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# ---------------- CONFIGURACIÓN GENERAL ----------------
st.set_page_config(
    page_title="Explorador automático de datos",
    page_icon="📊",
    layout="wide"
)

st.title("Explorador automático de datos")
st.markdown("Esta aplicación permite cargar un archivo de datos y realizar un análisis exploratorio automático. "
            "Funciona con diferentes áreas del conocimiento y no requiere programación avanzada.")

# ---------------- FUNCIONES AUXILIARES ----------------
@st.cache_data
def cargar_csv(file):
    try:
        df = pd.read_csv(file)
        return df
    except Exception as e:
        st.error(f"Error al leer CSV: {e}")
        return None

@st.cache_data
def cargar_excel(file, engine):
    try:
        df = pd.read_excel(file, engine=engine)
        return df
    except Exception as e:
        st.error(f"Error al leer Excel: {e}")
        return None

def limpiar_columnas(df):
    df.columns = df.columns.str.strip()
    return df

def detectar_fechas(df):
    for col in df.columns:
        if "fecha" in col.lower() or "date" in col.lower():
            try:
                df[col] = pd.to_datetime(df[col], errors="coerce")
            except:
                pass
    return df

# ---------------- CARGA DEL DATASET ----------------
st.sidebar.header("Carga del dataset")
archivo = st.sidebar.file_uploader("Sube tu archivo (CSV, XLSX, XLS)", type=["csv", "xlsx", "xls"])

if archivo is None:
    st.info("Bienvenido al Explorador automático de datos.\n\n"
            "Formatos permitidos: CSV, XLSX, XLS.\n\n"
            "Etapas de uso:\n1. Cargar\n2. Explorar\n3. Descargar\n\n"
            "Análisis disponibles: indicadores, tipos de variables, duplicados, valores faltantes, "
            "estadísticas, distribuciones, correlaciones, valores atípicos y tabla interactiva.")
    st.stop()

# ---------------- LECTURA DEL ARCHIVO ----------------
nombre_archivo = archivo.name
if nombre_archivo.endswith(".csv"):
    df = cargar_csv(archivo)
elif nombre_archivo.endswith(".xlsx"):
    df = cargar_excel(archivo, engine="openpyxl")
elif nombre_archivo.endswith(".xls"):
    df = cargar_excel(archivo, engine="xlrd")
else:
    st.error("Formato no soportado.")
    st.stop()

if df is None or df.empty:
    st.warning("El archivo está vacío o no pudo ser procesado.")
    st.stop()

df = limpiar_columnas(df)
df = detectar_fechas(df)

# ---------------- INDICADORES GENERALES ----------------
duplicados = df.duplicated().sum()
faltantes = df.isna().sum().sum()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Número de filas", df.shape[0])
col2.metric("Número de columnas", df.shape[1])
col3.metric("Duplicados", duplicados)
col4.metric("Celdas faltantes", faltantes)

# ---------------- PESTAÑAS ----------------
tabs = st.tabs([
    "Resumen y tipos", "Calidad de datos", "Estadísticas",
    "Distribuciones", "Correlaciones", "Valores atípicos", "Tabla ordenable"
])

# ---------------- RESUMEN Y TIPOS ----------------
with tabs[0]:
    st.subheader("Dimensiones del dataset")
    st.write(f"Archivo cargado: **{nombre_archivo}**")
    st.write(f"Filas: {df.shape[0]}, Columnas: {df.shape[1]}")

    resumen = pd.DataFrame({
        "Variable": df.columns,
        "Tipo Pandas": df.dtypes.astype(str),
        "No nulos": df.notna().sum(),
        "Valores únicos": df.nunique()
    })
    def tipo_analitico(dtype):
        if "int" in dtype or "float" in dtype:
            return "Numérica"
        elif "datetime" in dtype:
            return "Fecha/hora"
        elif "bool" in dtype:
            return "Booleana"
        elif resumen["Valores únicos"].max() < 50:
            return "Categórica"
        else:
            return "Texto"
    resumen["Tipo analítico"] = resumen["Tipo Pandas"].apply(tipo_analitico)
    st.dataframe(resumen)

# ---------------- CALIDAD DE DATOS ----------------
with tabs[1]:
    st.subheader("Valores faltantes")
    faltantes_tabla = pd.DataFrame({
        "Variable": df.columns,
        "Faltantes": df.isna().sum(),
        "Porcentaje": (df.isna().sum() / len(df)) * 100
    }).sort_values("Faltantes", ascending=False)
    st.dataframe(faltantes_tabla)

    fig = px.bar(faltantes_tabla, x="Variable", y="Porcentaje", title="Porcentaje de valores faltantes")
    st.plotly_chart(fig)

    st.subheader("Duplicados")
    if duplicados > 0:
        st.write(df[df.duplicated(keep=False)])
    else:
        st.info("No existen registros duplicados.")

# ---------------- ESTADÍSTICAS ----------------
with tabs[2]:
    st.subheader("Estadísticas descriptivas")
    opcion = st.radio("Selecciona tipo de variables", ["Todas", "Numéricas", "Categóricas"])
    try:
        if opcion == "Todas":
            st.write(df.describe(include="all"))
        elif opcion == "Numéricas":
            st.write(df.describe())
        elif opcion == "Categóricas":
            st.write(df.describe(include=["object"]))
    except:
        st.warning("No existen variables del tipo seleccionado.")

# ---------------- DISTRIBUCIONES ----------------
with tabs[3]:
    st.subheader("Distribuciones")
    variable = st.selectbox("Selecciona una variable", df.columns)
    if pd.api.types.is_numeric_dtype(df[variable]):
        bins = st.slider("Número de intervalos", 5, 50, 20)
        fig = px.histogram(df, x=variable, nbins=bins)
        st.plotly_chart(fig)
        fig_box = px.box(df, y=variable)
        st.plotly_chart(fig_box)
    else:
        freq = df[variable].fillna("(Faltante)").value_counts().nlargest(30)
        fig = px.bar(freq, x=freq.index, y=freq.values)
        st.plotly_chart(fig)

# ---------------- CORRELACIONES ----------------
with tabs[4]:
    st.subheader("Correlaciones")
    num_vars = df.select_dtypes(include=np.number).columns.tolist()
    seleccion = st.multiselect("Selecciona variables numéricas", num_vars)
    metodo = st.radio("Método", ["pearson", "spearman", "kendall"])
    if len(seleccion) >= 2:
        corr = df[seleccion].corr(method=metodo)
        fig = go.Figure(data=go.Heatmap(
            z=corr.values, x=corr.columns, y=corr.index,
            colorscale="RdBu", zmin=-1, zmax=1, text=corr.values, texttemplate="%{text:.2f}"
        ))
        st.plotly_chart(fig)
        st.dataframe(corr)
    else:
        st.warning("Selecciona al menos dos variables.")

# ---------------- VALORES ATÍPICOS ----------------
with tabs[5]:
    st.subheader("Valores atípicos")
    num_vars = df.select_dtypes(include=np.number).columns.tolist()
    seleccion = st.multiselect("Selecciona variables", num_vars)
    factor = st.slider("Factor IQR", 1.0, 3.0, 1.5)
    resultados = []
    for var in seleccion:
        Q1, Q3 = df[var].quantile([0.25, 0.75])
        IQR = Q3 - Q1
        lim_inf, lim_sup = Q1 - factor * IQR, Q3 + factor * IQR
        outliers = df[(df[var] < lim_inf) | (df[var] > lim_sup)]
        for idx, row in outliers.iterrows():
            resultados.append({"Fila": idx, "Variable": var, "Valor": row[var],
                               "Límite inferior": lim_inf, "Límite superior": lim_sup})
