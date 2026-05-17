import streamlit as st
import pandas as pd
from datetime import datetime
import os
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

# --- TRADUCCIONES ---
TEXTS = {
    "es": {
        "config_title": "🚀 Configuración Inicial",
        "name_label": "¿Cómo te llamas?",
        "meta_label": "Meta de ahorro mensual",
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

# --- CONTROL DE IDIOMA EN LA BARRA LATERAL ---
if "idioma" not in st.session_state:
    st.session_state.idioma = "es"

st.sidebar.title("🌐 Idioma / Language")
st.session_state.idioma = st.sidebar.selectbox("Seleccione Idioma:", ["es"], index=0)
T = TEXTS[st.session_state.idioma]

# --- BOTÓN DE REINICIAR / BORRAR ---
st.sidebar.title("🛠️ Administración")
if st.sidebar.button(T["reset_btn"], use_container_width=True):
    if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()

# --- FUNCIÓN PARA FORMATEAR EN TIEMPO REAL (PESOS CHILENOS) ---
def format_clp(val_str):
    clean = "".join(filter(str.isdigit, val_str))
    if clean == "" or clean == "0":
        return "$0"
    return f"${int(clean):,}".replace(",", ".")

def clean_to_int(val_str):
    clean = "".join(filter(str.isdigit, val_str))
    return int(clean) if clean else 0

# --- CARGAR CONFIGURACIÓN ---
if os.path.exists(FILE_CONFIG):
    try:
        config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
        USER_NAME = config["nombre"]
        if "meta_dinamica" not in st.session_state:
            st.session_state.meta_dinamica = int(config["meta"])
        CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split("|")]
        CATEGORIAS_SISTEMA = ["VIVIENDA (CUENTAS BASICAS)", "CUOTAS DE COMPRAS", "SERVICIOS PERSONALES", "GASTOS DIARIOS"]
        INGRESO_NETO = int(config.get("ingreso_neto", 0))
    except:
        st.error("Error cargando config.")
        if st.button("Reconfigurar"): 
            if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
            st.rerun()
        st.stop()
else:
    st.title(T["config_title"])
    st.write("Configura tu perfil de control de gastos en Pesos Chilenos sin decimales.")
    
    # Inicialización de listas y ticks de limpieza para los popovers
    if "lista_vivienda" not in st.session_state: st.session_state.lista_vivienda = []
    if "lista_cuotas" not in st.session_state: st.session_state.lista_cuotas = []
    if "lista_servicios" not in st.session_state: st.session_state.lista_servicios = []
    
    if "tick_viv" not in st.session_state: st.session_state.tick_viv = 0
    if "tick_cuo" not in st.session_state: st.session_state.tick_cuo = 0
    if "tick_ser" not in st.session_state: st.session_state.tick_ser = 0

    nombre = st.text_input(T["name_label"]).upper()
    
    # Inputs con formateador visual nativo en CLP sin decimales
    raw_ing = st.text_input("Ingresos Netos Mensuales $:", value="$0")
    formatted_ing = format_clp(raw_ing)
    if raw_ing != formatted_ing:
        st.text_input("Ingresos Netos Mensuales $:", value=formatted_ing, key="ing_input")
        ingreso_neto = clean_to_int(formatted_ing)
    else:
        ingreso_neto = clean_to_int(raw_ing)
        
    raw_meta = st.text_input(T["meta_label"] + " $:", value="$0")
    formatted_meta = format_clp(raw_meta)
    if raw_meta != formatted_meta:
        st.text_input(T["meta_label"] + " $:", value=formatted_meta, key="meta_input")
        meta = clean_to_int(formatted_meta)
    else:
        meta = clean_to_int(raw_meta)
    
    st.subheader("🏦 Cuentas Bancarias")
    bancos_seleccionados = st.multiselect("Selecciona tus bancos e instituciones:", BANCOS_CHILE)
    
    cuentas_finales = []
    if bancos_seleccionados:
        st.write("*Define el tipo de cuenta para cada institución seleccionada:*")
        for bco in bancos_seleccionados:
            tipo_cta = st.selectbox(f"Tipo para {bco}:", ["Vista", "Corriente"], key=f"tipo_{bco}")
            cuentas_finales.append(f"{bco} ({tipo_cta})")

    st.divider()
    
    # --- 1. VIVIENDA (CUENTAS BÁSICAS) ---
    st.subheader("1. VIVIENDA (CUENTAS BASICAS)")
    with st.popover("➕ Agregar gasto"):
        st.write("**Nuevo Gasto de Vivienda / Básica**")
        v_nom = st.text_input("Nombre del gasto (ej: Arriendo, Luz):", key=f"v_nom_{st.session_state.tick_viv}").upper()
        v_mto_raw = st.text_input("Monto $:", value="$0", key=f"v_raw_{st.session_state.tick_viv}")
        st.session_state[f"v_raw_{st.session_state.tick_viv}"] = format_clp(v_mto_raw)
        v_mto = clean_to_int(st.session_state[f"v_raw_{st.session_state.tick_viv}"])
        
        v_venc_check = st.checkbox("¿Tiene vencimiento?", key=f"v_vc_{st.session_state.tick_viv}")
        v_venc = st.date_input("Fecha de Vencimiento", datetime.now().date(), key=f"v_fec_{st.session_state.tick_viv}") if v_venc_check else "No"
        
        if st.button("Confirmar Gasto Vivienda"):
            if v_nom and v_mto > 0:
                st.session_state.lista_vivienda.append({"desc": v_nom, "monto": v_mto, "venc": str(v_venc)})
                st.session_state.tick_viv += 1  # Esto destruye los widgets viejos y los fuerza a vaciarse ($0)
                st.rerun()
                
    if st.session_state.lista_vivienda:
        st.dataframe(pd.DataFrame(st.session_state.lista_vivienda), use_container_width=True)

    # --- 2. CUOTAS DE COMPRAS ---
    st.subheader("2. CUOTAS DE COMPRAS")
    with st.popover("➕ Agregar gasto"):
        st.write("**Nuevo Gasto de Cuotas**")
        c_nom = st.text_input("Nombre del gasto (ej: Tarjeta CMR, Crédito):", key=f"c_nom_{st.session_state.tick_cuo}").upper()
        c_mto_raw = st.text_input("Monto $:", value="$0", key=f"c_raw_{st.session_state.tick_cuo}")
        st.session_state[f"c_raw_{st.session_state.tick_cuo}"] = format_clp(c_mto_raw)
        c_mto = clean_to_int(st.session_state[f"c_raw_{st.session_state.tick_cuo}"])
        
        c_venc_check = st.checkbox("¿Tiene vencimiento?", key=f"c_vc_{st.session_state.tick_cuo}")
        c_venc = st.date_input("Fecha de Vencimiento", datetime.now().date(), key=f"c_fec_{st.session_state.tick_cuo}") if c_venc_check else "No"
        
        if st.button("Confirmar Gasto Cuota"):
            if c_nom and c_mto > 0:
                st.session_state.lista_cuotas.append({"desc": c_nom, "monto": c_mto, "venc": str(c_venc)})
                st.session_state.tick_cuo += 1
                st.rerun()
                
    if st.session_state.lista_cuotas:
        st.dataframe(pd.DataFrame(st.session_state.lista_cuotas), use_container_width=True)

    # --- 3. SERVICIOS PERSONALES ---
    st.subheader("3. SERVICIOS PERSONALES")
    with st.popover("➕ Agregar gasto"):
        st.write("**Nuevo Servicio Personal**")
        s_nom = st.text_input("Nombre del gasto (ej: Netflix, Gimnasio):", key=f"s_nom_{st.session_state.tick_ser}").upper()
        s_mto_raw = st.text_input("Monto $:", value="$0", key=f"s_raw_{st.session_state.tick_ser}")
        st.session_state[f"s_raw_{st.session_state.tick_ser}"] = format_clp(s_mto_raw)
        s_mto = clean_to_int(st.session_state[f"s_raw_{st.session_state.tick_ser}"])
        
        s_venc_check = st.checkbox("¿Tiene vencimiento?", key=f"s_vc_{st.session_state.tick_ser}")
        s_venc = st.date_input("Fecha de Vencimiento", datetime.now().date(), key=f"s_fec_{st.session_state.tick_ser}") if s_venc_check else "No"
        
        if st.button("Confirmar Gasto Servicio"):
            if s_nom and s_mto > 0:
                st.session_state.lista_servicios.append({"desc": s_nom, "monto": s_mto, "venc": str(s_venc)})
                st.session_state.tick_ser += 1
                st.rerun()
                
    if st.session_state.lista_servicios:
        st.dataframe(pd.DataFrame(st.session_state.lista_servicios), use_container_width=True)

    st.divider()
    
    if st.button("💾 GUARDAR TODO E INICIAR SISTEMA", use_container_width=True):
        if nombre and ingreso_neto > 0 and cuentas_finales:
            string_cuentas = " | ".join(cuentas_finales)
            
            pd.DataFrame([{
                "nombre": nombre, 
                "ingreso_neto": int(ingreso_neto),
                "meta": int(meta), 
                "cuentas": string_cuentas,
                "idioma": "es"
            }]).to_csv(FILE_CONFIG, index=False)
            
            registros_iniciales = []
            fecha_hoy = str(datetime.now().date())
            
            for item in st.session_state.lista_vivienda:
                desc_final = f"{item['desc']} (Vence: {item['venc']})" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "VIVIENDA (CUENTAS BASICAS)", desc_final, item['monto']])
                
            for item in st.session_state.lista_cuotas:
                desc_final = f"{item['desc']} (Vence: {item['venc']})" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "CUOTAS DE COMPRAS", desc_final, item['monto']])
                
            for item in st.session_state.lista_servicios:
                desc_final = f"{item['desc']} (Vence: {item['venc']})" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "SERVICIOS PERSONALES", desc_final, item['monto']])
                
            df_inicial = pd.DataFrame(registros_iniciales, columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
            df_inicial.to_csv(FILE_DB, index=False)
            st.rerun()
        else:
            st.error("Asegúrate de llenar el Nombre, Ingresos y tener al menos un Banco con su tipo seleccionado.")
    st.stop()

# --- OPERACIONES DE BASE DE DATOS ---
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
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

# --- INTERFAZ CENTRAL ---
st.title(f"💳 Control de Gastos - {USER_NAME}")

# Formateador también para el input de meta dinámica en la cabecera
raw_meta_din = st.text_input(T["meta_actual"], value=format_clp(str(int(st.session_state.meta_dinamica))))
st.session_state.meta_dinamica = clean_to_int(raw_meta_din)

tabs = st.tabs([T["tab_reg"], T["tab_res"], T["tab_ia"]])

# --- PESTAÑA REGISTRO (CON MONTO FORMATEADO EN VIVO) ---
with tabs[0]:
    st.subheader("🖋️ Registrar Movimiento del Día")
    t_op = st.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    c1, c2 = st.columns(2)
    if t_op == T["gasto"]:
        f_cat = c1.selectbox(T["cat_label"], CATEGORIAS_SISTEMA, index=3) # GASTOS DIARIOS por defecto
        f_cta = c2.selectbox("Pagar desde (Cuenta)", CUENTAS_LISTA)
        f_fec = datetime.now().date()
    else:
        f_cta = c1.selectbox("Destino (Cuenta)", CUENTAS_LISTA)
        f_cat = "INGRESO"
        f_fec = datetime.now().date()
        
    raw_mto_reg = st.text_input(T["monto_label"], value="$0", key=f"m_{st.session_state.get('form_tick', 0)}")
    st.session_state[f"m_{st.session_state.get('form_tick', 0)}"] = format_clp(raw_mto_reg)
    clean_mto = clean_to_int(st.session_state[f"m_{st.session_state.get('form_tick', 0)}"])
    
    f_des = st.text_input(T["desc_label"], key=f"d_{st.session_state.get('form_tick', 0)}").upper()
    
    if st.button(T["save_reg"], use_container_width=True):
        if clean_mto > 0 and f_des:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, f_cta, f_cat, f_des, clean_mto]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            st.session_state.form_tick = st.session_state.get('form_tick', 0) + 1
            st.rerun()

# --- PESTAÑA RESUMEN ---
with tabs[1]:
    if not df_mov.empty and st.button(T["undo_btn"]):
        df_mov[:-1].to_csv(FILE_DB, index=False); st.rerun()
    
    st.metric(T["cap_total"], f"${total_capital:,.0f}".replace(",", "."))
    
    st.write("**Saldos de cuentas actuales:**")
    columnas_ctas = st.columns(len(CUENTAS_LISTA))
    for i, cta in enumerate(CUENTAS_LISTA):
        columnas_ctas[i].metric(cta, f"${saldos[cta]:,.0f}".replace(",", "."))
    
    st.divider()
    st.subheader("📊 Análisis por Categoría")
    
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    if not df_gastos.empty:
        resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum()
        
        for cat in CATEGORIAS_SISTEMA:
            monto = resumen_cat.get(cat, 0)
            col_c, col_m = st.columns([3, 1])
            col_c.write(f"**{cat}**")
            col_m.write(f"${int(monto):,.0f}".replace(",", "."))
            st.progress(min(monto / (df_gastos["MONTO"].sum() if df_gastos["MONTO"].sum() > 0 else 1), 1.0))
    else:
        st.info("Aún no hay gastos registrados para analizar.")

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
            ctx = f"Usuario: {USER_NAME}. Capital: {total_capital}. Ingreso: {INGRESO_NETO}. Meta: {st.session_state.meta_dinamica}. Gastos por categoría: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Eres un analista financiero. Analiza los gastos y da un consejo específico para alcanzar la meta de ahorro. Sé breve y directo en español de Chile sin usar decimales."},
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
