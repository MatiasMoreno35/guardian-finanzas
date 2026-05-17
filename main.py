import streamlit as str_app
import pandas as pd
from datetime import datetime
import calendar
import os
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA ---
str_app.set_page_config(page_title="Smart Wallet", page_icon="💰", layout="wide")

# --- LÓGICA DE RUTAS Y MULTIUSUARIO ---
user_id = str_app.query_params.get("user", "comun")
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
        "meta_label": "Meta de Ahorro Mensual ($)",
        "save_config": "Guardar Configuración",
        "meta_actual": "🎯 Meta de Ahorro Actual:",
        "reset_btn": "🚨 Reiniciar Sistema",
        "tab_reg": "📝 REGISTRO DIARIO",
        "tab_rel": "🔥 GASTO RELEVANTE",
        "tab_res": "📊 RESUMEN",
        "tab_ia": "🕵️ ANALISTA IA",
        "type_op": "Tipo de Movimiento",
        "gasto": "GASTO",
        "ingreso": "INGRESO",
        "monto_label": "Monto ($)",
        "desc_label": "Descripción / Detalle",
        "save_reg": "💾 GUARDAR REGISTRO",
        "undo_btn": "🔙 DESHACER ÚLTIMO REGISTRO",
        "cap_total": "CAPITAL TOTAL DISPONIBLE",
    }
}

if "idioma" not in str_app.session_state:
    str_app.session_state.idioma = "es"

str_app.sidebar.title("🌐 Idioma / Language")
str_app.session_state.idioma = str_app.sidebar.selectbox("Seleccione Idioma:", ["es"], index=0)
T = TEXTS[str_app.session_state.idioma]

# --- BOTÓN DE REINICIAR ---
str_app.sidebar.title("🛠️ Administración")
if str_app.sidebar.button(T["reset_btn"], use_container_width=True):
    if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    for key in list(str_app.session_state.keys()):
        del str_app.session_state[key]
    str_app.rerun()

# --- CARGAR CONFIGURACIÓN ---
if os.path.exists(FILE_CONFIG):
    try:
        config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
        USER_NAME = config["nombre"]
        if "meta_dinamica" not in str_app.session_state:
            str_app.session_state.meta_dinamica = int(config["meta"])
        CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split("|")]
        CATEGORIAS_RELEVANTES = ["VIVIENDA (CUENTAS BASICAS)", "CUOTAS DE COMPRAS", "SERVICIOS PERSONALES"]
        INGRESO_NETO = int(config.get("ingreso_neto", 0))
    except:
        str_app.error("Error cargando config.")
        if str_app.button("Reconfigurar"): 
            if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
            str_app.rerun()
        str_app.stop()
else:
    str_app.title(T["config_title"])
    str_app.write("Configura tu perfil de control de gastos en Pesos Chilenos (valores sin decimales).")
    
    if "lista_vivienda" not in str_app.session_state: str_app.session_state.lista_vivienda = []
    if "lista_cuotas" not in str_app.session_state: str_app.session_state.lista_cuotas = []
    if "lista_servicios" not in str_app.session_state: str_app.session_state.lista_servicios = []
    
    if "tick_viv" not in str_app.session_state: str_app.session_state.tick_viv = 0
    if "tick_cuo" not in str_app.session_state: str_app.session_state.tick_cuo = 0
    if "tick_ser" not in str_app.session_state: str_app.session_state.tick_ser = 0

    nombre = str_app.text_input(T["name_label"]).upper()
    
    ingreso_neto = str_app.number_input("Ingresos Netos Mensuales ($):", min_value=0, step=1000, value=None, placeholder="Ej: 1200000")
    meta = str_app.number_input(T["meta_label"], min_value=0, step=1000, value=None, placeholder="Ej: 200000")
    
    str_app.subheader("🏦 Cuentas Bancarias")
    bancos_seleccionados = str_app.multiselect("Selecciona tus bancos e instituciones:", BANCOS_CHILE)
    
    cuentas_finales = []
    if bancos_seleccionados:
        str_app.write("*Define el tipo de cuenta para cada institución seleccionada:*")
        for bco in bancos_seleccionados:
            tipo_cta = str_app.selectbox(f"Tipo para {bco}:", ["Vista", "Corriente"], key=f"tipo_{bco}")
            cuentas_finales.append(f"{bco} ({tipo_cta})")

    str_app.divider()
    
    # --- 1. VIVIENDA (CUENTAS BÁSICAS) ---
    str_app.subheader("1. VIVIENDA (CUENTAS BASICAS)")
    with str_app.popover("➕ Agregar gasto"):
        str_app.write("**Nuevo Gasto de Vivienda / Básica**")
        v_nom = str_app.text_input("Nombre del gasto (ej: Arriendo, Luz):", key=f"v_nom_{str_app.session_state.tick_viv}").upper()
        v_mto = str_app.number_input("Monto ($):", min_value=0, step=1000, value=None, placeholder="Ej: 350000", key=f"v_mto_{str_app.session_state.tick_viv}")
        v_venc_check = str_app.checkbox("¿Tiene vencimiento?", key=f"v_vc_{str_app.session_state.tick_viv}")
        v_venc = str_app.date_input("Fecha de Vencimiento", datetime.now().date(), key=f"v_fec_{str_app.session_state.tick_viv}") if v_venc_check else "No"
        
        if str_app.button("Confirmar Gasto Vivienda"):
            if v_nom and v_mto and v_mto > 0:
                str_app.session_state.lista_vivienda.append({"desc": v_nom, "monto": int(v_mto), "venc": str(v_venc)})
                str_app.session_state.tick_viv += 1
                str_app.rerun()
                
    if str_app.session_state.lista_vivienda:
        str_app.dataframe(pd.DataFrame(str_app.session_state.lista_vivienda), use_container_width=True)

    # --- 2. CUOTAS DE COMPRAS ---
    str_app.subheader("2. CUOTAS DE COMPRAS")
    with str_app.popover("➕ Agregar gasto"):
        str_app.write("**Nuevo Gasto de Cuotas**")
        c_nom = str_app.text_input("Nombre del gasto (ej: Casa Comercial, Crédito):", key=f"c_nom_{str_app.session_state.tick_cuo}").upper()
        c_mto = str_app.number_input("Monto de la Cuota ($):", min_value=0, step=1000, value=None, placeholder="Ej: 45000", key=f"c_mto_{str_app.session_state.tick_cuo}")
        c_tot_cuotas = str_app.number_input("¿En cuántas cuotas?", min_value=1, step=1, value=1, key=f"c_tot_{str_app.session_state.tick_cuo}")
        c_venc_check = str_app.checkbox("¿Tiene vencimiento?", key=f"c_vc_{str_app.session_state.tick_cuo}")
        c_venc = str_app.date_input("Fecha de Vencimiento", datetime.now().date(), key=f"c_fec_{str_app.session_state.tick_cuo}") if c_venc_check else "No"
        
        if str_app.button("Confirmar Gasto Cuota"):
            if c_nom and c_mto and c_mto > 0:
                desc_con_cuota = f"{c_nom} (Cuota 1/{int(c_tot_cuotas)})"
                str_app.session_state.lista_cuotas.append({"desc": desc_con_cuota, "monto": int(c_mto), "venc": str(c_venc)})
                str_app.session_state.tick_cuo += 1
                str_app.rerun()
                
    if str_app.session_state.lista_cuotas:
        str_app.dataframe(pd.DataFrame(str_app.session_state.lista_cuotas), use_container_width=True)

    # --- 3. SERVICIOS PERSONALES ---
    str_app.subheader("3. SERVICIOS PERSONALES")
    with str_app.popover("➕ Agregar gasto"):
        str_app.write("**Nuevo Servicio Personal**")
        s_nom = str_app.text_input("Nombre del gasto (ej: Netflix, Gimnasio):", key=f"s_nom_{str_app.session_state.tick_ser}").upper()
        s_mto = str_app.number_input("Monto ($):", min_value=0, step=1000, value=None, placeholder="Ej: 9990", key=f"s_mto_{str_app.session_state.tick_ser}")
        s_venc_check = str_app.checkbox("¿Tiene vencimiento?", key=f"s_vc_{str_app.session_state.tick_ser}")
        s_venc = str_app.date_input("Fecha de Vencimiento", datetime.now().date(), key=f"s_fec_{str_app.session_state.tick_ser}") if s_venc_check else "No"
        
        if str_app.button("Confirmar Gasto Servicio"):
            if s_nom and s_mto and s_mto > 0:
                str_app.session_state.lista_servicios.append({"desc": s_nom, "monto": int(s_mto), "venc": str(s_venc)})
                str_app.session_state.tick_ser += 1
                str_app.rerun()
                
    if str_app.session_state.lista_servicios:
        str_app.dataframe(pd.DataFrame(str_app.session_state.lista_servicios), use_container_width=True)

    str_app.divider()
    
    if str_app.button("💾 GUARDAR TODO E INICIAR SISTEMA", use_container_width=True):
        if nombre and ingreso_neto and ingreso_neto > 0 and cuentas_finales:
            string_cuentas = " | ".join(cuentas_finales)
            
            pd.DataFrame([{
                "nombre": nombre, 
                "ingreso_neto": int(ingreso_neto),
                "meta": int(meta if meta else 0), 
                "cuentas": string_cuentas,
                "idioma": "es"
            }]).to_csv(FILE_CONFIG, index=False)
            
            registros_iniciales = []
            fecha_hoy = str(datetime.now().date())
            
            for item in str_app.session_state.lista_vivienda:
                desc_final = f"{item['desc']} (Vence: {item['venc']})" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "VIVIENDA (CUENTAS BASICAS)", desc_final, item['monto']])
                
            for item in str_app.session_state.lista_cuotas:
                desc_final = f"{item['desc']} (Vence: {item['venc']})" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "CUOTAS DE COMPRAS", desc_final, item['monto']])
                
            for item in str_app.session_state.lista_servicios:
                desc_final = f"{item['desc']} (Vence: {item['venc']})" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "SERVICIOS PERSONALES", desc_final, item['monto']])
                
            df_inicial = pd.DataFrame(registros_iniciales, columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
            df_inicial.to_csv(FILE_DB, index=False)
            str_app.rerun()
        else:
            str_app.error("Asegúrate de llenar el Nombre, Ingresos y tener al menos un Banco con su tipo seleccionado.")
    str_app.stop()

# --- OPERACIONES DE BASE DE DATOS ---
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
df_mov = pd.read_csv(FILE_DB)

# --- CÁLCULOS DE SALDOS ---
cuenta_defecto = CUENTAS_LISTA[0]
total_capital = 0
total_ingresos = 0
total_gastos = 0

for _, row in df_mov.iterrows():
    try:
        m = int(row['MONTO'])
        tipo = row['TIPO']
        if tipo == "INGRESO":
            total_capital += m
            total_ingresos += m
        elif tipo == "GASTO":
            total_capital -= m
            total_gastos += m
    except: continue

# --- INTERFAZ CENTRAL ---
str_app.title(f"💳 Control de Gastos - {USER_NAME}")

str_app.session_state.meta_dinamica = str_app.number_input(T["meta_actual"], value=int(str_app.session_state.meta_dinamica), step=1000)

tabs = str_app.tabs([T["tab_reg"], T["tab_rel"], T["tab_res"], T["tab_ia"]])

# --- 1. PESTAÑA REGISTRO DIARIO ---
with tabs[0]:
    str_app.subheader("🖋️ Bitácora de Movimientos del Día")
    t_op = str_app.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    
    f_fec = datetime.now().date()
    
    if t_op == T["gasto"]:
        f_cat = "GASTOS DIARIOS"
        sub_cat = str_app.selectbox("Tipo de Gasto Diario:", ["TRANSPORTE", "COMIDA", "OTROS"])
    else:
        f_cat = "INGRESO"
        sub_cat = None

    clean_mto = str_app.number_input(T["monto_label"], min_value=0, step=1000, value=None, placeholder="Ej: 15000", key=f"m_{str_app.session_state.get('form_tick', 0)}")
    
    if t_op == T["gasto"]:
        if sub_cat == "OTROS":
            f_des = str_app.text_input(T["desc_label"] + " (Especifica qué compraste):", key=f"d_{str_app.session_state.get('form_tick', 0)}").upper()
        else:
            f_des = sub_cat
    else:
        f_des = str_app.text_input(T["desc_label"] + " (ej: Sueldo, Transferencia):", key=f"d_{str_app.session_state.get('form_tick', 0)}").upper()
    
    if str_app.button(T["save_reg"], use_container_width=True):
        if clean_mto and clean_mto > 0 and f_des:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, cuenta_defecto, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.session_state.form_tick = str_app.session_state.get('form_tick', 0) + 1
            str_app.rerun()

# --- 2. PESTAÑA GASTO RELEVANTE ---
with tabs[1]:
    str_app.subheader("🔥 Registrar un Compromiso o Gasto Relevante")
    
    rel_cat = str_app.selectbox("Selecciona Categoría Relevante:", CATEGORIAS_RELEVANTES)
    rel_nom = str_app.text_input("Nombre / Descripción del Gasto Relevante:", key="rel_nom_input").upper()
    rel_mto = str_app.number_input("Monto de la Cuota o Gasto ($):", min_value=0, step=1000, value=None, placeholder="Ej: 80000", key="rel_mto_input")
    
    if rel_cat == "CUOTAS DE COMPRAS":
        rel_tot_cuotas = str_app.number_input("¿En cuántas cuotas?", min_value=1, step=1, value=1, key="rel_cuotas_input")
    else:
        rel_tot_cuotas = 1
        
    rel_venc_check = str_app.checkbox("¿Tiene vencimiento / fecha de pago?", key="rel_venc_check")
    rel_venc = str_app.date_input("Fecha de Vencimiento", datetime.now().date(), key="rel_fec_input") if rel_venc_check else "No"
    
    if str_app.button("💾 GUARDAR GASTO RELEVANTE", use_container_width=True):
        if rel_nom and rel_mto and rel_mto > 0:
            f_fec_rel = str(datetime.now().date())
            desc_final_rel = rel_nom
            if rel_cat == "CUOTAS DE COMPRAS":
                desc_final_rel = f"{rel_nom} (Cuota 1/{int(rel_tot_cuotas)})"
            
            if str(rel_venc) != "No":
                desc_final_rel = f"{desc_final_rel} [Vence: {rel_venc}]"
                
            nuevo_rel = pd.DataFrame([[f_fec_rel, "GASTO", cuenta_defecto, rel_cat, desc_final_rel, int(rel_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo_rel], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.success(f"Gasto relevante '{rel_nom}' ingresado con éxito.")
            str_app.rerun()

# --- 3. PESTAÑA RESUMEN (CON CALENDARIO MENSUAL) ---
with tabs[2]:
    if not df_mov.empty and str_app.button(T["undo_btn"]):
        df_mov[:-1].to_csv(FILE_DB, index=False); str_app.rerun()
    
    str_app.metric(T["cap_total"], f"${total_capital:,.0f}".replace(",", "."))
    
    # --- BARRA DE PROGRESO DE AHORRO (RESTAURADA) ---
    str_app.divider()
    str_app.subheader("🎯 Progreso de Ahorro del Mes")
    monto_ahorrado = max(0, total_ingresos - total_gastos)
    meta_establecida = str_app.session_state.meta_dinamica if str_app.session_state.meta_dinamica > 0 else 1
    porcentaje_ahorro = min(monto_ahorrado / meta_establecida, 1.0)
    
    col_ah1, col_ah2 = str_app.columns([3, 1])
    col_ah1.write(f"Ahorro Real Actual: **${monto_ahorrado:,.0f}** de una meta de **${meta_establecida:,.0f}**".replace(",", "."))
    col_ah2.write(f"**{porcentaje_ahorro * 100:.1f}%**")
    str_app.progress(porcentaje_ahorro)
    
    # --- ANÁLISIS POR CATEGORÍA + SECCIÓN INGRESOS ---
    str_app.divider()
    str_app.subheader("📊 Análisis Estructural")
    
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum() if not df_gastos.empty else {}
    
    # Visualización de la nueva barra de ingresos totales
    col_i1, col_i2 = str_app.columns([3, 1])
    col_i1.write("🟢 **INGRESOS TOTALES (ENTRADAS DE PLATA)**")
    col_i2.write(f"${total_ingresos:,.0f}".replace(",", "."))
    str_app.progress(1.0) # Barra completa referencial
    
    # Visualización de las categorías de gastos anteriores
    TODAS_CATEGORIAS_GASTOS = ["VIVIENDA (CUENTAS BASICAS)", "CUOTAS DE COMPRAS", "SERVICIOS PERSONALES", "GASTOS DIARIOS"]
    denom_gastos = df_gastos["MONTO"].sum() if not df_gastos.empty and df_gastos["MONTO"].sum() > 0 else 1
    
    for cat in TODAS_CATEGORIAS_GASTOS:
        monto = resumen_cat.get(cat, 0) if isinstance(resumen_cat, pd.Series) else 0
        col_c, col_m = str_app.columns([3, 1])
        col_c.write(f"🔴 **{cat}**")
        col_m.write(f"${int(monto):,.0f}".replace(",", "."))
        str_app.progress(min(monto / denom_gastos, 1.0))

    # --- NUEVO CALENDARIO MENSUAL DEL MES EN CURSO ---
    str_app.divider()
    hoy = datetime.now()
    str_app.subheader(f"📅 Agenda Visual del Mes: {calendar.month_name[hoy.month].upper()} {hoy.year}")
    str_app.write("Revisión de gastos e ingresos distribuidos en el tiempo:")

    # Agrupar movimientos por día para mapearlos en el calendario
    df_mov['FECHA_DT'] = pd.to_datetime(df_mov['FECHA'])
    df_mes_actual = df_mov[(df_mov['FECHA_DT'].dt.year == hoy.year) & (df_mov['FECHA_DT'].dt.month == hoy.month)]
    
    mapa_dias = {}
    for _, fila in df_mes_actual.iterrows():
        dia = fila['FECHA_DT'].day
        if dia not in mapa_dias:
            mapa_dias[dia] = []
        mapa_dias[dia].append(fila)

    # Generar la grilla del calendario (Semanas)
    cal = calendar.Calendar(firstweekday=6) # Empezar en Domingo
    semanas = cal.monthdayscalendar(hoy.year, hoy.month)
    
    dias_semana = ["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"]
    cols_dias = str_app.columns(7)
    for i, d_nom in enumerate(dias_semana):
        cols_dias[i].markdown(f"<p style='text-align:center; font-weight:bold;'>{d_nom}</p>", unsafe_allow_html=True)
        
    for semana in semanas:
        cols = str_app.columns(7)
        for i, dia in enumerate(semanal_dia := semana):
            if dia == 0:
                cols[i].write("") # Espacio vacío fuera de rango de mes
            else:
                # Contenedor visual para cada casilla del día
                with cols[i].container(border=True):
                    str_app.markdown(f"**{dia}**")
                    if dia in mapa_dias:
                        for mov in mapa_dias[dia]:
                            color = "green" if mov['TIPO'] == "INGRESO" else "red"
                            simbolo = "🟢" if mov['TIPO'] == "INGRESO" else "🔴"
                            texto_item = f"<span style='color:{color}; font-size:12px;'>{simbolo} ${int(mov['MONTO']):,} ({mov['DESC']})</span>"
                            str_app.markdown(texto_item, unsafe_allow_html=True)

# --- 4. PESTAÑA IA ---
with tabs[3]:
    api_key = str_app.secrets.get("GROQ_API_KEY")
    if api_key:
        client = Groq(api_key=api_key)
        gastos_texto = ""
        if not df_gastos.empty:
            resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum()
            gastos_texto = resumen_cat.to_string()
        
        str_app.subheader("🕵️ Análisis Inteligente")
        if str_app.button("✨ GENERAR CONSEJO PROACTIVO"):
            ctx = f"Usuario: {USER_NAME}. Capital: {total_capital}. Ingreso: {INGRESO_NETO}. Meta: {str_app.session_state.meta_dinamica}. Gastos por categoría: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Eres un analista financiero. Analiza los gastos y da un consejo específico para alcanzar la meta de ahorro. Sé breve y directo en español de Chile sin usar decimales."},
                          {"role": "user", "content": ctx}],
                model="llama-3.1-8b-instant")
            str_app.success(chat.choices[0].message.content)
            
        user_ask = str_app.text_input(f"O hazle una pregunta directa:")
        if user_ask:
            ctx = f"Capital: {total_capital}, Ingreso: {INGRESO_NETO}, Meta: {str_app.session_state.meta_dinamica}. Gastos: {gastos_texto}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Asesor financiero breve."},
                          {"role": "user", "content": f"Contexto: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            str_app.info(chat.choices[0].message.content)
