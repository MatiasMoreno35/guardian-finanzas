import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Smart Wallet", page_icon="💰", layout="wide")

# --- LÓGICA DE RUTAS Y MULTIUSUARIO ---
user_id = st.query_params.get("user", "comun")
base_path = os.getcwd()
if not os.access(base_path, os.W_OK):
    base_path = "/tmp"

if not os.path.exists(base_path):
    os.makedirs(base_path, exist_ok=True)

FILE_DB = os.path.join(base_path, f"movimientos_{user_id}.csv")
FILE_CONFIG = os.path.join(base_path, f"config_{user_id}.csv")

# --- TRADUCCIONES ---
TEXTS = {
    "es": {
        "config_title": "🚀 Configuración Inicial",
        "name_label": "¿Cómo te llamas?",
        "meta_label": "Meta de ahorro mensual",
        "ctas_label": "Tus cuentas (ej: Billetera, Banco, Ahorro)",
        "venc_label": "Gastos con VENCIMIENTO (separados por coma)",
        "diario_label": "Gastos DIARIOS (separados por coma)",
        "save_config": "Guardar Configuración",
        "meta_actual": "🎯 Meta de Ahorro Actual:",
        "reset_btn": "🚨 Reiniciar Sistema",
        "tab_reg": "📝 REGISTRO",
        "tab_aho": "🏦 AHORROS",
        "tab_res": "📊 RESUMEN",
        "tab_ia": "🕵️ ANALISTA IA",
        "type_op": "Tipo",
        "gasto": "GASTO",
        "ingreso": "INGRESO",
        "cat_label": "Categoría",
        "monto_label": "Monto $",
        "desc_label": "Descripción",
        "save_reg": "💾 GUARDAR REGISTRO",
        "undo_btn": "🔙 DESHACER ÚLTIMO REGISTRO",
        "cap_total": "CAPITAL TOTAL DISPONIBLE",
        "aho_saldo": "SALDO EN AHORRO",
    }
}

# --- BOTÓN DE REINICIAR / BORRAR (En barra lateral, solicitado para pruebas) ---
st.sidebar.title("🛠️ Administración")
if st.sidebar.button(TEXTS["es"]["reset_btn"], use_container_width=True):
    if os.path.exists(FILE_CONFIG):
        os.remove(FILE_CONFIG)
    if os.path.exists(FILE_DB):
        os.remove(FILE_DB)
    st.rerun()

# --- CARGAR CONFIGURACIÓN ---
if os.path.exists(FILE_CONFIG):
    try:
        config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
        USER_NAME = config["nombre"]
        L = config.get("idioma", "es")
        T = TEXTS[L]
        if "meta_dinamica" not in st.session_state:
            st.session_state.meta_dinamica = float(config["meta"])
        CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split(",")]
        CAT_VENC = [c.strip() for c in config["cat_vencimiento"].split(",")]
        CAT_DIARIO = [c.strip() for c in config["cat_diarias"].split(",")]
        
        # Recuperar nuevas variables del perfil inicial
        INGRESO_NETO = float(config.get("ingreso_neto", 0.0))
        PAGA_VIVIENDA = config.get("paga_vivienda", "No")
        MONTO_VIVIENDA = float(config.get("monto_vivienda", 0.0))
        GASTOS_FINANCIEROS = float(config.get("gastos_financieros", 0.0))
        GASTOS_BASICOS = float(config.get("gastos_basicos", 0.0))
        
    except:
        st.error("Error cargando config.")
        if st.button("Reconfigurar"): 
            if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
            st.rerun()
        st.stop()
else:
    st.title(f"🚀 Setup")
    T = TEXTS["es"]
    with st.form("config_form"):
        nombre = st.text_input(T["name_label"]).upper() # Nombre forzado a mayúsculas
        ingreso_neto = st.number_input("Ingreso Neto Mensual ($):", min_value=0.0, step=10000.0, value=0.0)
        meta = st.number_input(T["meta_label"], value=0.0)
        nombres_ctas = st.text_input(T["ctas_label"])
        
        st.subheader("🏠 Situación de Vivienda")
        paga_vivienda = st.radio("¿Pagas actualmente arriendo o dividendo?", ["Sí", "No"])
        monto_vivienda = st.number_input("Monto mensual estimado de Vivienda ($):", min_value=0.0, step=10000.0, value=0.0)

        st.subheader("💳 Otros Gastos Mensuales Estimados")
        gastos_financieros = st.number_input("Gastos Financieros / Deudas ($):", min_value=0.0, step=5000.0, value=0.0)
        gastos_basicos = st.number_input("Gastos Básicos Estimados (Comida, Servicios) ($):", min_value=0.0, step=5000.0, value=0.0)

        cat_v = st.text_input(T["venc_label"])
        cat_d = st.text_input(T["diario_label"])
        
        if st.form_submit_button(T["save_config"]):
            if all([nombre, nombres_ctas, cat_v, cat_d]) and ingreso_neto > 0:
                pd.DataFrame([{
                    "nombre": nombre, 
                    "ingreso_neto": float(ingreso_neto),
                    "meta": float(meta), 
                    "cuentas": nombres_ctas, 
                    "paga_vivienda": paga_vivienda,
                    "monto_vivienda": float(monto_vivienda) if paga_vivienda == "Sí" else 0.0,
                    "gastos_financieros": float(gastos_financieros),
                    "gastos_basicos": float(gastos_basicos),
                    "cat_vencimiento": cat_v, 
                    "cat_diarias": cat_d, 
                    "idioma": "es"
                }]).to_csv(FILE_CONFIG, index=False)
                st.rerun()
            else:
                st.error("Por favor completa los campos y asegúrate de que el ingreso neto sea mayor a 0.")
    st.stop()

# --- BASE DE DATOS ---
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
df_mov = pd.read_csv(FILE_DB)

# --- CÁLCULOS ---
default_cta = CUENTAS_LISTA[0]
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

# --- INTERFAZ ---
st.title(f"💳 {USER_NAME} Wallet")
st.session_state.meta_dinamica = st.number_input(T["meta_actual"], value=st.session_state.meta_dinamica, step=10000.0)

tabs = st.tabs([T["tab_reg"], T["tab_aho"], T["tab_res"], T["tab_ia"]])

# --- PESTAÑA REGISTRO ---
with tabs[0]:
    t_op = st.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    c1, c2 = st.columns(2)
    if t_op == T["gasto"]:
        sub_t = c1.selectbox("Frecuencia", ["Vencimiento", "Diario"])
        f_cat = c1.selectbox(T["cat_label"], CAT_VENC if sub_t == "Vencimiento" else CAT_DIARIO)
        f_fec = c2.date_input("Fecha") if sub_t == "Vencimiento" else datetime.now().date()
        f_cta = default_cta 
    else:
        f_cta = c1.selectbox("Destino (Cuenta)", CUENTAS_LISTA)
        f_fec = datetime.now().date()
        f_cat = "INGRESO"
    raw_mto = st.text_input(T["monto_label"], key=f"m_{st.session_state.get('form_tick', 0)}")
    f_des = st.text_input(T["desc_label"], key=f"d_{st.session_state.get('form_tick', 0)}").upper() # Manteniendo mayúsculas consistentemente
    if st.button(T["save_reg"], use_container_width=True):
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        if clean_mto.isdigit() and int(clean_mto) > 0:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, f_cta, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            st.session_state.form_tick = st.session_state.get('form_tick', 0) + 1
            st.rerun()

# --- PESTAÑA AHORROS ---
with tabs[1]:
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.subheader("⬆️ Ahorrar")
        acc_ori = st.selectbox("De:", CUENTAS_LISTA, key="ao")
        mto_dep = st.number_input("Monto:", min_value=0.0, step=1000.0, key="md")
        if st.button("💰 DEPOSITAR"):
            if mto_dep > 0:
                mov = pd.DataFrame([[str(datetime.now().date()), "DEPOSITO AHORRO", acc_ori, "AHORRO", "TRASPASO", int(mto_dep)]], columns=df_mov.columns)
                pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False); st.rerun()
    with col_a2:
        st.subheader("⬇️ Retirar")
        acc_des = st.selectbox("Para:", CUENTAS_LISTA, key="ad")
        mto_ret = st.number_input("Monto:", min_value=0.0, step=1000.0, key="mr")
        if st.button("💸 RETIRAR"):
            if mto_ret > 0:
                mov = pd.DataFrame([[str(datetime.now().date()), "RETIRO AHORRO", acc_des, "AHORRO", "RETIRO", int(mto_ret)]], columns=df_mov.columns)
                pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False); st.rerun()

# --- PESTAÑA RESUMEN ---
with tabs[2]:
    if not df_mov.empty and st.button(T["undo_btn"]):
        df_mov[:-1].to_csv(FILE_DB, index=False); st.rerun()
    
    st.metric(T["cap_total"], f"${total_capital:,.0f}")
    c_aho, c_meta = st.columns(2)
    c_aho.metric(T["aho_saldo"], f"${saldos['Ahorro']:,.0f}")
    c_meta.metric("Diferencia Meta", f"${(saldos['Ahorro'] - st.session_state.meta_dinamica):,.0f}")
    
    st.divider()
    
    # Lógica de Escalas Basadas en el Análisis del Video
    st.subheader("🎯 Análisis y Distribución de Escalas (Modelo del Video)")
    
    # Porcentajes Teóricos sugeridos
    pct_ahorro = 0.10
    pct_vivienda = 0.30
    pct_financiero = 0.15
    pct_basicos = 0.20
    pct_variables = 0.25

    # Redistribución si NO paga vivienda
    if PAGA_VIVIENDA == "No":
        pct_vivienda = 0.0
        pct_ahorro += 0.15      # +15% ahorro
        pct_variables += 0.15   # +15% variables
        st.info("💡 Optimización: Al no pagar arriendo o dividendo, se reasigna el 30% disponible sumando 15% a tu Ahorro y 15% a tus Gastos Variables.")
    else:
        st.info("📋 Distribución estándar activa: Incluye el tope máximo sugerido de 30% para gastos de vivienda.")

    # Montos ideales sugeridos según el Ingreso Neto real
    monto_ideal_ahorro = INGRESO_NETO * pct_ahorro
    monto_ideal_vivienda = INGRESO_NETO * pct_vivienda
    monto_ideal_financiero = INGRESO_NETO * pct_financiero
    monto_ideal_basicos = INGRESO_NETO * pct_basicos
    monto_ideal_variables = INGRESO_NETO * pct_variables

    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.write("**Tus Límites Sugeridos:**")
        datos_tabla = {
            "Categoría": ["Ahorro (Mínimo)", "Vivienda (Máximo)", "Gastos Financieros / Deudas", "Gastos Básicos", "Gastos Variables"],
            "Porcentaje": [f"{int(pct_ahorro*100)}%", f"{int(pct_vivienda*100)}%", f"{int(pct_financiero*100)}%", f"{int(pct_basicos*100)}%", f"{int(pct_variables*100)}%"],
            "Monto Sugerido": [f"${int(monto_ideal_ahorro):,}", f"${int(monto_ideal_vivienda):,}", f"${int(monto_financiero := monto_ideal_financiero):,}", f"${int(monto_ideal_basicos):,}", f"${int(monto_ideal_variables):,}"]
        }
        st.table(pd.DataFrame(datos_tabla))

    with col_t2:
        st.write("**Diagnóstico con Datos Iniciales:**")
        st.write(f"**Ingreso Declarado:** ${INGRESO_NETO:,.0f}")
        if PAGA_VIVIENDA == "Sí":
            if MONTO_VIVIENDA > monto_ideal_vivienda:
                st.warning(f"⚠️ Vivienda (${MONTO_VIVIENDA:,.0f}) supera el 30% recomendado (${monto_ideal_vivienda:,.0f}).")
            else:
                st.success(f"✅ Gasto en vivienda (${MONTO_VIVIENDA:,.0f}) bajo el límite.")
        
        if GASTOS_FINANCIEROS > monto_ideal_financiero:
            st.error(f"🚨 Deudas (${GASTOS_FINANCIEROS:,.0f}) exceden el 15% recomendado (${monto_ideal_financiero:,.0f}).")
        else:
            st.success(f"✅ Gastos financieros bajo control.")
            
        if GASTOS_BASICOS > monto_ideal_basicos:
            st.warning(f"⚠️ Gastos básicos (${GASTOS_BASICOS:,.0f}) son mayores al 20% estimado.")

    st.divider()
    st.subheader("📊 Análisis por Categoría Real")
    
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    if not df_gastos.empty:
        resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum().sort_values(ascending=False)
        for cat, monto in resumen_cat.items():
            col_c, col_m = st.columns([3, 1])
            col_c.write(f"**{cat}**")
            col_m.write(f"${monto:,.0f}")
            st.progress(min(monto / resumen_cat.sum(), 1.0))
        
        max_cat = resumen_cat.index[0]
        st.warning(f"⚠️ **Alerta de Gasto:** Tu mayor fuga de dinero está en **{max_cat}** con ${resumen_cat[max_cat]:,.0f}")
    else:
        st.info("Aún no hay gastos registrados para analizar.")

    st.divider()
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- PESTAÑA IA ---
with tabs[3]:
    api_key = st.secrets.get("GROQ_API_KEY")
    if api_key:
        client = Groq(api_key=api_key)
        gastos_texto = ""
        if not df_gastos.empty:
            resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum()
            gastos_texto = resumen_cat.to_string()
        
        st.subheader("🕵️ Análisis Inteligente")
        if st.button("✨ GENERAR CONSEJO PROACTIVO"):
            ctx = f"Usuario: {USER_NAME}. Capital: {total_capital}. Ahorro: {saldos['Ahorro']}. Meta: {st.session_state.meta_dinamica}. Gastos por categoría: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Eres un analista financiero. Analiza los gastos y da un consejo específico para alcanzar la meta de ahorro. Sé breve y directo."},
                          {"role": "user", "content": ctx}],
                model="llama-3.1-8b-instant")
            st.success(chat.choices[0].message.content)
            
        user_ask = st.text_input(f"O hazle una pregunta directa:")
        if user_ask:
            ctx = f"Capital: {total_capital}, Ahorro: {saldos['Ahorro']}, Meta: {st.session_state.meta_dinamica}. Gastos: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Asesor financiero breve."},
                          {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            st.info(chat.choices[0].message.content)
