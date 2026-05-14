import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guardian Financiero Pro", page_icon="🛡️", layout="wide")

# --- ESTILO VISUAL (DARK MODE PARA LECTURA CLARA) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] {
        background-color: #1e2130;
        border: 1px solid #4a4a4a;
        padding: 15px;
        border-radius: 15px;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #00ff00 !important; }
    .stButton>button { border-radius: 20px; width: 100%; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    df_empty = pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
    df_empty.to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

# --- LÓGICA DE SALDOS ---
saldos = {"BILLETERA": 0, "MACH": 0, "DESTACAME": 0}
for _, row in df_mov.iterrows():
    if row['TIPO'] == 'INGRESO':
        saldos[row['CUENTA']] += row['MONTO']
    else:
        saldos[row['CUENTA']] -= row['MONTO']

total_patrimonio = sum(saldos.values())

# --- FUNCIONALIDAD DE CALENDARIO ---
def generar_link_calendario(titulo, monto, fecha_vence):
    f_limpia = str(fecha_vence).replace("-", "")
    params = {
        "action": "TEMPLATE",
        "text": f"PAGAR {titulo.upper()}",
        "details": f"Monto: ${monto:,.0f}",
        "dates": f"{f_limpia}/{f_limpia}"
    }
    return f"https://www.google.com/calendar/render?{urllib.parse.urlencode(params)}"

# --- INTERFAZ ---
st.title("🛡️ Guardian Financiero Pro")

tab1, tab2, tab3 = st.tabs(["📝 REGISTRO", "🕵️ ANALISTA IA", "🔮 SIMULADOR"])

with tab1:
    st.subheader("Nuevo Movimiento")
    tipo_op = st.radio("Operación", ["GASTO", "INGRESO"], horizontal=True)
    
    with st.form("registro_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            f_cuenta = st.selectbox("Cuenta", ["BILLETERA", "MACH", "DESTACAME"])
            f_monto = st.number_input("Monto $", min_value=0)
        with col_b:
            f_fecha = st.date_input("Fecha (Gasto o Vencimiento)", datetime.now())
            if tipo_op == "GASTO":
                f_cat = st.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
            else:
                f_cat = "INGRESO 💰"
        
        f_desc = st.text_input("Descripción").upper()
        
        btn_save = st.form_submit_button("💾 GUARDAR MOVIMIENTO")
        
        if btn_save:
            nueva_fila = pd.DataFrame([[f_fecha, tipo_op, f_cuenta, f_cat, f_desc, f_monto]], columns=df_mov.columns)
            df_updated = pd.concat([df_mov, nueva_fila], ignore_index=True)
            df_updated.to_csv(FILE_DB, index=False)
            
            st.success(f"Registrado en {f_cuenta}")
            
            # Alerta de Calendario (Solo para gastos críticos)
            if tipo_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                link = generar_link_calendario(f_desc, f_monto, f_fecha)
                st.markdown(f"### 📅 [HAGA CLIC AQUÍ PARA AGREGAR AL CALENDARIO]({link})")
            st.rerun()

with tab2:
    st.subheader("Estado de Cuentas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    c2.metric("Cuenta Mach", f"${saldos['MACH']:,.0f}")
    c3.metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    
    st.divider()
    
    st.subheader("💬 Chat con el Analista")
    pregunta = st.text_input("Pregúntale a la IA sobre tus finanzas:")
    if pregunta:
        # Lógica descriptiva
        if "ahorro" in pregunta.lower():
            if total_patrimonio < 100000:
                st.write(f"🤖 **Analista:** Francisco, estás a `${100000 - total_patrimonio:,.0f}` de tu meta. Revisa los gastos en COMIDA.")
            else:
                st.write(f"🤖 **Analista:** ¡Meta cumplida! Tienes `${total_patrimonio - 100000:,.0f}` de excedente.")
        else:
            st.write("🤖 **Analista:** Estoy revisando tus movimientos en tiempo real. ¿Quieres ver un resumen de gastos?")

with tab3:
    st.subheader("Simulador de Gastos Futuros")
    m_sim = st.number_input("Monto proyectado $", min_value=0)
    d_sim = st.text_input("¿Qué quieres comprar?").upper()
    if st.button("Consultar Viabilidad"):
        if (total_patrimonio - m_sim) < 100000:
            st.error(f"❌ RECHAZADO. Tu saldo bajaría a ${total_patrimonio - m_sim:,.0f}. No cumple la meta de ahorro.")
        else:
            st.success(f"✅ APROBADO. Mantienes el ahorro de $100.000 protegido.")

# Sidebar de Reinicio
if st.sidebar.button("🗑️ REINICIAR DATOS (BORRAR TODO)"):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
    st.rerun()
