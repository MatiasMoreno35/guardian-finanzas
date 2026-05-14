import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guardian Pro", page_icon="🛡️", layout="wide")

# --- CONEXIÓN IA ---
# Usa la llave de AISelect_20260513_220308_Chrome.jpg en tus Secrets
api_key = st.secrets.get("GEMINI_API_KEY")
model_ai = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Nombre del modelo actualizado para evitar errores 404
        model_ai = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error de Configuración IA: {e}")
else:
    st.warning("⚠️ No se encontró la GEMINI_API_KEY en los Secrets.")

# --- GESTIÓN DE BASE DE DATOS ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

# --- LÓGICA DE SALDOS ---
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

# --- DISEÑO DE INTERFAZ ---
st.title("🛡️ Guardian Financiero Pro")

tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN", "🕵️ ANALISTA IA", "🔮 SIMULADOR"])

# --- PESTAÑA 1: REGISTRO ---
with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Operación", ["GASTO", "INGRESO"], horizontal=True)
    
    with st.form("f_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            f_cta = st.selectbox("Cuenta", ["BILLETERA", "MACH", "DESTACAME"])
            f_mto = st.number_input("Monto $", min_value=0, step=1000)
        with c2:
            f_fec = st.date_input("Fecha", datetime.now())
            if t_op == "GASTO":
                f_cat = st.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
            else:
                f_cat = "INGRESO 💰"
        
        # Se convierte a mayúsculas automáticamente
        f_des = st.text_input("Descripción").upper()
        
        if st.form_submit_button("💾 GUARDAR"):
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            # Link opcional para Google Calendar en gastos fijos
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_limpia = str(f_fec).replace("-", "")
                params = urllib.parse.urlencode({
                    "action": "TEMPLATE", 
                    "text": f"PAGAR {f_des}", 
                    "details": f"Monto: ${f_mto:,.0f}", 
                    "dates": f"{f_limpia}/{f_limpia}"
                })
                st.info(f"📅 [Agendar recordatorio de pago](https://www.google.com/calendar/render?{params})")
            
            st.success("Movimiento guardado.")
            st.rerun()

# --- PESTAÑA 2: RESUMEN ---
with tabs[1]:
    st.subheader("Saldos Actuales")
    cols = st.columns(3)
    cols[0].metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    cols[1].metric("Cuenta Mach", f"${saldos['MACH']:,.0f}")
    cols[2].metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    
    st.divider()
    
    if not df_mov.empty:
        st.subheader("Gastos por Categoría")
        g_df = df_mov[df_mov['TIPO'] == 'GASTO']
        if not g_df.empty:
            res_cat = g_df.groupby('CATEGORIA')['MONTO'].sum().reset_index()
            st.table(res_cat.style.format({"MONTO": "${:,.0f}"}))
        
        st.subheader("Historial Completo")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)
    else:
        st.info("Sin datos registrados.")

# --- PESTAÑA 3: ANALISTA IA ---
with tabs[2]:
    st.subheader("🕵️ Chat con tu Analista")
    if model_ai:
        user_ask = st.text_input("Haz una pregunta sobre tus movimientos o ahorros:")
        if user_ask:
            # Contexto de datos para la IA
            ctx = f"Saldos: Mach ${saldos['MACH']}, Billetera ${saldos['BILLETERA']}, Destacame ${saldos['DESTACAME']}. Patrimonio total: ${total_patrimonio}."
            with st.spinner("Analizando..."):
                try:
                    response = model_ai.generate_content(f"Actúa como analista financiero. Contexto: {ctx}. Pregunta: {user_ask}")
                    st.info(f"🤖 **Analista:** {response.text}")
                except Exception as e:
                    st.error(f"Error de IA: {e}")
                    st.info("Nota: Revisa si el archivo requirements.txt tiene google-generativeai>=0.5.0")
    else:
        st.error("IA desactivada. Revisa tu API Key.")

# --- PESTAÑA 4: SIMULADOR ---
with tabs[3]:
    st.subheader("Simulador de Compra")
    m_sim = st.number_input("¿Cuánto planeas gastar? $", min_value=0)
    if st.button("Verificar Viabilidad"):
        restante = total_patrimonio - m_sim
        if restante < 100000:
            st.error(f"❌ RECHAZADO. Tu patrimonio bajaría a ${restante:,.0f}. Debes mantener al menos $100.000 ahorrados.")
        else:
            st.success(f"✅ PERMITIDO. Mantienes tu margen de ahorro de seguridad.")

# --- SIDEBAR: HERRAMIENTAS ---
with st.sidebar:
    st.write("---")
    if st.button("🗑️ BORRAR BASE DE DATOS"):
        if os.path.exists(FILE_DB):
            os.remove(FILE_DB)
            st.rerun()
