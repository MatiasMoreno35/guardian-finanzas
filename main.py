import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guardian Pro", page_icon="🛡️", layout="wide")

# --- CONEXIÓN IA REFORZADA ---
# Llave proporcionada: AIzaSyCpU64iUKy5m91g8phWk6GpjdmtSNfVEgU
api_key = st.secrets.get("GEMINI_API_KEY")
model_ai = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Forzamos el nombre técnico exacto para evitar el error 404 de versión beta
        model_ai = genai.GenerativeModel(model_name='gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error de inicialización: {e}")
else:
    st.warning("⚠️ Configura la GEMINI_API_KEY en los Secrets de Streamlit.")

# --- GESTIÓN DE DATOS ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

# --- CÁLCULO DE SALDOS ---
saldos = {"BILLETERA": 0.0, "MACH": 0.0, "DESTACAME": 0.0}
for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        if row['TIPO'] == 'INGRESO':
            saldos[row['CUENTA']] += m
        else:
            saldos[row['CUENTA']] -= m
    except: continue
total_patrimonio = sum(saldos.values())

# --- INTERFAZ ---
st.title("🛡️ Guardian Financiero Pro")

tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN", "🕵️ ANALISTA IA", "🔮 SIMULADOR"])

with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    with st.form("f_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cta = c1.selectbox("Cuenta", ["BILLETERA", "MACH", "DESTACAME"])
        f_mto = c1.number_input("Monto $", min_value=0, step=1000)
        f_fec = c2.date_input("Fecha", datetime.now())
        f_cat = c2.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"]) if t_op == "GASTO" else "INGRESO 💰"
        f_des = st.text_input("Descripción").upper()
        if st.form_submit_button("💾 GUARDAR"):
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            st.success("Guardado exitosamente.")
            st.rerun()

with tabs[1]:
    st.subheader("Saldos Actuales")
    c = st.columns(3)
    c[0].metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    c[1].metric("Cuenta Mach", f"${saldos['MACH']:,.0f}")
    c[2].metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    
    st.divider()
    if not df_mov.empty:
        st.subheader("Gastos por Categoría")
        g_df = df_mov[df_mov['TIPO'] == 'GASTO']
        if not g_df.empty:
            st.table(g_df.groupby('CATEGORIA')['MONTO'].sum().reset_index().style.format({"MONTO": "${:,.0f}"}))
        st.subheader("Historial Reciente")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[2]:
    st.subheader("🕵️ Chat con tu Analista")
    if model_ai:
        user_ask = st.text_input("Hazle una pregunta a la IA:")
        if user_ask:
            ctx = f"Saldos: Mach ${saldos['MACH']}, Billetera ${saldos['BILLETERA']}, Destacame ${saldos['DESTACAME']}. Total: ${total_patrimonio}."
            with st.spinner("Analizando información..."):
                try:
                    # Llamada directa al modelo
                    response = model_ai.generate_content(f"Eres asesor financiero de Francisco. Contexto: {ctx}. Pregunta: {user_ask}")
                    st.info(f"🤖 **Analista:** {response.text}")
                except Exception as e:
                    st.error(f"Error detectado: {e}")
                    st.warning("Si el error es 404, por favor haz 'Clear Cache' y luego 'Reboot' en Streamlit Cloud.")
    else:
        st.error("IA desactivada por falta de API Key.")

with tabs[3]:
    st.subheader("Simulador de Gasto")
    m_s = st.number_input("Monto a simular $", min_value=0)
    if st.button("¿Es viable?"):
        if (total_patrimonio - m_s) < 100000:
            st.error(f"❌ RECHAZADO. Debes proteger tus $100.000 de ahorro.")
        else:
            st.success(f"✅ PERMITIDO. Tu meta de ahorro está a salvo.")

if st.sidebar.button("🗑️ REINICIAR TODO"):
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    st.rerun()
