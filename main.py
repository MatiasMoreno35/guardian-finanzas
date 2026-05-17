import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Control de Gastos", page_icon="📊", layout="wide")

# --- LÓGICA DE RUTAS Y MULTIUSUARIO ---
user_id = st.query_params.get("user", "comun")
base_path = os.getcwd()
if not os.access(base_path, os.W_OK):
    base_path = "/tmp"

if not os.path.exists(base_path):
    os.makedirs(base_path, exist_ok=True)

FILE_DB = os.path.join(base_path, f"movimientos_{user_id}.csv")
FILE_CONFIG = os.path.join(base_path, f"config_{user_id}.csv")

# --- TRADUCCIONES Y TEXTOS ---
TEXTS = {
    "es": {
        "config_title": "🚀 Configuración Inicial",
        "name_label": "¿Cómo te llamas?",
        "meta_label": "Meta de ahorro mensual ($)",
        "ctas_label": "Tus cuentas de origen (ej: Efectivo, CuentaRut, Débito)",
        "save_config": "Guardar Perfil y Calcular Escalas",
        "reset_btn": "🚨 Reiniciar Sistema",
        "tab_reg": "📝 REGISTRO DE GASTOS",
        "tab_res": "📊 RESUMEN Y ESCALAS",
        "tab_ia": "🕵️ ANALISTA IA",
        "type_op": "Tipo",
        "gasto": "GASTO",
        "ingreso": "INGRESO",
        "cat_label": "Categoría (Modelo del Video)",
        "monto_label": "Monto $ (Sin decimales)",
        "desc_label": "Descripción / Detalle",
        "save_reg": "💾 GUARDAR REGISTRO",
        "undo_btn": "🔙 DESHACER ÚLTIMO REGISTRO",
        "cap_total": "CAPITAL TOTAL DISPONIBLE",
    }
}

T = TEXTS["es"]

# --- BOTÓN DE REINICIAR / BORRAR (Barra Lateral) ---
st.sidebar.title("🛠️ Administración")
if st.sidebar.button(T["reset_btn"], use_container_width=True):
    if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    st.rerun()

# --- CARGAR CONFIGURACIÓN ---
if os.path.exists(FILE_CONFIG):
    try:
        config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
        USER_NAME = config["nombre"]
        
        # Carga de variables nativas en formato entero (Sin decimales)
        INGRESO_NETO = int(config.get("ingreso_neto", 0))
        META_AHORRO = int(config.get("meta", 0))
        CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split(",")]
        PAGA_VIVIENDA = config.get("paga_vivienda", "No")
        MONTO_VIVIENDA = int(config.get("monto_vivienda", 0))
        GASTOS_FINANCIEROS = int(config.get("gastos_financieros", 0))
        GASTOS_BASICOS = int(config.get("gastos_basicos", 0))
        
        # Categorías fijas del video
        CATEGORIAS_VIDEO = ["Ahorro", "Vivienda", "Gastos Financieros", "Gastos Básicos", "Gastos Variables"]
    except:
        st.error("Error cargando la configuración.")
        if st.button("Reconfigurar"): 
            if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
            st.rerun()
        st.stop()
else:
    st.title(T["config_title"])
    st.write("Configura tu perfil inicial con valores enteros (Pesos Chilenos).")
    with st.form("config_form"):
        nombre = st.text_input(T["name_label"]).upper()
        ingreso_neto = st.number_input("Ingreso Neto Mensual ($):", min_value=0, step=10000, value=0)
        meta = st.number_input(T["meta_label"], min_value=0, step=10000, value=0)
        nombres_ctas = st.text_input(T["ctas_label"])
        
        st.subheader("🏠 Situación de Vivienda")
        paga_vivienda = st.radio("¿Pagas actualmente arriendo o dividendo?", ["Sí", "No"])
        monto_vivienda = st.number_input("Monto mensual de tu Vivienda ($):", min_value=0, step=10000, value=0)

        st.subheader("💳 Otros Gastos Mensuales Fijos")
        gastos_financieros = st.number_input("Gastos Financieros / Deudas ($):", min_value=0, step=5000, value=0)
        gastos_basicos = st.number_input("Gastos Básicos Estimados (Comida, Servicios) ($):", min_value=0, step=5000, value=0)
        
        if st.form_submit_button(T["save_config"]):
            if all([nombre, nombres_ctas]) and ingreso_neto > 0:
                pd.DataFrame([{
                    "nombre": nombre, 
                    "ingreso_neto": int(ingreso_neto),
                    "meta": int(meta), 
                    "cuentas": nombres_ctas, 
                    "paga_vivienda": paga_vivienda,
                    "monto_vivienda": int(monto_vivienda) if paga_vivienda == "Sí" else 0,
                    "gastos_financieros": int(gastos_financieros),
                    "gastos_basicos": int(gastos_basicos)
                }]).to_csv(FILE_CONFIG, index=False)
                st.rerun()
            else:
                st.error("Por favor completa los campos obligatorios. El ingreso debe ser mayor a 0.")
    st.stop()

# --- BASE DE DATOS ---
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
df_mov = pd.read_csv(FILE_DB)

# --- CÁLCULOS DE SALDOS ---
default_cta = CUENTAS_LISTA[0]
saldos = {cta: 0 for cta in CUENTAS_LISTA}
for _, row in df_mov.iterrows():
    try:
        m = int(row['MONTO'])
        tipo, cta = row['TIPO'], row['CUENTA']
        if tipo == "INGRESO" and cta in saldos: saldos[cta] += m
        elif tipo == "GASTO" and cta in saldos: saldos[cta] -= m
    except: continue
total_capital = sum(saldos[c] for c in CUENTAS_LISTA)

# --- INTERFAZ ---
st.title(f"📊 Control de Gastos - {USER_NAME}")

# Tabs mutados (Se quitó la pestaña de Ahorros por el momento)
tabs = st.tabs([T["tab_reg"], T["tab_res"], T["tab_ia"]])

# --- PESTAÑA REGISTRO ---
with tabs[0]:
    t_op = st.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    c1, c2 = st.columns(2)
    
    if t_op == T["gasto"]:
        f_cat = c1.selectbox(T["cat_label"], CATEGORIAS_VIDEO)
        f_cta = c2.selectbox("Pagar desde (Cuenta)", CUENTAS_LISTA)
        f_fec = datetime.now().date()
    else:
        f_cta = c1.selectbox("Destino (Cuenta)", CUENTAS_LISTA)
        f_cat = "INGRESO"
        f_fec = datetime.now().date()
        
    raw_mto = st.text_input(T["monto_label"], key=f"m_{st.session_state.get('form_tick', 0)}")
    f_des = st.text_input(T["desc_label"], key=f"d_{st.session_state.get('form_tick', 0)}").upper()
    
    if st.button(T["save_reg"], use_container_width=True):
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        if clean_mto.isdigit() and int(clean_mto) > 0:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, f_cta, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            st.session_state.form_tick = st.session_state.get('form_tick', 0) + 1
            st.rerun()

# --- PESTAÑA RESUMEN Y ESCALAS ---
with tabs[1]:
    if not df_mov.empty and st.button(T["undo_btn"]):
        df_mov[:-1].to_csv(FILE_DB, index=False); st.rerun()
    
    st.metric(T["cap_total"], f"${total_capital:,.0f}".replace(",", "."))
    
    st.divider()
    st.subheader("🎯 Comparativa de Distribución (Modelo del Video)")
    
    # Porcentajes Teóricos sugeridos
    pct_ahorro = 0.10
    pct_vivienda = 0.30
    pct_financiero = 0.15
    pct_basicos = 0.20
    pct_variables = 0.25

    # Redistribución si NO paga vivienda (30% se divide 15% ahorro y 15% variables)
    if PAGA_VIVIENDA == "No":
        pct_vivienda = 0.0
        pct_ahorro += 0.15
        pct_variables += 0.15
        st.info("💡 Optimización Dinámica: Al no registrar gastos de vivienda, se reasignó un 15% adicional a tu capacidad de Ahorro y un 15% a tus Gastos Variables.")
    else:
        st.info("📋 Distribución estándar activa. Se asigna un tope máximo del 30% para gastos de vivienda.")

    # Montos ideales calculados (Casteados a entero para evitar decimales)
    monto_ideal_ahorro = int(INGRESO_NETO * pct_ahorro)
    monto_ideal_vivienda = int(INGRESO_NETO * pct_vivienda)
    monto_ideal_financiero = int(INGRESO_NETO * pct_financiero)
    monto_ideal_basicos = int(INGRESO_NETO * pct_basicos)
    monto_ideal_variables = int(INGRESO_NETO * pct_variables)

    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.write("**Límites Ideales Basados en tus Ingresos:**")
        datos_tabla = {
            "Categoría": ["Ahorro (Mínimo)", "Vivienda (Máximo)", "Gastos Financieros / Deudas", "Gastos Básicos", "Gastos Variables"],
            "Porcentaje": [f"{int(pct_ahorro*100)}%", f"{int(pct_vivienda*100)}%", f"{int(pct_financiero*100)}%", f"{int(pct_basicos*100)}%", f"{int(pct_variables*100)}%"],
            "Monto Ideal Mensual": [
                f"${monto_ideal_ahorro:,.0f}".replace(",", "."),
                f"${monto_ideal_vivienda:,.0f}".replace(",", "."),
                f"${monto_ideal_financiero:,.0f}".replace(",", "."),
                f"${monto_ideal_basicos:,.0f}".replace(",", "."),
                f"${monto_ideal_variables:,.0f}".replace(",", ".")
            ]
        }
        st.table(pd.DataFrame(datos_tabla))

    with col_t2:
        st.write("**Diagnóstico con Datos Declarados:**")
        st.write(f"**Ingreso Neto Mensual:** ${INGRESO_NETO:,.0f}".replace(",", "."))
        
        if PAGA_VIVIENDA == "Sí":
            if MONTO_VIVIENDA > monto_ideal_vivienda:
                st.warning(f"⚠️ Tu vivienda (${MONTO_VIVIENDA:,.0f}) supera el 30% recomendado (${monto_ideal_vivienda:,.0f}).")
            else:
                st.success(f"✅ Gasto en vivienda (${MONTO_VIVIENDA:,.0f}) equilibrado.")
        
        if GASTOS_FINANCIEROS > monto_ideal_financiero:
            st.error(f"🚨 Deudas actuales (${GASTOS_FINANCIEROS:,.0f}) exceden el 15% límite recomendación (${monto_ideal_financiero:,.0f}).")
        else:
            st.success(f"✅ Carga de deuda bajo control.")
            
        if GASTOS_BASICOS > monto_ideal_basicos:
            st.warning(f"⚠️ Gastos básicos (${GASTOS_BASICOS:,.0f}) superan el 20% estimado.")

    st.divider()
    st.subheader("📊 Historial General de Gastos")
    
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    if not df_gastos.empty:
        resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum().sort_values(ascending=False)
        for cat, monto in resumen_cat.items():
            col_c, col_m = st.columns([3, 1])
            col_c.write(f"**{cat}**")
            col_m.write(f"${int(monto):,.0f}".replace(",", "."))
            st.progress(min(monto / resumen_cat.sum(), 1.0))
    else:
        st.info("Aún no hay transacciones en esta simulación.")

    st.divider()
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- PESTAÑA IA ---
with tabs[2]:
    api_key = st.secrets.get("GROQ_API_KEY")
    if api_key:
        client = Groq(api_key=api_key)
        gastos_texto = ""
        if not df_gastos.empty:
            resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum()
            gastos_texto = resumen_cat.to_string()
        
        st.subheader("🕵️ Análisis Inteligente")
        if st.button("✨ GENERAR CONSEJO PROACTIVO"):
            ctx = f"Usuario: {USER_NAME}. Capital: {total_capital}. Ingreso: {INGRESO_NETO}. Gastos por categoría: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Eres un analista financiero. Analiza los gastos y da un consejo breve basado en las escalas del video."},
                          {"role": "user", "content": ctx}],
                model="llama-3.1-8b-instant")
            st.success(chat.choices[0].message.content)
