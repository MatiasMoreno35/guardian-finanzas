import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Smart Wallet", page_icon="💰", layout="wide")

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

# --- SIDEBAR: META MENSUAL ---
with st.sidebar:
    st.title("⚙️ Configuración")
    # Formato visual $100.000 para la meta
    meta_mensual = st.number_input("Meta de Ahorro Mensual", min_value=0, value=100000, step=10000, format="%d")
    st.write(f"Meta actual: **${meta_mensual:,.0f}**")
    st.divider()
    if st.button("🗑️ REINICIAR BASE DE DATOS"):
        if os.path.exists(FILE_DB): 
            os.remove(FILE_DB)
            st.rerun()

# --- CÁLCULO DE SALDOS ---
cuentas_capital = ["Billetera física", "Cuenta Mach", "Cuenta destacame"]
saldos = {cta: 0.0 for cta in cuentas_capital + ["Ahorro"]}

for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        cta = row['CUENTA']
        if row['TIPO'] == 'INGRESO':
            saldos[cta] += m
        else:
            # Los gastos ahora restan del capital general. 
            # Para mantener integridad, se descuentan de la primera cuenta disponible o proporcionalmente
            saldos[cta] -= m
    except: continue

total_capital = sum(saldos[c] for c in cuentas_capital)
saldo_ahorro = saldos["Ahorro"]

# --- INTERFAZ ---
st.title("💳 Smart Wallet")

tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN", "🕵️ ANALISTA IA"])

# --- PESTAÑA 1: REGISTRO ---
with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Tipo de Movimiento", ["GASTO", "INGRESO"], horizontal=True)
    
    with st.form("f_reg", clear_on_submit=True):
        if t_op == "GASTO":
            # Eliminada la selección de cuenta para gastos
            c1, c2 = st.columns(2)
            f_cat = c1.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
            
            # Fecha condicional: Vencimiento para fijos, Hoy para el resto
            if f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_fec = c2.date_input("Fecha de Vencimiento", datetime.now())
            else:
                f_fec = datetime.now().date()
                c2.info("Fecha: Hoy")
            
            f_mto = st.number_input("Valor $", min_value=0, step=1000, format="%d")
            f_des = st.text_input("Descripción").upper()
            # Internamente se asigna a 'Billetera física' como cuenta por defecto para el descuento de capital
            f_cta_interna = "Billetera física" 
            
        else:
            # Para ingresos se mantiene la cuenta de destino
            c1, c2 = st.columns(2)
            f_cta_interna = c1.selectbox("Destino del dinero", ["Billetera física", "Cuenta Mach", "Cuenta destacame", "Ahorro"])
            f_mto = c1.number_input("Monto $", min_value=0, step=1000, format="%d")
            f_fec = c2.date_input("Fecha de Ingreso", datetime.now())
            f_cat = "INGRESO 💰"
            f_des = st.text_input("Descripción (Ej: Sueldo)").upper()

        if st.form_submit_button("💾 GUARDAR"):
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta_interna, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            # Google Calendar para fijos
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_l = str(f_fec).replace("-", "")
                p = urllib.parse.urlencode({"action":"TEMPLATE","text":f"PAGAR {f_des}","details":f"Monto: ${f_mto:,.0f}","dates":f"{f_l}/{f_l}"})
                st.info(f"📅 [Agendar Recordatorio](https://www.google.com/calendar/render?{p})")
            
            st.success("Registrado.")
            st.rerun()

# --- PESTAÑA 2: RESUMEN ---
with tabs[1]:
    st.subheader("Estado de Cuentas")
    c = st.columns(4)
    c[0].metric("Billetera física", f"${saldos['Billetera física']:,.0f}")
    c[1].metric("Cuenta Mach", f"${saldos['Cuenta Mach']:,.0f}")
    c[2].metric("Cuenta destacame", f"${saldos['Cuenta destacame']:,.0f}")
    c[3].metric("Ahorro", f"${saldo_ahorro:,.0f}")
    
    st.divider()
    col_cap, col_meta = st.columns(2)
    col_cap.metric("CAPITAL TOTAL", f"${total_capital:,.0f}")
    col_meta.metric("META MENSUAL", f"${meta_mensual:,.0f}")
    
    if not df_mov.empty:
        st.subheader("Historial")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- PESTAÑA 3: ANALISTA IA ---
with tabs[2]:
    st.subheader("🕵️ Analista Smart Wallet")
    if client:
        user_ask = st.text_input("Pregunta sobre tus gastos o presupuesto:")
        if user_ask:
            ctx = f"Pablo Moreno tiene Capital: ${total_capital}, Ahorro aparte: ${saldo_ahorro}, Meta: ${meta_mensual}."
            with st.spinner("Pensando..."):
                try:
                    chat = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "Eres un analista financiero para Pablo Moreno. Usa sus datos para aconsejar sobre compras y ahorro."},
                            {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}
                        ],
                        model="llama-3.1-8b-instant",
                    )
                    st.info(f"🤖 **Analista:** {chat.choices[0].message.content}")
                except Exception as e:
                    st.error(f"Error: {e}")
