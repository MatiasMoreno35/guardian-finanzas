import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Smart Wallet Personalizable", page_icon="💰", layout="wide")

# --- ARCHIVOS DE PERSISTENCIA ---
FILE_DB = "movimientos_db.csv"
FILE_CONFIG = "config_usuario.csv"

# --- FUNCIÓN DE INICIALIZACIÓN ---
def cargar_config():
    if os.path.exists(FILE_CONFIG):
        return pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
    return None

def guardar_config(datos):
    pd.DataFrame([datos]).to_csv(FILE_CONFIG, index=False)

# --- FLUJO DE CONFIGURACIÓN INICIAL ---
config = cargar_config()

if config is None:
    st.title("🚀 Configuración Inicial de Smart Wallet")
    st.info("Hola, vamos a personalizar tu billetera inteligente.")
    
    with st.form("config_form"):
        nombre = st.text_input("¿Cómo te llamas?")
        meta = st.number_input("¿Cuál es tu meta de ahorro mensual?", min_value=0, value=100000)
        
        st.subheader("Tus Cuentas")
        nombres_ctas = st.text_input("Nombres de tus cuentas (separadas por coma)", "Billetera, Banco Estado, Ahorro")
        
        st.subheader("Tus Categorías")
        cat_vencimiento = st.text_input("Categorías con VENCIMIENTO (ej: Luz, Arriendo, Colegio)", "Cuentas, Cuotas, Colegio")
        cat_diarias = st.text_input("Categorías DIARIAS (ej: Comida, Transporte, Ocio)", "Comida, Transporte, Varios")
        
        if st.form_submit_button("Finalizar Configuración"):
            lista_ctas = [c.strip() for c in nombres_ctas.split(",")]
            # Crear base de datos con saldos iniciales si se desea, o iniciar limpia
            if not os.path.exists(FILE_DB):
                pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
            
            guardar_config({
                "nombre": nombre,
                "meta": meta,
                "cuentas": nombres_ctas,
                "cat_vencimiento": cat_vencimiento,
                "cat_diarias": cat_diarias
            })
            st.success("¡Configuración guardada! Reiniciando...")
            st.rerun()
    st.stop()

# --- SI YA ESTÁ CONFIGURADO, CARGAR APP ---
USER_NAME = config["nombre"]
META_AHORRO = config["meta"]
CUENTAS = [c.strip() for c in config["cuentas"].split(",")]
CAT_VENC = [c.strip() for c in config["cat_vencimiento"].split(",")]
CAT_DIARIO = [c.strip() for c in config["cat_diarias"].split(",")]

# --- CONEXIÓN IA Y BASE DE DATOS ---
api_key = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None
df_mov = pd.read_csv(FILE_DB)

# --- LÓGICA DE SALDOS ---
saldos = {cta: 0.0 for cta in CUENTAS}
for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        if row['TIPO'] == "INGRESO": saldos[row['CUENTA']] += m
        elif row['TIPO'] == "GASTO": saldos[row['CUENTA']] -= m
    except: continue

# --- INTERFAZ PRINCIPAL ---
st.title(f"💰 Billetera de {USER_NAME}")

# Botón para resetear configuración (en caso de error)
if st.sidebar.button("⚙️ Resetear Configuración"):
    os.remove(FILE_CONFIG)
    st.rerun()

tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN", "🕵️ ANALISTA"])

with tabs[0]:
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    c1, c2 = st.columns(2)
    
    if t_op == "GASTO":
        sub_tipo = c1.selectbox("Tipo de Gasto", ["Vencimiento", "Diario"])
        opciones_cat = CAT_VENC if sub_tipo == "Vencimiento" else CAT_DIARIO
        f_cat = c1.selectbox("Categoría", opciones_cat)
        
        f_fec = c2.date_input("Fecha") if sub_tipo == "Vencimiento" else datetime.now().date()
        f_cta = c1.selectbox("Pagar desde", CUENTAS)
    else:
        f_cta = c1.selectbox("Destino de fondos", CUENTAS)
        f_fec = datetime.now().date()
        f_cat = "INGRESO"

    raw_mto = st.text_input("Monto $", key="input_monto")
    f_des = st.text_input("Descripción").upper()

    if st.button("💾 GUARDAR"):
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        if clean_mto.isdigit():
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            st.success("Registrado correctamente")
            st.rerun()

with tabs[1]:
    st.subheader("Estado de Cuentas")
    cols = st.columns(len(CUENTAS))
    for i, cta in enumerate(CUENTAS):
        cols[i].metric(cta, f"${saldos[cta]:,.0f}")
    
    st.divider()
    st.subheader("Historial")
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[2]:
    if client:
        st.subheader(f"Analista Personal de {USER_NAME}")
        pregunta = st.text_input("Haz una consulta:")
        if pregunta:
            res = client.chat.completions.create(
                messages=[{"role": "system", "content": f"Eres el analista de {USER_NAME}."},
                          {"role": "user", "content": pregunta}],
                model="llama-3.1-8b-instant")
            st.info(res.choices[0].message.content)
