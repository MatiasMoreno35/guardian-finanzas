import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la página estilo App Móvil
st.set_page_config(page_title="Guardian $100K", page_icon="🛡️")

# --- ESTILO VISUAL ---
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #007BFF; color: white; }
    .stMetric { background-color: #ffffff; padding: 10px; border-radius: 15px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛡️ Guardian Financiero")

# --- MANEJO DE DATOS LOCALES ---
# Como estamos en Streamlit Cloud, usaremos un archivo CSV local
FILE_DB = "movimientos_db.csv"

def cargar_datos():
    if os.path.exists(FILE_DB):
        return pd.read_csv(FILE_DB)
    return pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])

def guardar_datos(df):
    df.to_csv(FILE_DB, index=False)

# Cargar base de datos
df_mov = cargar_datos()

# --- SIDEBAR: TUS CUENTAS ---
st.sidebar.header("💰 Saldos Actuales")
s_billetera = st.sidebar.number_input("Billetera Física", value=0)
s_mach = st.sidebar.number_input("Cuenta Mach", value=0)
s_destacame = st.sidebar.number_input("Cuenta Destácame", value=0)

total_actual = s_billetera + s_mach + s_destacame

# --- INTERFAZ PRINCIPAL ---
tab1, tab2, tab3 = st.tabs(["📝 REGISTRO", "📊 ANÁLISIS IA", "🔮 SIMULADOR"])

with tab1:
    st.subheader("Nuevo Movimiento")
    with st.form("registro_gasto", clear_on_submit=True):
        f_tipo = st.selectbox("Operación", ["GASTO", "INGRESO", "AHORRO"])
        f_cuenta = st.selectbox("Cuenta", ["BILLETERA", "MACH", "DESTACAME"])
        f_cat = st.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
        f_monto = st.number_input("Monto $", min_value=0)
        f_desc = st.text_input("Descripción").upper()
        
        if st.form_submit_button("💾 GUARDAR"):
            nueva_fila = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), f_tipo, f_cuenta, f_cat, f_desc, f_monto]], 
                                      columns=df_mov.columns)
            df_mov = pd.concat([df_mov, nueva_fila], ignore_index=True)
            guardar_datos(df_mov)
            st.success("Guardado correctamente")

with tab2:
    st.metric("Patrimonio Total", f"${total_actual:,.0f}")
    
    # Análisis de IA
    st.subheader("🤖 Análisis de la IA")
    meta = 100000
    if total_actual < meta:
        st.warning(f"Faltan `${meta - total_actual:,.0f}` para tu meta de ahorro mensual.")
    else:
        st.success(f"¡Felicidades! Tienes `${total_actual - meta:,.0f}` sobre tu meta de ahorro.")
    
    if not df_mov.empty:
        st.write("Últimos movimientos:")
        st.dataframe(df_mov.tail(5))

with tab3:
    st.subheader("Simulador de Gastos")
    m_sim = st.number_input("¿Cuánto cuesta?", value=0)
    if st.button("¿Puedo comprarlo?"):
        if (total_actual - m_sim) < 100000:
            st.error("❌ NO. Arruinas tu meta de ahorro de $100.000.")
        else:
            st.success(f"✅ SÍ. Te sobran ${(total_actual - m_sim - 100000):,.0f} después de ahorrar.")
