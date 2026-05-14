import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Smart Wallet", page_icon="💰", layout="wide")

# --- CONEXIÓN IA ---
api_key = st.secrets.get("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

# --- BASE DE DATOS ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

# --- INICIALIZACIÓN DE ESTADO ---
if "meta_ahorro" not in st.session_state:
    st.session_state.meta_ahorro = 100000

# Función para limpiar campos después de guardar
def reset_campos():
    st.session_state["monto_input"] = ""
    st.session_state["desc_input"] = ""

# --- BOTONES SUPERIORES (ESQUINA) ---
col_vacia, col_meta, col_reset = st.columns([2, 1, 1])
with col_meta:
    st.session_state.meta_ahorro = st.number_input("Meta Mensual $", min_value=0, value=st.session_state.meta_ahorro, step=10000)
with col_reset:
    st.write(" <br> ", unsafe_allow_html=True) # Espaciador
    if st.button("🗑️ Reiniciar Base", use_container_width=True):
        if os.path.exists(FILE_DB): 
            os.remove(FILE_DB)
            st.rerun()

# --- CÁLCULOS ---
cuentas_cap = ["Billetera física", "Cuenta Mach", "Cuenta destacame"]
saldos = {cta: 0.0 for cta in cuentas_cap + ["Ahorro"]}
for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        saldos[row['CUENTA']] = saldos.get(row['CUENTA'], 0) + (m if row['TIPO'] == 'INGRESO' else -m)
    except: continue
total_capital = sum(saldos[c] for c in cuentas_cap)

# --- INTERFAZ PRINCIPAL ---
st.title("💳 Smart Wallet")
tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN", "🕵️ ANALISTA IA"])

with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    
    c1, c2 = st.columns(2)
    
    if t_op == "GASTO":
        f_cat = c1.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
        if f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
            f_fec = c2.date_input("Vencimiento", datetime.now())
        else:
            f_fec = datetime.now().date()
        
        raw_mto = st.text_input("Valor $", key="monto_input", placeholder="Ej: 5000")
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        f_mto = int(clean_mto) if clean_mto.isdigit() else 0
        
        if f_mto > 0:
            st.markdown(f"### **${f_mto:,.0f}**")
            
        f_des = st.text_input("DESCRIPCIÓN", key="desc_input").upper()
        f_cta_int = "Billetera física"
        
    else:
        f_cta_int = c1.selectbox("Destino", ["Billetera física", "Cuenta Mach", "Cuenta destacame", "Ahorro"])
        raw_mto = c1.text_input("Monto $", key="monto_input", placeholder="Ej: 100000")
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        f_mto = int(clean_mto) if clean_mto.isdigit() else 0
        
        if f_mto > 0:
            c1.markdown(f"### **${f_mto:,.0f}**")
            
        f_fec = c2.date_input("Fecha", datetime.now())
        f_cat = "INGRESO 💰"
        f_des = st.text_input("DESCRIPCIÓN", key="desc_input").upper()

    if st.button("💾 GUARDAR MOVIMIENTO", use_container_width=True):
        if f_mto > 0:
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta_int, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            # Calendario
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_l = str(f_fec).replace("-", "")
                p = urllib.parse.urlencode({"action":"TEMPLATE","text":f"PAGAR {f_des}","dates":f"{f_l}/{f_l}"})
                cal_url = f"https://www.google.com/calendar/render?{p}"
                st.success(f"✅ Registrado. [AGENDAR EN CALENDAR]({cal_url})")
            else:
                st.success("✅ ¡Movimiento registrado!")
            
            # Resetear y refrescar
            reset_campos()
            st.rerun()

with tabs[1]:
    st.subheader("Estado Financiero")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Billetera", f"${saldos['Billetera física']:,.0f}")
    col2.metric("Mach", f"${saldos['Cuenta Mach']:,.0f}")
    col3.metric("Destácame", f"${saldos['Cuenta destacame']:,.0f}")
    col4.metric("Ahorro", f"${saldos['Ahorro']:,.0f}")
    
    st.divider()
    c_met1, c_met2 = st.columns(2)
    c_met1.metric("CAPITAL TOTAL", f"${total_capital:,.0f}")
    c_met2.metric("META MENSUAL", f"${st.session_state.meta_ahorro:,.0f}")
    
    if not df_mov.empty:
        st.subheader("Historial")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[2]:
    st.subheader("🕵️ Analista Smart Wallet")
    if client:
        user_ask = st.text_input("Consulta a tu analista:")
        if user_ask:
            ctx = f"Capital: ${total_capital}, Ahorro: ${saldos['Ahorro']}, Meta: ${st.session_state.meta_ahorro}."
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Analista financiero de Pablo Moreno."},
                          {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            st.info(f"🤖 {chat.choices[0].message.content}")
