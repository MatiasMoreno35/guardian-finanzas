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

# --- TRADUCCIONES ---
TEXTS = {
    "es": {
        "config_title": "🚀 Configuración Inicial",
        "name_label": "¿Cómo te llamas?",
        "meta_label": "Meta de Ahorro Mensual ($)",
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

T = TEXTS[str_app.session_state.idioma]

# --- BOTÓN DE REINICIAR ---
str_app.sidebar.title("🛠️ Administración")
if str_app.sidebar.button(T["reset_btn"], use_container_width=True):
    if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
    if os.path.exists(FILE_DB): os.remove(FILE_DB)
    for key in list(str_app.session_state.keys()): del str_app.session_state[key]
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
        str_app.stop()
else:
    str_app.title(T["config_title"])
    nombre = str_app.text_input(T["name_label"]).upper()
    ingreso_neto = str_app.number_input("Ingresos Netos Mensuales ($):", min_value=0, step=1000, value=None, placeholder="Ej: 1200000")
    meta = str_app.number_input(T["meta_label"], min_value=0, step=1000, value=None, placeholder="Ej: 200000")
    
    bancos_seleccionados = str_app.multiselect("Selecciona tus bancos e instituciones:", BANCOS_CHILE)
    cuentas_finales = [f"{b} (Corriente)" for b in bancos_seleccionados] if bancos_seleccionados else ["Mi Cuenta Única"]

    if str_app.button("💾 INICIAR SISTEMA", use_container_width=True):
        if nombre and ingreso_neto and ingreso_neto > 0:
            pd.DataFrame([{"nombre": nombre, "ingreso_neto": int(ingreso_neto), "meta": int(meta if meta else 0), "cuentas": " | ".join(cuentas_finales)}]).to_csv(FILE_CONFIG, index=False)
            pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
            str_app.rerun()
    str_app.stop()

# --- OPERACIONES DE BASE DE DATOS ---
df_mov = pd.read_csv(FILE_DB)

cuenta_defecto = CUENTAS_LISTA[0]
total_capital, total_ingresos, total_gastos = 0, 0, 0
for _, row in df_mov.iterrows():
    try:
        m = int(row['MONTO'])
        if row['TIPO'] == "INGRESO": total_capital += m; total_ingresos += m
        elif row['TIPO'] == "GASTO": total_capital -= m; total_gastos += m
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
        f_des = str_app.text_input(T["desc_label"] + " (Detalle):", key=f"d_{str_app.session_state.get('form_tick', 0)}").upper() if sub_cat == "OTROS" else sub_cat
    else:
        f_des = str_app.text_input(T["desc_label"] + " (ej: Sueldo):", key=f"d_{str_app.session_state.get('form_tick', 0)}").upper()
    
    if str_app.button(T["save_reg"], use_container_width=True):
        if clean_mto and clean_mto > 0 and f_des:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, cuenta_defecto, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.session_state.form_tick = str_app.session_state.get('form_tick', 0) + 1
            str_app.rerun()

# --- 2. PESTAÑA GASTO RELEVANTE ---
with tabs[1]:
    str_app.subheader("🔥 Registrar Gasto Relevante")
    rel_cat = str_app.selectbox("Selecciona Categoría Relevante:", CATEGORIAS_RELEVANTES)
    rel_nom = str_app.text_input("Nombre / Descripción:", key="rel_nom_input").upper()
    rel_mto = str_app.number_input("Monto ($):", min_value=0, step=1000, value=None, placeholder="Ej: 80000", key="rel_mto_input")
    
    rel_tot_cuotas = str_app.number_input("¿En cuántas cuotas?", min_value=1, step=1, value=1) if rel_cat == "CUOTAS DE COMPRAS" else 1
    rel_venc_check = str_app.checkbox("¿Tiene vencimiento / fecha de pago?", key="rel_venc_check")
    rel_venc = str_app.date_input("Fecha de Vencimiento", datetime.now().date()) if rel_venc_check else "No"
    
    if str_app.button("💾 GUARDAR GASTO RELEVANTE", use_container_width=True):
        if rel_nom and rel_mto and rel_mto > 0:
            desc_final_rel = f"{rel_nom} (Cuota 1/{int(rel_tot_cuotas)})" if rel_cat == "CUOTAS DE COMPRAS" else rel_nom
            if str(rel_venc) != "No":
                desc_final_rel = f"{desc_final_rel} [Vence: {rel_venc}]"
                
            nuevo_rel = pd.DataFrame([[str(datetime.now().date()), "GASTO", cuenta_defecto, rel_cat, desc_final_rel, int(rel_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo_rel], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.rerun()

# --- 3. PESTAÑA RESUMEN (CON CALENDARIO MATRICIAL INTEGRADO) ---
with tabs[2]:
    if not df_mov.empty and str_app.button(T["undo_btn"]):
        df_mov[:-1].to_csv(FILE_DB, index=False); str_app.rerun()
    
    str_app.metric(T["cap_total"], f"${total_capital:,.0f}".replace(",", "."))
    
    # --- BARRA DE PROGRESO DE AHORRO ---
    str_app.subheader("Ahorro Real Mensual")
    monto_ahorrado = max(0, total_ingresos - total_gastos)
    meta_establecida = str_app.session_state.meta_dinamica if str_app.session_state.meta_dinamica > 0 else 1
    str_app.progress(min(monto_ahorrado / meta_establecida, 1.0))
    
    # --- ANÁLISIS ESTRUCTURAL ---
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum() if not df_gastos.empty else {}
    
    str_app.write(f"🟢 **INGRESOS:** ${total_ingresos:,.0f}".replace(",", "."))
    for cat in ["VIVIENDA (CUENTAS BASICAS)", "CUOTAS DE COMPRAS", "SERVICIOS PERSONALES", "GASTOS DIARIOS"]:
        m = resumen_cat.get(cat, 0) if isinstance(resumen_cat, pd.Series) else 0
        str_app.write(f"🔴 **{cat}:** ${int(m):,.0f}".replace(",", "."))

    # --- PROCESAMIENTO DEL CALENDARIO CUADRADO ---
    str_app.divider()
    hoy = datetime.now()
    str_app.subheader(f"📅 Calendario del Mes: {calendar.month_name[hoy.month].upper()} {hoy.year}")
    
    # Mapear los datos de la DB
    df_mov['FECHA_DT'] = pd.to_datetime(df_mov['FECHA'])
    df_mes = df_mov[(df_mov['FECHA_DT'].dt.year == hoy.year) & (df_mov['FECHA_DT'].dt.month == hoy.month)]
    
    # Clasificación diaria para pintar la matriz
    # 0 = Vacío, 1 = Solo Gasto, 2 = Solo Ingreso, 3 = Ambos / Vencimientos
    datos_dias = {d: 0 for d in range(1, 32)}
    detalle_dias = {d: [] for d in range(1, 32)}
    
    # Buscar registros ingresados el día o vencimientos que caen este mes
    for _, fila in df_mes.iterrows():
        d_ingreso = fila['FECHA_DT'].day
        detalle_dias[d_ingreso].append(f"{'🟢' if fila['TIPO']=='INGRESO' else '🔴'} ${int(fila['MONTO']):,} - {fila['DESC']}")
        if fila['TIPO'] == 'INGRESO':
            datos_dias[d_ingreso] = 2 if datos_dias[d_ingreso] == 0 else 3
        else:
            datos_dias[d_ingreso] = 1 if datos_dias[d_ingreso] == 0 else 3

    # Buscar si en la descripción hay un vencimiento explícito para marcarlo [Vence: YYYY-MM-DD]
    for _, fila in df_mov.iterrows():
        if "[Vence: " in str(fila['DESC']):
            try:
                f_venc_str = str(fila['DESC']).split("[Vence: ")[1].replace("]", "").strip()
                f_venc_dt = datetime.strptime(f_venc_str, "%Y-%m-%d")
                if f_venc_dt.year == hoy.year and f_venc_dt.month == hoy.month:
                    d_venc = f_venc_dt.day
                    datos_dias[d_venc] = 3  # Forzar alerta amarilla/vencimiento
                    detalle_dias[d_venc].append(f"⚠️ VENCIMIENTO: {fila['DESC'].split(' [')[0]} (${int(fila['MONTO']):,})")
            except: pass

    # Construcción de la matriz visual cuadrada estándar de calendario
    cal_obj = calendar.Calendar(firstweekday=6)
    semanas_mes = cal_obj.monthdayscalendar(hoy.year, hoy.month)
    
    matriz_visual = []
    for sem in semanas_mes:
        fila_sem = {}
        for idx, dia_sem in enumerate(["Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb"]):
            dia_num = sem[idx]
            if dia_num == 0:
                fila_sem[dia_sem] = ""
            else:
                status = datos_dias.get(dia_num, 0)
                marca = "⚪" if status == 0 else ("🔴" if status == 1 else ("🟢" if status == 2 else "🟡"))
                fila_sem[dia_sem] = f"{dia_num} {marca}"
        matriz_visual.append(fila_sem)
        
    df_cal_visual = pd.DataFrame(matriz_visual)
    
    # Renderizado estético del cuadro
    str_app.dataframe(df_cal_visual, use_container_width=True, hide_index=True)
    str_app.caption("Leyenda: ⚪ Sin movimientos | 🔴 Solo Gastos | 🟢 Solo Ingresos | 🟡 Mix del Día o Vencimientos Fijos")
    
    # --- VENTANA EMERGENTE DETALLADA AL SELECCIONAR DÍA ---
    dia_elegido = str_app.number_input("🔎 Selecciona un día para ver el detalle:", min_value=1, max_value=len(datos_dias), value=hoy.day)
    
    with str_app.popover(f"📋 Ver detalles del Día {dia_elegido}", use_container_width=True):
        str_app.write(f"### Historial Técnico - Día {dia_elegido}")
        items = detalle_dias.get(dia_elegido, [])
        if items:
            for item in items:
                str_app.markdown(f"* {item}")
        else:
            str_app.info("No hay registros ni compromisos agendados para esta fecha.")

# --- 4. PESTAÑA IA ---
with tabs[3]:
    api_key = str_app.secrets.get("GROQ_API_KEY")
    if api_key:
        client = Groq(api_key=api_key)
        if str_app.button("✨ GENERAR CONSEJO PROACTIVO"):
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": "Asesor breve de finanzas chilenas."},
                          {"role": "user", "content": f"Capital: {total_capital}. Ingresos: {total_ingresos}. Gastos: {total_gastos}"}],
                model="llama-3.1-8b-instant")
            str_app.success(chat.choices[0].message.content)
