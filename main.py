import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Guardian Pro", page_icon="🛡️", layout="wide")

# --- CONEXIÓN IA (GROQ) ---
api_key = st.secrets.get("GROQ_API_KEY")
client = None

if api_key:
    try:
        client = Groq(api_key=api_key)
    except Exception as e:
        st.error(f"Error al conectar con la IA: {e}")
else:
    st.warning("⚠️ No se encontró la GROQ_API_KEY en los Secrets.")

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
            
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_l = str(f_fec).replace("-", "")
                p = urllib.parse.urlencode({"action":"TEMPLATE","text":f"PAGAR {f_des}","dates":f"{f_l}/{f_l}"})
                st.info(f"📅 [Agendar en Calendar](https://www.google.com/calendar/render?{p})")
            
            st.success("Guardado.")
            st.rerun()

with tabs[1]:
    st.subheader("Estado de Cuentas")
    c = st.columns(3)
    c[0].metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    c[1].metric("Mach", f"${saldos['MACH']:,.0f}")
    c[2].metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    st.divider()
    if not df_mov.empty:
        st.subheader("Historial Reciente")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[2]:
    st.subheader("🕵️ Analista IA (Llama 3)")
    if client:
        user_ask = st.text_input("¿En qué puedo ayudarte hoy, Pablo?")
        if user_ask:
            ctx = f"Saldos: Mach ${saldos['MACH']}, Billetera ${saldos['BILLETERA']}, Destacame ${saldos['DESTACAME']}. Total: ${total_patrimonio}."
            with st.spinner("IA Pensando..."):
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "Eres un analista financiero experto. Ayuda a Pablo Moreno con sus finanzas."},
                            {"role": "user", "content": f"Datos: {ctx}. Pregunta: {user_ask}"}
                        ],
                        model="llama3-8b-8192", # Usamos Llama 3 que es gratis y veloz
                    )
                    st.info(f"🤖 **Analista:** {chat_completion.choices[0].message.content}")
                except Exception as e:
                    st.error(f"Error de IA: {e}")
    else:
        st.error("IA no configurada.")

with tabs[3]:
    st.subheader("Simulador")
    m_s = st.number_input("Gasto proyectado $", min_value=0)
    if st.button("¿Es viable?"):
        if (total_patrimonio - m_s) < 100000:
            st.error(f"❌ RECHAZADO. Debes proteger tus $100.000 de ahorro.")
        else:
            st.success(f"✅ PERMITIDO. No afecta tu meta.")

if st.sidebar.button("🗑️ REINICIAR TODO"):
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    st.rerun()
