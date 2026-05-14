import streamlit as st
import pandas as pd
from datetime import datetime
import os
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Guardian Pro", page_icon="🛡️", layout="wide")

# --- CONEXIÓN IA REFORZADA ---
# Según Screenshot_20260513_215240_Chrome.jpg, tu clave empieza con AIzaSyB...
api_key = st.secrets.get("GEMINI_API_KEY")

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Cambiamos la lógica de inicialización
        model_ai = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error de Configuración: {e}")
        model_ai = None
else:
    st.warning("⚠️ No se encontró la API KEY en los Secrets.")
    model_ai = None

# --- BASE DE DATOS ---
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

tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN DETALLADO", "🕵️ ANALISTA IA", "🔮 SIMULADOR"])

with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    with st.form("f_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        f_cta = c1.selectbox("Cuenta", ["BILLETERA", "MACH", "DESTACAME"])
        f_mto = c1.number_input("Monto $", min_value=0)
        f_fec = c2.date_input("Fecha", datetime.now())
        f_cat = c2.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"]) if t_op == "GASTO" else "INGRESO 💰"
        f_des = st.text_input("Descripción").upper()
        if st.form_submit_button("💾 GUARDAR"):
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            st.success("Guardado.")
            st.rerun()

with tabs[1]:
    st.subheader("Estado de tus Cuentas")
    cols = st.columns(3)
    cols[0].metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    cols[1].metric("Mach", f"${saldos['MACH']:,.0f}")
    cols[2].metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    
    st.divider()
    st.subheader("Gastos por Categoría")
    g_df = df_mov[df_mov['TIPO'] == 'GASTO']
    if not g_df.empty:
        res = g_df.groupby('CATEGORIA')['MONTO'].sum().reset_index()
        st.table(res.style.format({"MONTO": "${:,.0f}"}))
    
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[2]:
    st.subheader("🕵️ Chat con tu Analista")
    if model_ai:
        user_ask = st.text_input("Haz una pregunta:")
        if user_ask:
            ctx = f"Saldos: Mach ${saldos['MACH']}, Billetera ${saldos['BILLETERA']}, Destacame ${saldos['DESTACAME']}. Total: ${total_patrimonio}."
            with st.spinner("Analizando..."):
                try:
                    # En lugar de solo el texto, intentamos pasar el prompt limpio
                    response = model_ai.generate_content(f"Eres un asesor financiero. Contexto: {ctx}. Pregunta: {user_ask}")
                    st.info(f"🤖 **Analista:** {response.text}")
                except Exception as e:
                    st.error(f"Error: {e}")
    else:
        st.error("IA no disponible.")

with tabs[3]:
    st.subheader("Simulador")
    m_f = st.number_input("Gasto a simular $", min_value=0)
    if st.button("¿Es viable?"):
        if (total_patrimonio - m_f) < 100000:
            st.error("❌ RECHAZADO. Protege tus $100.000.")
        else:
            st.success("✅ PERMITIDO.")
