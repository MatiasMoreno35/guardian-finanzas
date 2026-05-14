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
if "form_tick" not in st.session_state:
    st.session_state.form_tick = 0

def trigger_reset():
    st.session_state.form_tick += 1

# --- BOTONES SUPERIORES ---
col_vacia, col_meta, col_reset = st.columns([2, 1, 1])
with col_meta:
    st.session_state.meta_ahorro = st.number_input("Meta Mensual $", min_value=0, value=st.session_state.meta_ahorro, step=10000)
with col_reset:
    st.write(" <br> ", unsafe_allow_html=True)
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
        tipo = row['TIPO']
        cta = row['CUENTA']
        
        if tipo == "INGRESO": saldos[cta] += m
        elif tipo == "GASTO": saldos[cta] -= m
        elif tipo == "DEPOSITO AHORRO":
            saldos[cta] -= m      # Sale de cuenta origen
            saldos["Ahorro"] += m # Entra a ahorro
        elif tipo == "RETIRO AHORRO":
            saldos["Ahorro"] -= m # Sale de ahorro
            saldos[cta] += m      # Entra a cuenta destino
    except: continue

total_capital = sum(saldos[c] for c in cuentas_cap)

# --- INTERFAZ ---
st.title("💳 Smart Wallet")
tabs = st.tabs(["📝 REGISTRO", "🏦 AHORROS", "📊 RESUMEN", "🕵️ ANALISTA IA"])

with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    
    c1, c2 = st.columns(2)
    if t_op == "GASTO":
        f_cat = c1.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
        f_fec = c2.date_input("Vencimiento", datetime.now()) if f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"] else datetime.now().date()
        f_cta_int = "Billetera física"
    else:
        f_cta_int = c1.selectbox("Destino", cuentas_cap)
        f_fec = datetime.now().date()
        f_cat = "INGRESO 💰"

    raw_mto = st.text_input("Monto $", key=f"m_{st.session_state.form_tick}")
    clean_mto = raw_mto.replace(".", "").replace(",", "")
    f_mto = int(clean_mto) if clean_mto.isdigit() else 0
    if f_mto > 0: st.markdown(f"### **${f_mto:,.0f}**")
    
    f_des = st.text_input("DESCRIPCIÓN", key=f"d_{st.session_state.form_tick}").upper()

    if st.button("💾 GUARDAR", use_container_width=True):
        if f_mto > 0:
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta_int, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            trigger_reset()
            st.rerun()

with tabs[1]:
    st.subheader("Traspasos a Ahorro")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.write("**Depositar en Ahorro**")
        acc_ori = st.selectbox("Origen:", cuentas_cap)
        mto_dep = st.number_input("Cantidad a guardar:", min_value=0, step=5000, key="dep")
        if st.button("💰 EJECUTAR DEPÓSITO"):
            if mto_dep > 0 and saldos[acc_ori] >= mto_dep:
                mov = pd.DataFrame([[str(datetime.now().date()), "DEPOSITO AHORRO", acc_ori, "AHORRO 🏦", "TRASPASO A AHORRO", mto_dep]], columns=df_mov.columns)
                pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False)
                st.rerun()

    with col_a2:
        st.write("**Retirar de Ahorro**")
        acc_des = st.selectbox("Destino:", cuentas_cap)
        mto_ret = st.number_input("Cantidad a retirar:", min_value=0, step=5000, key="ret")
        if st.button("💸 EJECUTAR RETIRO"):
            if mto_ret > 0 and saldos["Ahorro"] >= mto_ret:
                mov = pd.DataFrame([[str(datetime.now().date()), "RETIRO AHORRO", acc_des, "AHORRO 🏦", "RETIRO DE AHORRO", mto_ret]], columns=df_mov.columns)
                pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False)
                st.rerun()

with tabs[2]:
    st.subheader("Estado Financiero")
    c_m1, c_m2, c_m3, c_m4 = st.columns(4)
    c_m1.metric("Billetera", f"${saldos['Billetera física']:,.0f}")
    c_m2.metric("Mach", f"${saldos['Cuenta Mach']:,.0f}")
    c_m3.metric("Destácame", f"${saldos['Cuenta destacame']:,.0f}")
    c_m4.metric("AHORRO", f"${saldos['Ahorro']:,.0f}")
    st.divider()
    st.metric("CAPITAL DISPONIBLE", f"${total_capital:,.0f}")
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[3]:
    st.subheader("🕵️ Analista")
    if client:
        user_ask = st.text_input("Pablo, consulta sobre tus finanzas:")
        if user_ask:
            ctx = f"Capital: {total_capital}, Ahorro: {saldos['Ahorro']}, Meta: {st.session_state.meta_ahorro}."
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Analista de Pablo Moreno."},
                          {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            st.info(f"🤖 {chat.choices[0].message.content}")
