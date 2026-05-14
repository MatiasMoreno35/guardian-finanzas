import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
import google.generativeai as genai

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Guardian Pro", page_icon="🛡️", layout="wide")

# --- CONEXIÓN IA REFORZADA ---
# Usa la nueva llave que creaste en un "New Project" de Google AI Studio
api_key = st.secrets.get("GEMINI_API_KEY")
model_ai = None

if api_key:
    try:
        genai.configure(api_key=api_key)
        # Usamos 'gemini-1.5-flash' sin prefijos de versión para evitar el error 404
        model_ai = genai.GenerativeModel('gemini-1.5-flash')
    except Exception as e:
        st.error(f"Error de Configuración: {e}")
else:
    st.warning("⚠️ No se encontró la API KEY en los Secrets de Streamlit.")

# --- BASE DE DATOS LOCAL ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

# --- LÓGICA DE SALDOS (Billetera, Mach, Destácame) ---
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

# --- INTERFAZ PRINCIPAL ---
st.title("🛡️ Guardian Financiero Pro")

tabs = st.tabs(["📝 REGISTRO", "📊 RESUMEN DETALLADO", "🕵️ ANALISTA IA", "🔮 SIMULADOR"])

# --- PESTAÑA 1: REGISTRO ---
with tabs[0]:
    st.subheader("Nuevo Movimiento")
    t_op = st.radio("Operación", ["GASTO", "INGRESO"], horizontal=True)
    
    with st.form("f_reg", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            f_cta = st.selectbox("Cuenta de destino/origen", ["BILLETERA", "MACH", "DESTACAME"])
            f_mto = st.number_input("Monto $", min_value=0)
        with c2:
            f_fec = st.date_input("Fecha", datetime.now())
            if t_op == "GASTO":
                f_cat = st.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
            else:
                f_cat = "INGRESO 💰"
        
        f_des = st.text_input("Descripción (Ej: Pago Luz, Bono, etc.)").upper()
        
        if st.form_submit_button("💾 GUARDAR"):
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta, f_cat, f_des, f_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            # Alerta de Calendario para gastos críticos
            if t_op == "GASTO" and f_cat in ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡"]:
                f_limpia = str(f_fec).replace("-", "")
                params = urllib.parse.urlencode({
                    "action": "TEMPLATE", 
                    "text": f"PAGAR {f_des}", 
                    "details": f"Monto: ${f_mto:,.0f}", 
                    "dates": f"{f_limpia}/{f_limpia}"
                })
                st.markdown(f"### 📅 [AGENDAR EN GOOGLE CALENDAR](https://www.google.com/calendar/render?{params})")
            
            st.success("Movimiento registrado con éxito.")
            st.rerun()

# --- PESTAÑA 2: RESUMEN DETALLADO ---
with tabs[1]:
    st.subheader("Estado Actual")
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
        
        st.subheader("Historial de Movimientos")
        st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)
    else:
        st.info("No hay datos registrados todavía.")

# --- PESTAÑA 3: ANALISTA IA ---
with tabs[2]:
    st.subheader("🕵️ Chat con tu Analista")
    if model_ai:
        user_ask = st.text_input("Hazle una pregunta a tu IA sobre tus finanzas:")
        if user_ask:
            # Contexto simplificado para evitar errores de red
            ctx = f"Saldos: Mach ${saldos['MACH']}, Billetera ${saldos['BILLETERA']}, Destacame ${saldos['DESTACAME']}. Patrimonio total: ${total_patrimonio}."
            with st.spinner("Consultando al analista..."):
                try:
                    response = model_ai.generate_content(f"Eres un analista financiero experto. Usuario: Francisco. Datos: {ctx}. Pregunta: {user_ask}")
                    st.info(f"🤖 **Analista:** {response.text}")
                except Exception as e:
                    st.error(f"Error de respuesta de la IA: {e}")
    else:
        st.error("❌ IA no configurada correctamente.")

# --- PESTAÑA 4: SIMULADOR ---
with tabs[3]:
    st.subheader("Simulador de Meta de Ahorro")
    m_sim = st.number_input("Monto del gasto que quieres simular $", min_value=0)
    if st.button("¿Puedo realizar este gasto?"):
        if (total_patrimonio - m_sim) < 100000:
            st.error(f"❌ RECHAZADO. Tu saldo bajaría a ${total_patrimonio - m_sim:,.0f}, rompiendo tu meta de ahorro de $100.000.")
        else:
            st.success(f"✅ PERMITIDO. Mantendrías tu meta de ahorro protegida.")

# --- BOTÓN DE REINICIO ---
if st.sidebar.button("🗑️ BORRAR TODOS LOS DATOS"):
    if os.path.exists(FILE_DB):
        os.remove(FILE_DB)
    st.rerun()
