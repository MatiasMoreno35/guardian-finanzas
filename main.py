import streamlit as st
import pandas as pd
from datetime import datetime
import os
import urllib.parse
from groq import Groq

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Smart Wallet", page_icon="💰", layout="wide")

# --- TRADUCCIONES ---
TEXTS = {
    "es": {
        "config_title": "🚀 Configuración Inicial",
        "name_label": "¿Cómo te llamas?",
        "meta_label": "Meta de ahorro mensual",
        "ctas_label": "Tus cuentas (ej: Billetera, Mach, Destacame)",
        "venc_label": "Gastos con VENCIMIENTO (ej: Colegio, Cuentas)",
        "diario_label": "Gastos DIARIOS (ej: Transporte, Comida)",
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
        "cal_msg": "✅ Registrado. [Agendar en Calendar]",
        "undo_btn": "🔙 DESHACER ÚLTIMO REGISTRO",
        "cap_total": "CAPITAL TOTAL DISPONIBLE",
        "aho_saldo": "SALDO EN AHORRO",
        "lang_label": "Idioma / Idioma"
    },
    "pt": {
        "config_title": "🚀 Configuração Inicial",
        "name_label": "Como você se chama?",
        "meta_label": "Meta de economia mensal",
        "ctas_label": "Suas contas (ex: Carteira, Nubank)",
        "venc_label": "Gastos com VENCIMENTO (ex: Escola, Contas)",
        "diario_label": "Gastos DIÁRIOS (ex: Transporte, Comida)",
        "save_config": "Salvar Configuração",
        "meta_actual": "🎯 Meta de Economia Atual:",
        "reset_btn": "🚨 Reiniciar Sistema",
        "tab_reg": "📝 REGISTRO",
        "tab_aho": "🏦 POUPANÇA",
        "tab_res": "📊 RESUMO",
        "tab_ia": "🕵️ ANALISTA IA",
        "type_op": "Tipo",
        "gasto": "GASTO",
        "ingreso": "RECEITA",
        "cat_label": "Categoria",
        "monto_label": "Valor $",
        "desc_label": "Descrição",
        "save_reg": "💾 SALVAR REGISTRO",
        "cal_msg": "✅ Registrado. [Agendar no Calendar]",
        "undo_btn": "🔙 DESFAZER ÚLTIMO REGISTRO",
        "cap_total": "CAPITAL TOTAL DISPONÍVEL",
        "aho_saldo": "SALDO EM POUPANÇA",
        "lang_label": "Idioma / Idioma"
    }
}

# --- ARCHIVOS ---
FILE_DB = "movimientos_db.csv"
FILE_CONFIG = "config_usuario.csv"

# --- LÓGICA DE IDIOMA ---
if "lang" not in st.session_state:
    st.session_state.lang = "es"

# --- CARGAR CONFIGURACIÓN ---
if os.path.exists(FILE_CONFIG):
    config = pd.read_csv(FILE_CONFIG).iloc[0].to_dict()
    USER_NAME = config["nombre"]
    st.session_state.lang = config.get("idioma", "es")
    T = TEXTS[st.session_state.lang]
    
    if "meta_dinamica" not in st.session_state:
        st.session_state.meta_dinamica = float(config["meta"])
    CUENTAS_LISTA = [c.strip() for c in config["cuentas"].split(",")]
    CAT_VENC = [c.strip() for c in config["cat_vencimiento"].split(",")]
    CAT_DIARIO = [c.strip() for c in config["cat_diarias"].split(",")]
else:
    st.title("🚀 Smart Wallet Setup")
    lang_setup = st.selectbox("Select Language / Selecione o Idioma", ["Español", "Português"])
    current_lang = "es" if lang_setup == "Español" else "pt"
    T = TEXTS[current_lang]
    
    with st.form("config_form"):
        st.subheader(T["config_title"])
        nombre = st.text_input(T["name_label"], placeholder="Ex: Francisco Moreno")
        meta = st.number_input(T["meta_label"], value=0.0, step=10000.0)
        nombres_ctas = st.text_input(T["ctas_label"], placeholder="Billetera, Banco, Ahorro")
        cat_v = st.text_input(T["venc_label"], placeholder="Colegio, Cuentas, Luz")
        cat_d = st.text_input(T["diario_label"], placeholder="Comida, Transporte, Ocio")
        
        if st.form_submit_button(T["save_config"]):
            if nombre and nombres_ctas:
                pd.DataFrame([{
                    "nombre": nombre, "meta": float(meta), "cuentas": nombres_ctas, 
                    "cat_vencimiento": cat_v, "cat_diarias": cat_d, "idioma": current_lang
                }]).to_csv(FILE_CONFIG, index=False)
                st.session_state.lang = current_lang
                st.rerun()
            else:
                st.error("Por favor rellena los campos principales / Por favor preencha os campos")
    st.stop()

# --- INTERFAZ PRINCIPAL ---
T = TEXTS[st.session_state.lang]

# --- BASE DE DATOS ---
if not os.path.exists(FILE_DB):
    pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO']).to_csv(FILE_DB, index=False)
df_mov = pd.read_csv(FILE_DB)

# --- CÁLCULOS ---
saldos = {cta: 0.0 for cta in CUENTAS_LISTA + ["Ahorro"]}
for _, row in df_mov.iterrows():
    try:
        m = float(row['MONTO'])
        tipo, cta = row['TIPO'], row['CUENTA']
        if tipo in ["INGRESO", "RECEITA"]: saldos[cta] += m
        elif tipo == "GASTO": saldos[cta] -= m
        elif tipo == "DEPOSITO AHORRO":
            saldos[cta] -= m
            saldos["Ahorro"] += m
        elif tipo == "RETIRO AHORRO":
            saldos["Ahorro"] -= m
            saldos[cta] += m
    except: continue
total_capital = sum(saldos[c] for c in CUENTAS_LISTA)

# --- CABECERA ---
c_meta, c_reiniciar = st.columns([3, 1])
with c_meta:
    st.session_state.meta_dinamica = st.number_input(T["meta_actual"], value=st.session_state.meta_dinamica, step=10000.0)
with c_reiniciar:
    if st.button(T["reset_btn"], use_container_width=True):
        st.session_state.confirmar_reinicio = True

if st.session_state.get("confirmar_reinicio"):
    col1, col2, col3 = st.columns(3)
    if col1.button("Limpiar Datos"):
        if os.path.exists(FILE_DB): os.remove(FILE_DB)
        st.rerun()
    if col2.button("Reset Total"):
        if os.path.exists(FILE_DB): os.remove(FILE_DB)
        if os.path.exists(FILE_CONFIG): os.remove(FILE_CONFIG)
        st.rerun()
    if col3.button("X"):
        del st.session_state.confirmar_reinicio
        st.rerun()

st.title(f"💳 {USER_NAME} Wallet")
tabs = st.tabs([T["tab_reg"], T["tab_aho"], T["tab_res"], T["tab_ia"]])

# --- PESTAÑA REGISTRO ---
with tabs[0]:
    t_op = st.radio(T["type_op"], [T["gasto"], T["ingreso"]], horizontal=True)
    c1, c2 = st.columns(2)
    
    if t_op == T["gasto"]:
        sub_t = c1.selectbox("Subtipo", ["Vencimiento", "Diario"] if st.session_state.lang == "es" else ["Vencimento", "Diário"])
        f_cat = c1.selectbox(T["cat_label"], CAT_VENC if "Venciment" in sub_t else CAT_DIARIO)
        f_fec = c2.date_input("Fecha/Data") if "Venciment" in sub_t else datetime.now().date()
        f_cta = c1.selectbox("Origen/Origem", CUENTAS_LISTA)
    else:
        f_cta = c1.selectbox("Destino", CUENTAS_LISTA)
        f_fec = datetime.now().date()
        f_cat = "INGRESO"

    raw_mto = st.text_input(T["monto_label"], key=f"m_{st.session_state.get('form_tick', 0)}")
    f_des = st.text_input(T["desc_label"], key=f"d_{st.session_state.get('form_tick', 0)}").upper()

    if st.button(T["save_reg"], use_container_width=True):
        clean_mto = raw_mto.replace(".", "").replace(",", "")
        if clean_mto.isdigit() and int(clean_mto) > 0:
            m_tipo = "GASTO" if t_op == T["gasto"] else "INGRESO"
            nuevo = pd.DataFrame([[str(f_fec), m_tipo, f_cta, f_cat, f_des, int(clean_mto)]], columns=df_mov.columns)
            pd.concat([df_mov, nuevo], ignore_index=True).to_csv(FILE_DB, index=False)
            
            if m_tipo == "GASTO" and f_cat in CAT_VENC:
                p = urllib.parse.urlencode({"action":"TEMPLATE","text":f"PAGAR {f_des}","dates":f"{str(f_fec).replace('-','')}/{str(f_fec).replace('-','')}"})
                st.success(f"{T['cal_msg']} (https://www.google.com/calendar/render?{p})")
            
            st.session_state.form_tick = st.session_state.get('form_tick', 0) + 1
            st.rerun()

# --- PESTAÑA AHORROS ---
with tabs[1]:
    col_a1, col_a2 = st.columns(2)
    with col_a1:
        st.write("⬆️ **Ahorrar / Poupar**")
        acc_ori = st.selectbox("Desde/De:", CUENTAS_LISTA, key="ao")
        mto_dep = st.number_input("Valor:", min_value=0.0, step=5000.0, key="md")
        if st.button("💰 OK"):
            if mto_dep > 0:
                mov = pd.DataFrame([[str(datetime.now().date()), "DEPOSITO AHORRO", acc_ori, "AHORRO 🏦", "TRASPASO", int(mto_dep)]], columns=df_mov.columns)
                pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False)
                st.rerun()
    with col_a2:
        st.write("⬇️ **Retirar**")
        acc_des = st.selectbox("Hacia/Para:", CUENTAS_LISTA, key="ad")
        mto_ret = st.number_input("Valor:", min_value=0.0, step=5000.0, key="mr")
        if st.button("💸 OK"):
            if mto_ret > 0:
                mov = pd.DataFrame([[str(datetime.now().date()), "RETIRO AHORRO", acc_des, "AHORRO 🏦", "RETIRO", int(mto_ret)]], columns=df_mov.columns)
                pd.concat([df_mov, mov], ignore_index=True).to_csv(FILE_DB, index=False)
                st.rerun()

# --- PESTAÑA RESUMEN ---
with tabs[2]:
    if not df_mov.empty and st.button(T["undo_btn"], type="primary"):
        pd.read_csv(FILE_DB)[:-1].to_csv(FILE_DB, index=False)
        st.rerun()

    cols_cta = st.columns(len(CUENTAS_LISTA))
    for i, cta in enumerate(CUENTAS_LISTA):
        cols_cta[i].metric(cta, f"${saldos[cta]:,.0f}")
    
    st.divider()
    c_cap, c_aho = st.columns(2)
    c_cap.metric(T["cap_total"], f"${total_capital:,.0f}")
    diff = saldos['Ahorro'] - st.session_state.meta_dinamica
    c_aho.metric(T["aho_saldo"], f"${saldos['Ahorro']:,.0f}", delta=f"{diff:,.0f}")
    st.dataframe(df_mov.sort_values(by="FECHA", ascending=False), use_container_width=True)

# --- ANALISTA IA ---
with tabs[3]:
    api_key = st.secrets.get("GROQ_API_KEY")
    if api_key:
        client = Groq(api_key=api_key)
        user_ask = st.text_input(f"{USER_NAME}:")
        if user_ask:
            ctx = f"Capital: {total_capital}, Ahorro: {saldos['Ahorro']}, Meta: {st.session_state.meta_dinamica}. Idioma: {st.session_state.lang}"
            chat = client.chat.completions.create(
                messages=[{"role": "system", "content": f"Asesor financiero de {USER_NAME}. Responde en {st.session_state.lang}."},
                          {"role": "user", "content": f"Ctx: {ctx}. Pregunta: {user_ask}"}],
                model="llama-3.1-8b-instant")
            st.info(chat.choices[0].message.content)
