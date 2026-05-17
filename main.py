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
    "001 - Banco de Chile", "012 - BancoEstado", "014 - Scotiabank Chile",
    "016 - Banco Bci", "028 - Banco BICE", "037 - Banco Santander Chile",
    "039 - Banco Itaú", "049 - Banco Security", "051 - Banco Falabella",
    "053 - Banco Ripley", "055 - Banco Consorcio", "730 - Tenpo Prepago",
    "672 - Coopeuch"
]

CATEGORIAS_ESTRICTAS = [
    "1. VIVIENDA (CUENTAS BASICAS)", 
    "2. CUOTAS DE COMPRAS", 
    "3. SERVICIOS PERSONALES"
]

# --- TRADUCCIONES ---
TEXTS = {
    "es": {
        "config_title": "🚀 CONFIGURACIÓN INICIAL DEL SISTEMA",
        "name_label": "¿CÓMO TE LLAMAS?",
        "meta_label": "META DE AHORRO MENSUAL ($)",
        "meta_actual": "🎯 META DE AHORRO ACTUAL:",
        "reset_btn": "🚨 REINICIAR SISTEMA",
        "tab_reg": "📝 REGISTRO DIARIO",
        "tab_rel": "🔥 GASTO RELEVANTE",
        "tab_aho": "🎯 AHORRO",
        "tab_res": "📊 RESUMEN",
        "tab_ia": "🕵️ ANALISTA IA",
        "type_op": "TIPO DE MOVIMIENTO",
        "gasto": "GASTO",
        "ingreso": "INGRESO",
        "monto_label": "MONTO ($)",
        "desc_label": "DESCRIPCIÓN / DETALLE",
        "save_reg": "💾 GUARDAR REGISTRO",
        "undo_btn": "🔙 DESHACER ÚLTIMO REGISTRO",
        "cap_total": "CAPITAL TOTAL DISPONIBLE",
    }
}

if "idioma" not in str_app.session_state:
    str_app.session_state.idioma = "es"

T = TEXTS[str_app.session_state.idioma]

# --- BOTÓN DE REINICIAR EN BARRA LATERAL ---
str_app.sidebar.title("🛠️ ADMINISTRACIÓN")
if str_app.sidebar.button(T["reset_btn"], use_container_width=True):
    if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    for key in list(str_app.session_state.keys()): del str_app.session_state[key]
    str_app.rerun()

# --- CARGAR CONFIGURACIÓN O INICIALIZAR CONTROLES (CON ENTRADA E INCLUSIÓN DE GASTOS INICIALES) ---
if os.path.exists(FILE_CONFIG):
    try:
        config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
        USER_NAME = config["nombre"]
        if "meta_dinamica" not in str_app.session_state:
            str_app.session_state.meta_dinamica = int(config["meta"])
        CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split("|")]
        INGRESO_NETO = int(config.get("ingreso_neto", 0))
    except:
        str_app.error("ERROR CARGANDO CONFIGURACIÓN HISTÓRICA.")
        str_app.stop()
else:
    str_app.title(T["config_title"])
    
    # 1. DATOS DE IDENTIFICACIÓN Y PRESUPUESTO
    nombre = str_app.text_input(T["name_label"]).upper()
    ingreso_neto = str_app.number_input("INGRESOS NETOS MENSUALES ($):", min_value=0, step=1000, value=None, placeholder="EJ: 1200000")
    meta = str_app.number_input(T["meta_label"], min_value=0, step=1000, value=None, placeholder="EJ: 200000")
    
    # 2. CONFIGURACIÓN DE BANCOS Y TIPO DE CUENTA
    bancos_seleccionados = str_app.multiselect("SELECCIONA TUS BANCOS E INSTITUCIONES:", BANCOS_CHILE)
    tipo_cuenta = str_app.radio("TIPO DE CUENTA:", ["CORRIENTE", "VISTA"], horizontal=True)
    cuentas_finales = [f"{b} ({tipo_cuenta})" for b in bancos_seleccionados] if bancos_seleccionados else [f"MI CUENTA ÚNICA ({tipo_cuenta})"]
    cuenta_inicial_defecto = cuentas_finales[0]

    str_app.divider()
    
    # 3. CARGA E INCLUSIÓN OBLIGATORIA DE GASTOS FIJOS/RELEVANTES EN LA CONFIGURACIÓN INICIAL
    str_app.subheader("🔥 INCLUSIÓN DE GASTOS ESTRUCTURALES INICIALES")
    
    str_app.markdown("### 🏠 1. GASTOS DE VIVIENDA (CUENTAS BÁSICAS)")
    v_desc = str_app.text_input("DESCRIPCIÓN VIVIENDA (EJ: ARRIENDO, LUZ, AGUA):", key="init_v_desc").upper()
    v_monto = str_app.number_input("MONTO VIVIENDA ($):", min_value=0, step=1000, key="init_v_monto")
    v_venc = str_app.date_input("FECHA DE VENCIMIENTO VIVIENDA:", datetime.now().date(), key="init_v_venc")

    str_app.markdown("### 💳 2. CUOTAS DE COMPRAS")
    c_desc = str_app.text_input("DESCRIPCIÓN COMPRA (EJ: REFRIGERADOR, AVION):", key="init_c_desc").upper()
    c_monto = str_app.number_input("MONTO CUOTA ($):", min_value=0, step=1000, key="init_c_monto")
    col_i1, col_i2 = str_app.columns(2)
    with col_i1:
        c_act = str_app.number_input("CUOTA ACTUAL:", min_value=1, step=1, value=1, key="init_c_act")
    with col_i2:
        c_tot = str_app.number_input("TOTAL CUOTAS:", min_value=1, step=1, value=12, key="init_c_tot")
    c_venc = str_app.date_input("FECHA DE VENCIMIENTO CUOTA:", datetime.now().date(), key="init_c_venc")

    str_app.markdown("### 👤 3. SERVICIOS PERSONALES")
    p_desc = str_app.text_input("DESCRIPCIÓN SERVICIO PERSONAL (EJ: ISAPRE, GIMNASIO):", key="init_p_desc").upper()
    p_monto = str_app.number_input("MONTO PERSONAL ($):", min_value=0, step=1000, key="init_p_monto")
    p_venc = str_app.date_input("FECHA DE VENCIMIENTO PERSONAL:", datetime.now().date(), key="init_p_venc")

    if str_app.button("💾 INICIAR SISTEMA Y CARGAR GASTOS", use_container_width=True):
        if nombre and ingreso_neto and ingreso_neto > 0:
            # Guardar la configuración base del usuario
            pd.DataFrame([{"nombre": nombre, "ingreso_neto": int(ingreso_neto), "meta": int(meta if meta else 0), "cuentas": " | ".join(cuentas_finales)}]).to_csv(FILE_CONFIG, index=False)
            
            # Preparar dataframe base de movimientos
            df_inicial = pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
            nuevos_registros = []
            fecha_hoy_str = str(datetime.now().date())

            # Inyectar obligatoriamente los 3 tipos de gastos si tienen monto definido
            if v_monto > 0 and v_desc:
                nuevos_registros.append([fecha_hoy_str, "GASTO", cuenta_inicial_defecto, "1. VIVIENDA (CUENTAS BASICAS)", f"{v_desc} [VENCE: {v_venc}]", int(v_monto)])
            
            if c_monto > 0 and c_desc:
                nuevos_registros.append([fecha_hoy_str, "GASTO", cuenta_inicial_defecto, "2. CUOTAS DE COMPRAS", f"{c_desc} (CUOTA {int(c_act)}/{int(c_tot)}) [VENCE: {c_venc}]", int(c_monto)])
                
            if p_monto > 0 and p_desc:
                nuevos_registros.append([fecha_hoy_str, "GASTO", cuenta_inicial_defecto, "3. SERVICIOS PERSONALES", f"{p_desc} [VENCE: {p_venc}]", int(p_monto)])

            if nuevos_registros:
                df_inicial = pd.concat([df_inicial, pd.DataFrame(nuevos_registros, columns=df_inicial.columns)], ignore_index=True)
                
            df_inicial.to_csv(FILE_DB, index=False)
            str_app.rerun()
    str_app.stop()

# --- CARGA Y VERIFICACIÓN DEL CSV DE MOVIMIENTOS ---
if os.path.exists(FILE_DB):
    try:
        df_mov = pd.read_csv(FILE_DB)
        df_mov['MONTO'] = pd.to_numeric(df_mov['MONTO'], errors='coerce').fillna(0).astype(int)
    except:
        df_mov = pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
else:
    df_mov = pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
    df_mov.to_csv(FILE_DB, index=False)

cuenta_defecto = CUENTAS_LISTA[0]

# --- CÁLCULO DE CAPITAL TOTAL (TRANSACCIONAL PURO) ---
total_capital = 0
for _, row in df_mov.iterrows():
    m = int(row['MONTO'])
    if row['TIPO'] in ["INGRESO", "AHORRO_ENTRA"]:
        total_capital += m
    elif row['TIPO'] in ["GASTO", "AHORRO_SACO"]:
        total_capital -= m

# --- INTERFAZ CENTRAL ---
str_app.title(f"💳 CONTROL DE GASTOS - {USER_NAME}")
str_app.session_state.meta_dinamica = str_app.number_input(T["meta_actual"], value=int(str_app.session_state.meta_dinamica), step=1000)

tabs = str_app.tabs([T["tab_reg"], T["tab_rel"], T["tab_aho"], T["tab_res"], T["tab_ia"]])

# --- 1. PESTAÑA REGISTRO DIARIO ---
with tabs[0]:
    str_app.subheader("🖋️ BITÁCORA DE MOVIMIENTOS DEL DÍA")
    t_op = str_app.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    f_fec = datetime.now().date()
    
    if t_op == T["gasto"]:
        f_cat = "GASTOS DIARIOS"
        sub_cat = str_app.selectbox("TIPO DE GASTO DIARIO:", ["TRANSPORTE", "COMIDA", "OTROS"])
    else:
        f_cat = "INGRESO"
        sub_cat = None

    clean_mto = str_app.number_input(T["monto_label"], min_value=0, step=1000, value=None, placeholder="EJ: 15000", key=f"m_{str_app.session_state.get('form_tick', 0)}")
    
    if t_op == T["gasto"]:
        f_des = str_app.text_input(T["desc_label"] + " (DETALLE):", key=f"d_{str_app.session_state.get('form_tick', 0)}").upper() if sub_cat == "OTROS" else sub_cat
    else:
        f_des = str_app.text_input(T["desc_label"] + " (EJ: SUELDO):", key=f"d_{str_app.session_state.get('form_tick', 0)}").upper()
    
    if str_app.button(T["save_reg"], use_container_width=True):
        if clean_mto and clean_mto > 0 and f_des:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, cuenta_defecto, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.session_state.form_tick = str_app.session_state.get('form_tick', 0) + 1
            str_app.rerun()

# --- 2. PESTAÑA GASTO RELEVANTE ---
with tabs[1]:
    str_app.subheader("🔥 REGISTRAR GASTO RELEVANTE EXTRA")
    rel_cat = str_app.selectbox("SELECCIONA CATEGORÍA RELEVANTE:", CATEGORIAS_ESTRICTAS)
    rel_nom = str_app.text_input("NOMBRE / DESCRIPCIÓN:", key="rel_nom_input").upper()
    rel_mto = str_app.number_input("MONTO ($):", min_value=0, step=1000, value=None, placeholder="EJ: 80000", key="rel_mto_input")
    
    if "2. CUOTAS DE COMPRAS" in rel_cat:
        col_c1, col_c2 = str_app.columns(2)
        with col_c1:
            n_cuota_actual = str_app.number_input("CUOTA ACTUAL:", min_value=1, step=1, value=1)
        with col_c2:
            n_cuotas_totales = str_app.number_input("TOTAL CUOTAS:", min_value=1, step=1, value=12)
    
    rel_venc = str_app.date_input("FECHA DE VENCIMIENTO OBLIGATORIA:", datetime.now().date())
    
    if str_app.button("💾 GUARDAR GASTO RELEVANTE", use_container_width=True):
        if rel_nom and rel_mto and rel_mto > 0:
            if "2. CUOTAS DE COMPRAS" in rel_cat:
                desc_final_rel = f"{rel_nom} (CUOTA {int(n_cuota_actual)}/{int(n_cuotas_totales)})"
            else:
                desc_final_rel = rel_nom
                
            desc_final_rel = f"{desc_final_rel} [VENCE: {rel_venc}]"
                
            nuevo_rel = pd.DataFrame([[str(datetime.now().date()), "GASTO", cuenta_defecto, rel_cat, desc_final_rel, int(rel_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo_rel], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.rerun()

# --- 3. PESTAÑA AHORRO ---
with tabs[2]:
    str_app.subheader("💰 REGISTRO TRANSACCIONAL DE FONDOS DE AHORRO")
    
    tipo_ahorro = str_app.radio("SELECCIONA TIPO DE TRANSACCIÓN DE AHORRO:", ["DEPOSITAR EN AHORRO (ENTRA)", "RETIRAR DE AHORRO (SACA)"], horizontal=True)
    monto_ahorro_trans = str_app.number_input("MONTO DE LA OPERACIÓN ($):", min_value=0, step=1000, value=None, placeholder="EJ: 50000", key="monto_aho_trans")
    detalle_ahorro_trans = str_app.text_input("DETALLE DE LA OPERACIÓN (EJ: FONDO MUTUO, DEPÓSITO A PLAZO):", key="det_aho_trans").upper()
    
    if str_app.button("💾 REGISTRAR MOVIMIENTO DE AHORRO", use_container_width=True):
        if monto_ahorro_trans and monto_ahorro_trans > 0 and detalle_ahorro_trans:
            tipo_csv = "AHORRO_ENTRA" if "ENTRA" in tipo_ahorro else "AHORRO_SACO"
            nuevo_aho = pd.DataFrame([[str(datetime.now().date()), tipo_csv, cuenta_defecto, "AHORRO", detalle_ahorro_trans, int(monto_ahorro_trans)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo_aho], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.rerun()

# --- 4. PESTAÑA RESUMEN (CALENDARIO Y DESGLOSE COMPLETO) ---
with tabs[3]:
    if not df_mov.empty and str_app.button(T["undo_btn"]):
        df_mov = df_mov.iloc[:-1]
        df_mov.to_csv(FILE_DB, index=False)
        str_app.rerun()
    
    str_app.metric(T["cap_total"], f"${total_capital:,.0f}".replace(",", "."))
    
    str_app.subheader("📊 ANÁLISIS ESTRUCTURAL POR CATEGORÍAS")
    
    total_ingresos_mes = df_mov[df_mov["TIPO"] == "INGRESO"]["MONTO"].sum()
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum() if not df_gastos.empty else {}
    
    str_app.write(f"🟢 **INGRESOS REGISTRADOS:** ${total_ingresos_mes:,.0f}".replace(",", "."))
    
    TODAS_LAS_CATEGORIAS = CATEGORIAS_ESTRICTAS + ["GASTOS DIARIOS"]
    
    for cat in TODAS_LAS_CATEGORIAS:
        m = resumen_cat.get(cat, 0) if isinstance(resumen_cat, pd.Series) else 0
        str_app.write(f"🔴 **{cat}:** ${int(m):,.0f}".replace(",", "."))
        
        df_sub_cat = df_gastos[df_gastos["CATEGORIA"] == cat]
        if not df_sub_cat.empty:
            for _, g_fila in df_sub_cat.iterrows():
                str_app.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;📄 *{g_fila['FECHA']}* | {g_fila['DESC']} | **${int(g_fila['MONTO']):,.0f}**".replace(",", "."))

    # --- PROCESAMIENTO MATRICIAL DEL CALENDARIO ---
    str_app.divider()
    hoy = datetime.now()
    str_app.subheader(f"📅 CALENDARIO DE VENCIMIENTOS Y OPERACIONES DIARIAS: {calendar.month_name[hoy.month].upper()} {hoy.year}")
    
    df_mov['FECHA_DT'] = pd.to_datetime(df_mov['FECHA'])
    
    datos_dias = {d: 0 for d in range(1, 32)}
    detalle_dias = {d: [] for d in range(1, 32)}
    
    df_mes_ingresados = df_mov[(df_mov['FECHA_DT'].dt.year == hoy.year) & (df_mov['FECHA_DT'].dt.month == hoy.month)]
    for _, fila in df_mes_ingresados.iterrows():
        if fila['CATEGORIA'] == "GASTOS DIARIOS" or fila['TIPO'] == "INGRESO":
            d_real = int(fila['FECHA_DT'].day)
            detalle_dias[d_real].append(f"{'🟢 INGRESO' if fila['TIPO']=='INGRESO' else '🔴 GASTO DIARIO'} - {fila['DESC']}: ${int(fila['MONTO']):,}")
            if fila['TIPO'] == 'INGRESO':
                datos_dias[d_real] = 2 if datos_dias[d_real] == 0 else 3
            else:
                datos_dias[d_real] = 1 if datos_dias[d_real] == 0 else 3

    for _, fila in df_mov.iterrows():
        if "[VENCE: " in str(fila['DESC']):
            try:
                f_venc_str = str(fila['DESC']).split("[VENCE: ")[1].replace("]", "").strip()
                f_venc_dt = datetime.strptime(f_venc_str, "%Y-%m-%d")
                if f_venc_dt.year == hoy.year and f_venc_dt.month == hoy.month:
                    d_venc = int(f_venc_dt.day)
                    limpio_desc = fila['DESC'].split(" [")[0]
                    detalle_dias[d_venc].append(f"⚠️ VENCIMIENTO ({fila['CATEGORIA']}) - {limpio_desc}: ${int(fila['MONTO']):,}")
                    datos_dias[d_venc] = 3
            except: pass

    cal_obj = calendar.Calendar(firstweekday=6)
    semanas_mes = cal_obj.monthdayscalendar(hoy.year, hoy.month)
    
    matriz_visual = []
    for sem in semanas_mes:
        fila_sem = {}
        for idx, dia_sem in enumerate(["DOM", "LUN", "MAR", "MIÉ", "JUE", "VIE", "SÁB"]):
            dia_num = sem[idx]
            if dia_num == 0:
                fila_sem[dia_sem] = ""
            else:
                status = datos_dias.get(int(dia_num), 0)
                marca = "⚪" if status == 0 else ("🔴" if status == 1 else ("🟢" if status == 2 else "🟡"))
                fila_sem[dia_sem] = f"{dia_num} {marca}"
        matriz_visual.append(fila_sem)
        
    df_cal_visual = pd.DataFrame(matriz_visual)
    
    seleccion_interactiva = str_app.dataframe(
        df_cal_visual, 
        use_container_width=True, 
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row"
    )
    
    str_app.caption("LEYENDA: ⚪ SIN COMPROMISOS | 🔴 GASTOS DIARIOS | 🟢 INGRESOS | 🟡 ALERTAS O VENCIMIENTOS")

    filas_seleccionadas = seleccion_interactiva.get("selection", {}).get("rows", [])
    
    str_app.divider()
    str_app.subheader("📋 PANEL DE DETALLE AUTOMATIZADO")
    
    if filas_seleccionadas:
        indice_semana = filas_seleccionadas[0]
        semana_elegida = semanas_mes[indice_semana]
        dias_con_datos = [int(d) for d in semana_elegida if d != 0 and len(detalle_dias[int(d)]) > 0]
        
        if dias_con_datos:
            pestanas_dias = str_app.tabs([f"DÍA {d}" for d in dias_con_datos])
            for i, d_activo in enumerate(dias_con_datos):
                with pestanas_dias[i]:
                    str_app.write(f"### 📑 BITÁCORA COMPLETA DEL DÍA {d_activo}")
                    for item in detalle_dias[d_activo]:
                        str_app.markdown(f"* {item}")
        else:
            str_app.info("LA SEMANA SELECCIONADA NO REGISTRA GASTOS DIARIOS, INGRESOS NI VENCIMIENTOS AGENDADOS.")
    else:
        str_app.warning("SELECCIONA HACIENDO CLIC ARRIBA EN CUALQUIER FILA DEL CALENDARIO PARA CARGAR DINÁMICAMENTE EL DESGLOSE DE LOS DÍAS.")

# --- 5. PESTAÑA IA ---
with tabs[4]:
    str_app.subheader("🕵️ CHAT INTERACTIVO CON EL ANALISTA IA")
    api_key = str_app.secrets.get("GROQ_API_KEY")
    
    if api_key:
        client = Groq(api_key=api_key)
        
        user_query = str_app.text_input("HAZLE UNA PREGUNTA A LA IA SOBRE TU ESTADO FINANCIERO O MOVIMIENTOS:", key="ia_chat_query").upper()
        
        if str_app.button("✨ CONSULTAR AL ANALISTA", use_container_width=True):
            if user_query:
                contexto_datos = f"DATOS ACTUALES DEL SISTEMA -> CAPITAL TOTAL: {total_capital}. RESUMEN MOVIMIENTOS: {str(df_mov[['FECHA', 'TIPO', 'CATEGORIA', 'DESC', 'MONTO']].tail(20).to_dict(orient='records'))}"
                
                with str_app.spinner("ANALIZANDO INFORMACIÓN..."):
                    chat = client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": "ERES UN ASISTENTE Y ANALISTA FINANCIERO EXPERTO PARA CHILE. RESPONDE DE FORMA CONCISA Y DIRECTA, SIEMPRE EN MAYÚSCULAS."},
                            {"role": "user", "content": f"CONTEXTO FINANCIERO: {contexto_datos}. PREGUNTA DEL USUARIO: {user_query}"}
                        ],
                        model="llama-3.1-8b-instant"
                    )
                str_app.success(chat.choices[0].message.content)
            else:
                str_app.warning("POR FAVOR ESCRIBE UNA PREGUNTA ANTES DE CONSULTAR.")
    else:
        str_app.error("NO SE DETECTÓ LA CLAVE DE API (GROQ_API_KEY) EN LOS SECRETOS DE STREAMLIT.")
