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
        "tab_reg": "📝 REGISTRO",
        "tab_res": "📊 RESUMEN",
        "tab_ia": "🕵️ ANALISTA IA",
        "type_op": "Tipo",
        "gasto": "GASTO",
        "ingreso": "INGRESO",
        "cat_label": "Categoría",
        "monto_label": "Monto ($)",
        "desc_label": "Descripción",
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

# --- CARGAR CONFIGURACIÓN O INTERFAZ DE CONFIGURACIÓN INICIAL FIEL ---
if os.path.exists(FILE_CONFIG):
    try:
        config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
        USER_NAME = config["nombre"]
        if "meta_dinamica" not in str_app.session_state:
            str_app.session_state.meta_dinamica = int(config["meta"])
        CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split("|")]
        CATEGORIAS_SISTEMA = ["VIVIENDA (CUENTAS BASICAS)", "CUOTAS DE COMPRAS", "SERVICIOS PERSONALES", "GASTOS DIARIOS"]
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
                desc_final = f"{item['desc']} [VENCE: {item['venc']}]" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "VIVIENDA (CUENTAS BASICAS)", desc_final, item['monto']])
                
            for item in str_app.session_state.lista_cuotas:
                desc_final = f"{item['desc']} [VENCE: {item['venc']}]" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "CUOTAS DE COMPRAS", desc_final, item['monto']])
                
            for item in str_app.session_state.lista_servicios:
                desc_final = f"{item['desc']} [VENCE: {item['venc']}]" if item['venc'] != "No" else item['desc']
                registros_iniciales.append([fecha_hoy, "GASTO", cuentas_finales[0], "SERVICIOS PERSONALES", desc_final, item['monto']])
                
            df_inicial = pd.DataFrame(registros_iniciales, columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
            df_inicial.to_csv(FILE_DB, index=False)
            str_app.rerun()
        else:
            str_app.error("Asegúrate de llenar el Nombre, Ingresos y tener al menos un Banco con su tipo seleccionado.")
    str_app.stop()

# --- OPERACIONES DE BASE DE DATOS Y FLUJO CENTRAL ---
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
df_mov = pd.read_csv(FILE_DB)

# --- CÁNCULOS DE SALDOS ---
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
str_app.title(f"💳 Control de Gastos - {USER_NAME}")

str_app.session_state.meta_dinamica = str_app.number_input(T["meta_actual"], value=int(str_app.session_state.meta_dinamica), step=1000)

tabs = str_app.tabs([T["tab_reg"], T["tab_res"], T["tab_ia"]])

# --- PESTAÑA REGISTRO ---
with tabs[0]:
    str_app.subheader("🖋️ Registrar Movimiento del Día")
    t_op = str_app.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    c1, c2 = str_app.columns(2)
    if t_op == T["gasto"]:
        f_cat = c1.selectbox(T["cat_label"], CATEGORIAS_SISTEMA, index=3)
        f_cta = c2.selectbox("Pagar desde (Cuenta)", CUENTAS_LISTA)
        f_fec = datetime.now().date()
    else:
        f_cta = c1.selectbox("Destino (Cuenta)", CUENTAS_LISTA)
        f_cat = "INGRESO"
        f_fec = datetime.now().date()
        
    clean_mto = str_app.number_input(T["monto_label"], min_value=0, step=1000, value=None, placeholder="Ej: 15000", key=f"m_{str_app.session_state.get('form_tick', 0)}")
    f_des = str_app.text_input(T["desc_label"], key=f"d_{str_app.session_state.get('form_tick', 0)}").upper()
    
    if str_app.button(T["save_reg"], use_container_width=True):
        if clean_mto and clean_mto > 0 and f_des:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, f_cta, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            str_app.session_state.form_tick = str_app.session_state.get('form_tick', 0) + 1
            str_app.rerun()

# --- PESTAÑA RESUMEN (CALENDARIO INTEGRADO) ---
with tabs[1]:
    if not df_mov.empty and str_app.button(T["undo_btn"]):
        df_mov[:-1].to_csv(FILE_DB, index=False); str_app.rerun()
    
    str_app.metric(T["cap_total"], f"${total_capital:,.0f}".replace(",", "."))
    
    str_app.write("**Saldos de cuentas actuales:**")
    columnas_ctas = str_app.columns(len(CUENTAS_LISTA))
    for i, cta in enumerate(CUENTAS_LISTA):
        columnas_ctas[i].metric(cta, f"${saldos[cta]:,.0f}".replace(",", "."))
    
    str_app.divider()
    str_app.subheader("📊 Análisis por Categoría")
    
    df_gastos = df_mov[df_mov["TIPO"] == "GASTO"].copy()
    if not df_gastos.empty:
        resumen_cat = df_gastos.groupby("CATEGORIA")["MONTO"].sum()
        
        for cat in CATEGORIAS_SISTEMA:
            monto = resumen_cat.get(cat, 0)
            col_c, col_m = str_app.columns([3, 1])
            col_c.write(f"**{cat}**")
            col_m.write(f"${int(monto):,.0f}".replace(",", "."))
            str_app.progress(min(monto / (df_gastos["MONTO"].sum() if df_gastos["MONTO"].sum() > 0 else 1), 1.0))
    else:
        str_app.info("Aún no hay gastos registrados para analizar.")

    # --- LÓGICA DE CALENDARIO MATRICIAL ---
    str_app.divider()
    hoy = datetime.now()
    str_app.subheader(f"📅 Calendario de Vencimientos y Operaciones Diarias: {calendar.month_name[hoy.month].upper()} {hoy.year}")
    
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
    seleccion_interactiva = str_app.dataframe(df_cal_visual, use_container_width=True, hide_index=True, on_select="rerun", selection_mode="single-row")
    
    str_app.caption("Leyenda: ⚪ Sin compromisos | 🔴 Gastos Diarios | 🟢 Ingresos | 🟡 Alertas o Vencimientos")

    filas_seleccionadas = seleccion_interactiva.get("selection", {}).get("rows", [])
    str_app.divider()
    str_app.subheader("📋 Panel de Detalle Automatizado")
    
    if filas_seleccionadas:
        indice_semana = filas_seleccionadas[0]
        semana_elegida = semanas_mes[indice_semana]
        dias_con_datos = [int(d) for d in semana_elegida if d != 0 and len(detalle_dias[int(d)]) > 0]
        
        if dias_con_datos:
            pestanas_dias = str_app.tabs([f"DÍA {d}" for d in dias_con_datos])
            for i, d_activo in enumerate(dias_con_datos):
                with pestanas_dias[i]:
                    str_app.write(f"### 📑 Bitácora Completa del Día {d_activo}")
                    for item in detalle_dias[d_activo]:
                        str_app.markdown(f"* {item}")
        else:
            str_app.info("La semana seleccionada no registra gastos diarios, ingresos ni vencimientos agendados.")
    else:
        str_app.warning("Selecciona haciendo clic arriba en cualquier fila del calendario para cargar dinámicamente el desglose de los días.")

    str_app.divider()
    str_app.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- PESTAÑA IA ---
with tabs[2]:
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
