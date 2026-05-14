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
        model = genai.GenerativeModel('gemini-pro')
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
    m = float(row['MONTO'])
    if row['TIPO'] == 'INGRESO':
        saldos[row['CUENTA']] += m
    else:
        saldos[row['CUENTA']] -= m

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
            st.success("Registrado.")
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
        st.subheader("Historial Detallado")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)
        
        st.subheader("Gastos por Categoría")
        gastos_df = df_mov[df_mov['TIPO'] == 'GASTO']
        if not gastos_df.empty:
            resumen_cat = gastos_df.groupby('CATEGORIA')['MONTO'].sum().sort_values(ascending=False).reset_index()
            resumen_cat.columns = ['Categoría', 'Monto Total']
            st.table(resumen_cat.style.format({"Monto Total": "${:,.0f}"}))
    else:
        st.info("No hay datos registrados aún.")

with tab3:
    st.subheader("💬 Consulta a la IA")
    if api_key_disponible:
        pregunta = st.text_input("Hazle una pregunta a tu Analista sobre tus datos:")
        if pregunta:
            # Contexto resumido para la IA
            resumen_gastos = ""
            if not df_mov.empty:
                resumen_gastos = df_mov[df_mov['TIPO']=='GASTO'].groupby('CATEGORIA')['MONTO'].sum().to_string()

            contexto = f"""
            Usuario: Francisco. 
            Patrimonio total: ${total_patrimonio}. 
            Saldos: Billetera ${saldos['BILLETERA']}, Mach ${saldos['MACH']}, Destacame ${saldos['DESTACAME']}. 
            Meta de ahorro: $100.000. 
            Resumen de gastos por categoría: {resumen_gastos}.
            """
            with st.spinner("Analizando..."):
                try:
                    response = model.generate_content(f"Eres un analista financiero fiero pero servicial. Contexto: {contexto}. Pregunta: {pregunta}")
                    st.markdown(f"🤖 **Analista:** {response.text}")
                except Exception as e:
                    st.error(f"Error en la IA: {e}")
    else:
        st.warning("⚠️ La IA está desactivada. Por favor, ingresa tu API KEY en los Secrets de Streamlit con el formato: GEMINI_API_KEY = 'TU_LLAVE'")

with tab4:
    st.subheader("Simulador")
    m_sim = st.number_input("Monto del gasto proyectado $", min_value=0)
    if st.button("¿Es viable realizar este gasto?"):
        disponible = total_patrimonio - m_sim
        if disponible < 100000:
            st.error(f"❌ RECHAZADO. Tu saldo bajaría a ${disponible:,.0f}, lo cual rompe tu meta de ahorro de $100.000.")
        else:
            st.success(f"✅ APROBADO. Te quedarían ${disponible - 100000:,.0f} adicionales después de proteger tu ahorro.")

# Botón de reinicio en Sidebar
if st.sidebar.button("🗑️ REINICIAR TODO"):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
    st.rerun()
