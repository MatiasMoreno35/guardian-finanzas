import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import google.generativeai as genai

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Guardian Pro", page_icon="🛡️", layout="wide")

# --- IA (GEMINI 1.5 FLASH) ---
api_key = st.secrets.get("GEMINI_API_KEY")
model_ai = None
if api_key:
    try:
        genai.configure(api_key=api_key)
        model_ai = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error IA: {e}")

# --- ESTILO DARK ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetric"] { background-color: #1e2130; border: 1px solid #4a4a4a; padding: 15px; border-radius: 15px; }
    .stButton>button { border-radius: 20px; width: 100%; font-weight: bold; background-color: #2e7d32; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- DB ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

# --- SALDOS ---
saldos = {"BILLETERA": 0.0, "MACH": 0.0, "DESTACAME": 0.0}
for _, row in df_mov.iterrows():
    m = float(row['MONTO'])
    if row['TIPO'] == 'INGRESO':
        saldos[row['CUENTA']] += m
    else:
        saldos[row['CUENTA']] -= m
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
            nuevo = pd.DataFrame([[f_fec, t_op, f_cta, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                params = urllib.parse.urlencode({"action": "TEMPLATE", "text": f"PAGAR {f_des}", "details": f"${f_mto}", "dates": f"{str(f_fec).replace('-','')}/{str(f_fec).replace('-','')}"})
                st.markdown(f"### 📅 [AGENDAR EN CALENDARIO](https://www.google.com/calendar/render?{params})")
            st.rerun()

with tabs[1]:
    st.subheader("Resumen de Finanzas")
    cols = st.columns(3)
    cols[0].metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    cols[1].metric("Mach", f"${saldos['MACH']:,.0f}")
    cols[2].metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    
    if not df_mov.empty:
        st.divider()
        st.subheader("Gastos por Categoría")
        g_df = df_mov[df_mov['TIPO'] == 'GASTO']
        if not g_df.empty:
            res = g_df.groupby('CATEGORIA')['MONTO'].sum().reset_index()
            st.table(res.style.format({"MONTO": "${:,.0f}"}))
        
        st.subheader("Historial Completo")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[2]:
    st.subheader("🕵️ Chat con tu Analista")
    if model_ai:
        user_ask = st.text_input("¿En qué te ayudo hoy, Francisco?")
        if user_ask:
            # Enviamos datos limpios para evitar errores de procesamiento
            prompt = f"""
            Contexto Financiero:
            - Patrimonio: ${total_patrimonio}
            - Cuentas: Billetera(${saldos['BILLETERA']}), Mach(${saldos['MACH']}), Destácame(${saldos['DESTACAME']})
            - Meta Ahorro: $100.000
            - Últimos movimientos: {df_mov.tail(5).to_dict('records')}
            
            Pregunta del usuario: {user_ask}
            Responde de forma breve, fiera y profesional.
            """
            with st.spinner("Analizando..."):
                try:
                    resp = model_ai.generate_content(prompt)
                    st.info(f"🤖 **Analista:** {resp.text}")
                except:
                    st.error("La IA tuvo un hipo. Intenta preguntar algo más específico sobre tus saldos.")
    else:
        st.warning("IA no configurada. Revisa tus Secrets.")

with tabs[3]:
    st.subheader("Simulador de Gasto")
    m_f = st.number_input("Monto del capricho $", min_value=0)
    if st.button("¿Puedo?"):
        if (total_patrimonio - m_f) < 100000:
            st.error(f"❌ NO. Quedarías con ${total_patrimonio - m_f:,.0f}. ¡Protege tus 100k!")
        else:
            st.success(f"✅ SÍ. Tu ahorro está a salvo.")

if st.sidebar.button("🗑️ REINICIAR TODO"):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
    st.rerun()
