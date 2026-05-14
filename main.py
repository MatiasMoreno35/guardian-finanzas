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

# --- SIDEBAR: META MENSUAL Y HERRAMIENTAS ---
with st.sidebar:
    st.title("⚙️ Configuración")
    meta_mensual = st.number_input("Meta de Ahorro Mensual $", min_value=0, value=100000, step=10000)
    st.divider()
    if st.button("🗑️ REINICIAR BASE DE DATOS"):
        if os.path.exists(FILE_DB): 
            os.remove(FILE_DB)
            st.rerun()

# --- CÁLCULO DE SALDOS ---
# Cuentas que suman al capital
cuentas_capital = ["Billetera física", "Cuenta Mach", "Cuenta destacame"]
saldos = {cta: 0.0 for cta in cuentas_capital + ["Ahorro"]}

for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        cta = row['CUENTA']
        if row['TIPO'] == 'INGRESO':
            saldos[cta] += m
        else:
            # Los gastos descuentan del capital general (proporcionalmente o de una bolsa común)
            # Para la lógica de visualización, restamos de la cuenta marcada en el registro
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
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    
    with st.form("f_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            # En gastos, se elige de dónde sale el dinero, aunque sumen al mismo capital
            f_cta = st.selectbox("Cuenta", ["Billetera física", "Cuenta Mach", "Cuenta destacame", "Ahorro"])
            f_mto = st.number_input("Monto $", min_value=0, step=1000)
        with c2:
            f_fec = st.date_input("Fecha", datetime.now())
            if t_op == "GASTO":
                f_cat = st.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
            else:
                f_cat = "INGRESO 💰"
        
        f_des = st.text_input("Descripción").upper()
        
        if st.form_submit_button("💾 GUARDAR"):
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            # Recordatorios para el calendario (solo gastos críticos)
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_l = str(f_fec).replace("-", "")
                p = urllib.parse.urlencode({"action":"TEMPLATE","text":f"PAGAR {f_des}","details":f"Monto: ${f_mto:,.0f}","dates":f"{f_l}/{f_l}"})
                st.info(f"📅 [Agendar Recordatorio en Google Calendar](https://www.google.com/calendar/render?{p})")
            
            st.success("Registrado correctamente.")
            st.rerun()

# --- PESTAÑA 2: RESUMEN ---
with tabs[1]:
    st.subheader("Estado de Cuentas")
    c = st.columns(4)
    c[0].metric("Billetera física", f"${saldos['Billetera física']:,.0f}")
    c[1].metric("Cuenta Mach", f"${saldos['Cuenta Mach']:,.0f}")
    c[2].metric("Cuenta destacame", f"${saldos['Cuenta destacame']:,.0f}")
    c[3].metric("Ahorro (Aparte)", f"${saldo_ahorro:,.0f}", delta_color="off")
    
    st.divider()
    col_cap, col_meta = st.columns(2)
    col_cap.metric("CAPITAL TOTAL", f"${total_capital:,.0f}")
    col_meta.metric("META MENSUAL", f"${meta_mensual:,.0f}")
    
    st.divider()
    if not df_mov.empty:
        st.subheader("Historial")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- PESTAÑA 3: ANALISTA IA ---
with tabs[2]:
    st.subheader("🕵️ Analista Smart Wallet")
    if client:
        user_ask = st.text_input("Pregunta sobre tus finanzas, ahorros o futuras compras:")
        if user_ask:
            # Contexto ultra-detallado para que la IA actúe como simulador y analista
            resumen_gastos = ""
            if not df_mov.empty:
                resumen_gastos = df_mov[df_mov['TIPO']=='GASTO'].groupby('CATEGORIA')['MONTO'].sum().to_dict()

            ctx = (
                f"Datos de Pablo Moreno: "
                f"Capital Total: ${total_capital}. "
                f"Saldo en Ahorro: ${saldo_ahorro}. "
                f"Meta de ahorro mensual establecida: ${meta_mensual}. "
                f"Desglose por cuenta: {saldos}. "
                f"Resumen de gastos por categoría: {resumen_gastos}."
            )
            
            with st.spinner("Analizando..."):
                try:
                    chat_completion = client.chat.completions.create(
                        messages=[
                            {
                                "role": "system", 
                                "content": (
                                    "Eres un asesor financiero personal para Pablo Moreno. "
                                    "Tu objetivo es ayudarle a decidir si puede hacer compras, "
                                    "analizar sus saldos y motivarlo a cumplir su meta mensual. "
                                    "Si una compra hace que el capital baje de la meta mensual, adviértele seriamente."
                                )
                            },
                            {"role": "user", "content": f"Contexto financiero: {ctx}. Pregunta del usuario: {user_ask}"}
                        ],
                        model="llama-3.1-8b-instant",
                    )
                    st.info(f"🤖 **Analista:** {chat_completion.choices[0].message.content}")
                except Exception as e:
                    st.error(f"Error de IA: {e}")
    else:
        st.error("IA no configurada.")
