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

# --- SIDEBAR: META ---
with st.sidebar:
    st.title("⚙️ Configuración")
    meta_mensual = st.number_input("Meta de Ahorro Mensual", min_value=0, value=100000)
    if st.button("🗑️ REINICIAR TODO"):
        if os.path.exists(FILE_DB): os.remove(FILE_DB)
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

# --- INTERFAZ ---
st.title("💳 Smart Wallet")
tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN", "🕵️ ANALISTA IA"])

with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    
    # --- COLUMNAS DINÁMICAS ---
    c1, c2 = st.columns(2)
    
    if t_op == "GASTO":
        f_cat = c1.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"], key="cat_gasto")
        
        # FECHA: Solo aparece si la categoría es crítica
        if f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
            f_fec = c2.date_input("Vencimiento", datetime.now())
        else:
            f_fec = datetime.now().date()
            # No se muestra nada en c2, queda limpio
        
        # MONTO DINÁMICO: Formateo inmediato
        raw_mto = st.text_input("Valor $", value="", placeholder="Ej: 10000")
        # Limpieza de puntos para procesar el número
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        f_mto = int(clean_mto) if clean_mto.isdigit() else 0
        
        # Si hay un número, lo mostramos arriba del input con puntos de forma elegante
        if f_mto > 0:
            st.markdown(f"### ${f_mto:,.0f}")
            
        f_des = st.text_input("DESCRIPCIÓN").upper()
        f_cta_int = "Billetera física"
        
    else:
        f_cta_int = c1.selectbox("Destino", ["Billetera física", "Cuenta Mach", "Cuenta destacame", "Ahorro"])
        raw_mto = c1.text_input("Monto $", value="")
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        f_mto = int(clean_mto) if clean_mto.isdigit() else 0
        if f_mto > 0:
            c1.markdown(f"### ${f_mto:,.0f}")
            
        f_fec = c2.date_input("Fecha", datetime.now())
        f_cat = "INGRESO 💰"
        f_des = st.text_input("DESCRIPCIÓN").upper()

    # BOTÓN DE GUARDADO ÚNICO
    if st.button("💾 GUARDAR", use_container_width=True):
        if f_mto > 0:
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta_int, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            # Solo agendar si es gasto crítico
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_l = str(f_fec).replace("-", "")
                p = urllib.parse.urlencode({"action":"TEMPLATE","text":f"PAGAR {f_des}","dates":f"{f_l}/{f_l}"})
                st.info(f"📅 [Agendar en Calendar](https://www.google.com/calendar/render?{p})")
            
            st.success("Registrado correctamente.")
            st.rerun()

with tabs[1]:
    st.subheader("Saldos")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Billetera", f"${saldos['Billetera física']:,.0f}")
    col2.metric("Mach", f"${saldos['Cuenta Mach']:,.0f}")
    col3.metric("Destácame", f"${saldos['Cuenta destacame']:,.0f}")
    col4.metric("Ahorro", f"${saldos['Ahorro']:,.0f}")
    st.divider()
    st.metric("CAPITAL TOTAL", f"${total_capital:,.0f}")
    if not df_mov.empty:
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[2]:
    st.subheader("🕵️ Analista IA")
    if client:
        user_ask = st.text_input("Dime, ¿qué necesitas analizar?")
        if user_ask:
            ctx = f"Capital: ${total_capital}, Ahorro: ${saldos['Ahorro']}, Meta: ${meta_mensual}."
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Analista de Pablo Moreno."},
                          {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            st.info(f"🤖 {chat.choices[0].message.content}")
