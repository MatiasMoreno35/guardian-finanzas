import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Smart Wallet", page_icon="💰", layout="wide")

# --- ARCHIVOS ---
FILE_DB = "movimientos_db.csv"
FILE_CONFIG = "config_usuario.csv"

# --- CARGAR CONFIGURACIÓN ---
if os.path.exists(FILE_CONFIG):
    config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
    USER_NAME = config["nombre"]
    # La meta se carga del archivo, pero se puede modificar en el estado de la sesión
    if "meta_dinamica" not in st.session_state:
        st.session_state.meta_dinamica = float(config["meta"])
    CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split(",")]
    CAT_VENC = [c.strip() for c in config["cat_vencimiento"].split(",")]
    CAT_DIARIO = [c.strip() for c in config["cat_diarias"].split(",")]
else:
    st.title("🚀 Configuración Inicial")
    with st.form("config_form"):
        nombre = st.text_input("¿Cómo te llamas?", "Francisco Moreno")
        meta = st.number_input("Meta de ahorro mensual", value=100000)
        nombres_ctas = st.text_input("Tus cuentas (ej: Billetera, Mach, Destacame)", "Billetera, Mach, Destacame")
        cat_v = st.text_input("Gastos con VENCIMIENTO", "Colegio, Cuentas, Cuotas")
        cat_d = st.text_input("Gastos DIARIOS", "Transporte, Comida, Varios")
        if st.form_submit_button("Guardar Configuración"):
            pd.DataFrame([{"nombre": nombre, "meta": meta, "cuentas": nombres_ctas, 
                           "cat_vencimiento": cat_v, "cat_diarias": cat_d}]).to_csv(FILE_CONFIG, index=False)
            st.rerun()
    st.stop()

# --- BASE DE DATOS Y ESTADO ---
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)

df_mov = pd.read_csv(FILE_DB)

if "form_tick" not in st.session_state:
    st.session_state.form_tick = 0

# --- CÁLCULOS DE SALDOS ---
saldos = {cta: 0.0 for cta in CUENTAS_LISTA + ["Ahorro"]}
for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        tipo, cta = row['TIPO'], row['CUENTA']
        if tipo == "INGRESO": saldos[cta] += m
        elif tipo == "GASTO": saldos[cta] -= m
        elif tipo == "DEPOSITO AHORRO":
            saldos[cta] -= m
            saldos["Ahorro"] += m
        elif tipo == "RETIRO AHORRO":
            saldos["Ahorro"] -= m
            saldos[cta] += m
    except: continue

total_capital = sum(saldos[c] for c in CUENTAS_LISTA)

# --- BOTONES SUPERIORES Y REINICIO ---
c_meta, c_reiniciar = st.columns([3, 1])

with c_meta:
    # Meta modificable dinámicamente
    st.session_state.meta_dinamica = st.number_input("🎯 Meta de Ahorro Actual:", value=st.session_state.meta_dinamica, step=10000)

with c_reiniciar:
    if st.button("🚨 Reiniciar Sistema", use_container_width=True):
        st.session_state.confirmar_reinicio = True

if st.session_state.get("confirmar_reinicio"):
    st.warning("¿Qué deseas reiniciar?")
    col1, col2, col3 = st.columns(3)
    if col1.button("Limpiar Movimientos"):
        os.remove(FILE_DB)
        del st.session_state.confirmar_reinicio
        st.rerun()
    if col2.button("Borrar Todo (Config + Datos)"):
        if os.path.exists(FILE_DB): os.remove(FILE_DB)
        if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
        del st.session_state.confirmar_reinicio
        st.rerun()
    if col3.button("Cancelar"):
        del st.session_state.confirmar_reinicio
        st.rerun()

st.divider()

# --- INTERFAZ PRINCIPAL ---
st.title(f"💳 Wallet de {USER_NAME}")
tabs = st.tabs(["📝 REGISTRO", "🏦 AHORROS", "📊 RESUMEN", "🕵️ ANALISTA IA"])

with tabs[0]:
    t_op = st.radio("Tipo", ["GASTO", "INGRESO"], horizontal=True)
    c1, c2 = st.columns(2)
    
    if t_op == "GASTO":
        sub_t = c1.selectbox("Tipo de Gasto", ["Vencimiento", "Diario"])
        f_cat = c1.selectbox("Categoría", CAT_VENC if sub_t == "Vencimiento" else CAT_DIARIO)
        f_fec = c2.date_input("Vencimiento") if sub_t == "Vencimiento" else datetime.now().date()
        f_cta = c1.selectbox("Cuenta de origen", CUENTAS_LISTA)
    else:
        f_cta = c1.selectbox("Destino", CUENTAS_LISTA)
        f_fec = datetime.now().date()
        f_cat = "INGRESO 💰"

    raw_mto = st.text_input("Monto $", key=f"m_{st.session_state.form_tick}")
    f_des = st.text_input("Descripción", key=f"d_{st.session_state.form_tick}").upper()

    if st.button("💾 GUARDAR REGISTRO", use_container_width=True):
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        if clean_mto.isdigit() and int(clean_mto) > 0:
            nuevo = pd.DataFrame([[str(f_fec), t_op, f_cta, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            if t_op == "GASTO" and f_cat in CAT_VENC:
                f_l = str(f_fec).replace("-", "")
                p = urllib.parse.urlencode({"action":"TEMPLATE","text":f"PAGAR {f_des}","dates":f"{f_l}/{f_l}"})
                st.success(f"✅ Registrado. [Calendar]({cal_url})")
            
            st.session_state.form_tick += 1
            st.rerun()

with tabs[1]:
    st.subheader("Gestión de Ahorros")
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.write("**Depositar en Ahorro**")
        acc_ori = st.selectbox("Desde:", CUENTAS_LISTA, key="acc_ori")
        mto_dep = st.number_input("Monto:", min_value=0, step=5000, key="dep")
        if st.button("💰 DEPOSITAR"):
            mov = pd.DataFrame([[str(datetime.now().date()), "DEPOSITO AHORRO", acc_ori, "AHORRO 🏦", "TRASPASO", mto_dep]], columns=df_mov.columns)
            pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False)
            st.rerun()
    with col_a2:
        st.write("**Retirar de Ahorro**")
        acc_des = st.selectbox("Hacia:", CUENTAS_LISTA, key="acc_des")
        mto_ret = st.number_input("Monto:", min_value=0, step=5000, key="ret")
        if st.button("💸 RETIRAR"):
            mov = pd.DataFrame([[str(datetime.now().date()), "RETIRO AHORRO", acc_des, "AHORRO 🏦", "RETIRO", mto_ret]], columns=df_mov.columns)
            pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False)
            st.rerun()

with tabs[2]:
    st.subheader("Estado Financiero")
    
    # Botón Deshacer
    if not df_mov.empty:
        if st.button("🔙 DESHACER ÚLTIMO REGISTRO", type="primary"):
            df_mov = df_mov[:-1]
            df_mov.to_csv(FILE_DB, index=False)
            st.warning("Último registro eliminado.")
            st.rerun()

    cols_cta = st.columns(len(CUENTAS_LISTA))
    for i, cta in enumerate(CUENTAS_LISTA):
        cols_cta[i].metric(cta, f"${saldos[cta]:,.0f}")
    
    st.divider()
    c_cap, c_aho = st.columns(2)
    c_cap.metric("CAPITAL TOTAL DISPONIBLE", f"${total_capital:,.0f}")
    
    # Delta comparado con la meta dinámica
    diff_meta = saldos['Ahorro'] - st.session_state.meta_dinamica
    c_aho.metric("SALDO EN AHORRO", f"${saldos['Ahorro']:,.0f}", delta=f"{diff_meta:,.0f} vs Meta")
    
    st.subheader("Historial de Movimientos")
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

with tabs[3]:
    api_key = st.secrets.get("GROQ_API_KEY")
    if api_key:
        client = Groq(api_key=api_key)
        user_ask = st.text_input(f"{USER_NAME}, ¿qué quieres analizar hoy?")
        if user_ask:
            ctx = f"Capital: {total_capital}, Ahorro: {saldos['Ahorro']}, Meta: {st.session_state.meta_dinamica}."
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": f"Asesor de Francisco Moreno."},
                          {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            st.info(chat.choices[0].message.content)
