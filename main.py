import streamlit as st
import pandas as pd
from datetime import datetime
import os
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

# --- LISTA OFICIAL DE BANCOS DE CHILE ---
BANCOS_CHILE = [
    "001 - Banco de Chile",
    "012 - BancoEstado (Banco del Estado de Chile)",
    "014 - Scotiabank Chile",
    "016 - Banco Bci (Banco de Crédito e Inversiones)",
    "028 - Banco BICE",
    "037 - Banco Santander Chile",
    "039 - Banco Itaú",
    "049 - Banco Security",
    "051 - Banco Falabella",
    "053 - Banco Ripley",
    "055 - Banco Consorcio",
    "009 - Banco Internacional",
    "672 - Coopeuch",
    "730 - Tenpo Prepago",
    "729 - Prepago Los Héroes",
    "732 - Tapp (Prepago Los Andes)",
    "031 - HSBC Bank Chile",
    "059 - Banco BTG Pactual Chile",
    "041 - JP Morgan Chase Bank",
    "045 - China Construction Bank"
]

# --- TEXTOS TRADUCCIONES ---
TEXTS = {
    "es": {
        "config_title": "🚀 Configuración Inicial",
        "name_label": "¿Cómo te llamas?",
        "meta_label": "Meta de ahorro mensual ($)",
        "save_config": "Guardar Configuración Inicial",
        "reset_btn": "🚨 Reiniciar Sistema",
        "tab_reg": "📝 BITÁCORA DIARIA (REGISTRO)",
        "tab_res": "📊 RESUMEN Y ANÁLISIS",
        "tab_ia": "🕵️ ANALISTA IA",
        "type_op": "Tipo de Operación",
        "gasto": "GASTO",
        "ingreso": "INGRESO",
        "cat_label": "Categoría del Gasto",
        "monto_label": "Monto $ (Pesos Chilenos sin puntos)",
        "desc_label": "Descripción / Detalle del movimiento",
        "save_reg": "💾 GUARDAR EN BITÁCORA",
        "undo_btn": "🔙 DESHACER ÚLTIMO REGISTRO",
        "cap_total": "CAPITAL TOTAL EN CUENTAS",
    }
}
T = TEXTS["es"]

# --- BOTÓN DE REINICIAR / BORRAR (Barra Lateral) ---
st.sidebar.title("🛠️ Administración")
if st.sidebar.button(T["reset_btn"], use_container_width=True):
    if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- CARGAR CONFIGURACIÓN ---
if os.path.exists(FILE_CONFIG):
    try:
        config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
        USER_NAME = config["nombre"]
        INGRESO_NETO = int(config.get("ingreso_neto", 0))
        
        if "meta_dinamica" not in st.session_state:
            st.session_state.meta_dinamica = float(config["meta"])
            
        CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split("|")]
        CATEGORIAS_SISTEMA = ["VIVIENDA (CUENTAS BASICAS)", "CUOTAS DE COMPRAS", "SERVICIOS PERSONALES", "GASTOS DIARIOS"]
    except:
        st.error("Error cargando la configuración.")
        if st.button("Reconfigurar"): 
            if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
            st.rerun()
        st.stop()
else:
    st.title(T["config_title"])
    st.write("Configura tu perfil de control de gastos en Pesos Chilenos (valores sin decimales).")
    
    if "filas_vivienda" not in st.session_state: st.session_state.filas_vivienda = 1
    if "filas_cuotas" not in st.session_state: st.session_state.filas_cuotas = 1
    if "filas_servicios" not in st.session_state: st.session_state.filas_servicios = 1

    with st.form("config_form"):
        nombre = st.text_input(T["name_label"]).upper()
        ingreso_neto = st.number_input("Ingresos Netos Mensuales ($):", min_value=0, step=10000, value=0)
        meta = st.number_input(T["meta_label"], min_value=0, step=10000, value=0)
        
        st.subheader("🏦 Cuentas Bancarias")
        bancos_seleccionados = st.multiselect("Selecciona tus bancos e instituciones:", BANCOS_CHILE)
        
        tipos_cuentas = {}
        if bancos_seleccionados:
            st.write("*Define el tipo de cuenta para cada institución seleccionada:*")
            for bco in bancos_seleccionados:
                tipos_cuentas[bco] = st.selectbox(f"Tipo para {bco}:", ["Vista", "Corriente"], key=f"tipo_{bco}")
        
        st.divider()
        st.subheader("1. VIVIENDA (CUENTAS BÁSICAS)")
        gastos_vivienda_items = []
        for i in range(st.session_state.filas_vivienda):
            c1, c2 = st.columns([2, 1])
            n_g = c1.text_input(f"Descripción Gasto {i+1} (ej: Arriendo, Luz)", key=f"viv_n_{i}").upper()
            m_g = c2.number_input(f"Monto $", min_value=0, step=1000, key=f"viv_m_{i}", value=0)
            if n_g and m_g > 0: gastos_vivienda_items.append((n_g, m_g))
            
        st.subheader("2. CUOTAS DE COMPRAS")
        gastos_cuotas_items = []
        for i in range(st.session_state.filas_cuotas):
            c1, c2 = st.columns([2, 1])
            n_g = c1.text_input(f"Descripción Gasto {i+1} (ej: Tarjeta CMR, Crédito)", key=f"cuo_n_{i}").upper()
            m_g = c2.number_input(f"Monto $", min_value=0, step=1000, key=f"cuo_m_{i}", value=0)
            if n_g and m_g > 0: gastos_cuotas_items.append((n_g, m_g))

        st.subheader("3. SERVICIOS PERSONALES")
        gastos_servicios_items = []
        for i in range(st.session_state.filas_servicios):
            c1, c2 = st.columns([2, 1])
            n_g = c1.text_input(f"Descripción Gasto {i+1} (ej: Netflix, Gimnasio)", key=f"ser_n_{i}").upper()
            m_g = c2.number_input(f"Monto $", min_value=0, step=1000, key=f"ser_m_{i}", value=0)
            if n_g and m_g > 0: gastos_servicios_items.append((n_g, m_g))

        st.write("💡 *Si necesitas agregar más filas de gastos a los bloques, usa los botones de abajo antes de guardar.*")
        guardar_todo = st.form_submit_button(T["save_config"])
        
    c_b1, c_b2, c_b3 = st.columns(3)
    if c_b1.button("➕ Más filas en Vivienda"): st.session_state.filas_vivienda += 1; st.rerun()
    if c_b2.button("➕ Más filas en Cuotas"): st.session_state.filas_cuotas += 1; st.rerun()
    if c_b3.button("➕ Más filas en Servicios"): st.session_state.filas_servicios += 1; st.rerun()

    if guardar_todo:
        if nombre and ingreso_neto > 0 and bancos_seleccionados:
            cuentas_procesadas = [f"{bco} ({tipos_cuentas[bco]})" for bco in bancos_seleccionados]
            string_cuentas = " | ".join(cuentas_procesadas)
            
            pd.DataFrame([{
                "nombre": nombre, 
                "ingreso_neto": int(ingreso_neto),
                "meta": int(meta), 
                "cuentas": string_cuentas
            }]).to_csv(FILE_CONFIG, index=False)
            
            registros_iniciales = []
            fecha_hoy = str(datetime.now().date())
            
            for n, m in gastos_vivienda_items:
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_procesadas[0], "VIVIENDA (CUENTAS BASICAS)", n, int(m)])
            for n, m in gastos_cuotas_items:
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_procesadas[0], "CUOTAS DE COMPRAS", n, int(m)])
            for n, m in gastos_servicios_items:
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_procesadas[0], "SERVICIOS PERSONALES", n, int(m)])
                
            df_inicial = pd.DataFrame(registros_iniciales, columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
            df_inicial.to_csv(FILE_DB, index=False)
            st.rerun()
        else:
            st.error("Por favor completa los datos básicos (Nombre, Ingreso) y selecciona al menos una cuenta bancaria.")
    st.stop()

# --- CARGAR BASE DE DATOS TRAS EL SETUP ---
df_mov = pd.read_csv(FILE_DB)

# --- CÁLCULOS DE SALDOS ---
saldos = {cta: 0 for cta in CUENTAS_LISTA}
for _, row in df_mov.iterrows():
    try:
        m = int(row['MONTO'])
        tipo, cta = row['TIPO'], row['CUENTA']
        if tipo == "INGRESO" and cta in saldos: saldos[cta] += m
        elif tipo == "GASTO" and cta in saldos: saldos[cta] -= m
    except: continue
total_capital = sum(saldos[c] for c in CUENTAS_LISTA)

# --- INTERFAZ PANEL DE CONTROL ---
st.title(f"📊 Control de Gastos - Perfil: {USER_NAME}")
st.session_state.meta_dinamica = st.number_input("🎯 Meta de Ahorro Actual:", value=st.session_state.meta_dinamica, step=10000.0)

tabs = st.tabs([T["tab_reg"], T["tab_res"], T["tab_ia"]])

# --- PESTAÑA 1: BITÁCORA DIARIA (REGISTRO) ---
with tabs[0]:
    st.subheader("🖋️ Registrar Movimiento del Día")
    t_op = st.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    c1, c2 = st.columns(2)
    
    if t_op == T["gasto"]:
        f_cat = c1.selectbox(T["cat_label"], CATEGORIAS_SISTEMA, index=3) # GASTOS DIARIOS por defecto
        f_cta = c2.selectbox("Pagar desde Cuenta", CUENTAS_LISTA)
        f_fec = datetime.now().date()
    else:
        f_cta = c1.selectbox("Destino del Ingreso", CUENTAS_LISTA)
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

# --- PESTAÑA 2: RESUMEN Y ANÁLISIS ---
with tabs[1]:
    if not df_mov.empty and st.button(T["undo_btn"]):
        df_mov[:-1].to_csv(FILE_DB, index=False); st.rerun()
        
    st.metric(T["cap_total"], f"${total_capital:,.0f}".replace(",", "."))
    
    st.write("**Saldos por Cuenta Declarada:**")
    cc = st.columns(len(CUENTAS_LISTA))
    for idx, cta in enumerate(CUENTAS_LISTA):
        cc[idx].metric(cta, f"${saldos[cta]:,.0f}".replace(",", "."))
        
    st.divider()
    st.subheader("🎯 Resumen de Gastos por Categorías Fijas")
    
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    if not df_gastos.empty:
        resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum()
        
        col_graf1, col_graf2 = st.columns(2)
        with col_graf1:
            st.write("**Consumo Actual por Categoría:**")
            for cat in CATEGORIAS_SISTEMA:
                monto = resumen_cat.get(cat, 0)
                st.write(f"**{cat}:** ${int(monto):,.0f}".replace(",", "."))
                st.progress(min(monto / (df_gastos["MONTO"].sum() if df_gastos["MONTO"].sum() > 0 else 1), 1.0))
        with col_graf2:
            st.write("**Análisis de Límites:**")
            st.write(f"Tu ingreso mensual de referencia es: **${INGRESO_NETO:,.0f}**".replace(",", "."))
            st.write(f"Tu meta de ahorro mensual establecida es: **${st.session_state.meta_dinamica:,.0f}**".replace(",", "."))
    else:
        st.info("Aún no se registran gastos en el historial.")

    st.divider()
    st.write("**Historial Completo de Movimientos (Bitácora):**")
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- PESTAÑA 3: ANALISTA IA ---
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
            ctx = f"Usuario: {USER_NAME}. Capital: {total_capital}. Ingreso: {INGRESO_NETO}. Meta: {st.session_state.meta_dinamica}. Gastos por categoría: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Eres un analista financiero. Analiza los gastos y da un consejo breve basado en los parámetros de control de gastos. Sé breve y directo."},
                          {"role": "user", "content": ctx}],
                model="llama-3.1-8b-instant")
            st.success(chat.choices[0].message.content)
            
        user_ask = st.text_input(f"O hazle una pregunta directa:")
        if user_ask:
            ctx = f"Capital: {total_capital}, Ingreso: {INGRESO_NETO}, Meta: {st.session_state.meta_dinamica}. Gastos: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Asesor financiero breve."},
                          {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            st.info(chat.choices[0].message.content)
