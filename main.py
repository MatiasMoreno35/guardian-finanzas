import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guardian Financiero Pro", page_icon="🛡️", layout="wide")

# --- CONEXIÓN CON IA (GEMINI) ---
api_key_disponible = False
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Usamos flash para que sea más rápido y eficiente
        model = genai.GenerativeModel('gemini-1.5-flash')
        api_key_disponible = True
    except Exception as e:
        st.error(f"Error al configurar Gemini: {e}")

# --- ESTILO VISUAL DARK MODE ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] { background-color: #1e2130; border: 1px solid #4a4a4a; padding: 15px; border-radius: 15px; }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    div[data-testid="stMetricLabel"] { color: #00ff00 !important; }
    .stButton>button { border-radius: 20px; width: 100%; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- BASE DE DATOS ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

# --- LÓGICA DE SALDOS ---
saldos = {"BILLETERA": 0, "MACH": 0, "DESTACAME": 0}
for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        if row['TIPO'] == 'INGRESO':
            saldos[row['CUENTA']] += m
        else:
            saldos[row['CUENTA']] -= m
    except:
        continue

total_patrimonio = sum(saldos.values())

# --- FUNCIONALIDADES ---
def generar_link_calendario(titulo, monto, fecha_vence):
    f_limpia = str(fecha_vence).replace("-", "")
    params = {"action": "TEMPLATE", "text": f"PAGAR {titulo.upper()}", "details": f"Monto: ${monto:,.0f}", "dates": f"{f_limpia}/{f_limpia}"}
    return f"https://www.google.com/calendar/render?{urllib.parse.urlencode(params)}"

# --- INTERFAZ ---
st.title("🛡️ Guardian Financiero Pro")

tab1, tab2, tab3, tab4 = st.tabs(["📝 REGISTRO", "📊 RESUMEN DETALLADO", "🕵️ ANALISTA IA", "🔮 SIMULADOR"])

with tab1:
    st.subheader("Nuevo Movimiento")
    tipo_op = st.radio("Operación", ["GASTO", "INGRESO"], horizontal=True)
    with st.form("registro_form", clear_on_submit=True):
        col_a, col_b = st.columns(2)
        with col_a:
            f_cuenta = st.selectbox("Cuenta", ["BILLETERA", "MACH", "DESTACAME"])
            f_monto = st.number_input("Monto $", min_value=0)
        with col_b:
            f_fecha = st.date_input("Fecha", datetime.now())
            f_cat = st.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"]) if tipo_op == "GASTO" else "INGRESO 💰"
        f_desc = st.text_input("Descripción").upper()
        if st.form_submit_button("💾 GUARDAR"):
            nueva_fila = pd.DataFrame([[f_fecha, tipo_op, f_cuenta, f_cat, f_desc, f_monto]], columns=df_mov.columns)
            pd.concat([df_mov, nueva_fila], ignore_index=True).to_csv(FILE_DB, index=False)
            st.success("Registrado con éxito.")
            if tipo_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                st.markdown(f"### 📅 [AGENDAR EN CALENDARIO]({generar_link_calendario(f_desc, f_monto, f_fecha)})")
            st.rerun()

with tab2:
    st.subheader("Resumen General")
    c1, c2, c3 = st.columns(3)
    c1.metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    c2.metric("Cuenta Mach", f"${saldos['MACH']:,.0f}")
    c3.metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    
    st.divider()
    if not df_mov.empty:
        st.subheader("Gastos por Categoría")
        gastos_df = df_mov[df_mov['TIPO'] == 'GASTO']
        if not gastos_df.empty:
            res_cat = gastos_df.groupby('CATEGORIA')['MONTO'].sum().reset_index()
            st.table(res_cat.style.format({"MONTO": "${:,.0f}"}))
        
        st.subheader("Historial de Movimientos")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)
    else:
        st.info("No hay datos registrados.")

with tab3:
    st.subheader("💬 Consulta a la IA")
    if api_key_disponible:
        pregunta = st.text_input("Pregúntale al Analista (Ej: ¿Cómo van mis gastos de este mes?)")
        if pregunta:
            # Resumen simplificado para no saturar la IA
            contexto = f"Francisco tiene ${total_patrimonio}. En Mach: ${saldos['MACH']}. En Billetera: ${saldos['BILLETERA']}. En Destacame: ${saldos['DESTACAME']}. Meta ahorro: $100.000. Movimientos recientes: {df_mov.tail(5).to_string()}"
            with st.spinner("Analizando tus finanzas..."):
                try:
                    response = model.generate_content(f"Eres un analista financiero experto. Contexto: {contexto}. Pregunta: {pregunta}")
                    st.markdown(f"🤖 **Analista:** {response.text}")
                except Exception as e:
                    st.error("La IA tuvo un problema al procesar. Intenta con una pregunta más corta.")
    else:
        st.warning("Configura tu API KEY en los Secrets de Streamlit.")

with tab4:
    st.subheader("Simulador de Meta")
    m_sim = st.number_input("Monto gasto proyectado $", min_value=0)
    if st.button("¿Consultar viabilidad?"):
        if (total_patrimonio - m_sim) < 100000:
            st.error(f"❌ PELIGRO. Tu saldo caería a ${total_patrimonio - m_sim:,.0f}, por debajo de tu meta de ahorro.")
        else:
            st.success(f"✅ VIABLE. Tu ahorro de $100.000 está protegido.")

if st.sidebar.button("🗑️ REINICIAR DATOS"):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
    st.rerun()
