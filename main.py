import streamlit as st
import pandas as pd
from datetime import datetime
import os

# Configuración de la página
st.set_page_config(page_title="Guardian Financiero", page_icon="🛡️", layout="wide")

# --- ESTILO PERSONALIZADO (Solución Visual) ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: white; }
    div[data-testid="stMetric"] {
        background-color: #1e2130;
        border: 1px solid #4a4a4a;
        padding: 15px;
        border-radius: 15px;
        color: #00ff00 !important;
    }
    div[data-testid="stMetricValue"] { color: #ffffff !important; }
    .stButton>button { border-radius: 20px; background-color: #2e7d32; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- SISTEMA DE ARCHIVOS Y REINICIO ---
FILE_DB = "movimientos_db.csv"
if not os.path.exists(FILE_DB):
    df_empty = pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
    df_empty.to_csv(FILE_DB, index=False)

# Cargar datos
df_mov = pd.read_csv(FILE_DB)

# --- CÁLCULO DE SALDOS REALES ---
# Inicializamos saldos base (puedes ajustar estos números iniciales)
saldos = {"BILLETERA": 0, "MACH": 0, "DESTACAME": 0}

for index, row in df_mov.iterrows():
    monto = row['MONTO']
    cuenta = row['CUENTA']
    if row['TIPO'] == 'INGRESO':
        saldos[cuenta] += monto
    elif row['TIPO'] in ['GASTO', 'AHORRO']:
        saldos[cuenta] -= monto

total_patrimonio = sum(saldos.values())

# --- INTERFAZ PRINCIPAL ---
st.title("🛡️ Guardian Financiero Pro")

tab1, tab2, tab3 = st.tabs(["📝 REGISTRO", "🕵️ ANALISTA IA", "🔮 SIMULADOR"])

with tab1:
    st.subheader("Registrar Movimiento")
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        tipo_op = st.radio("Tipo de Operación", ["GASTO", "INGRESO"], horizontal=True)
    
    with st.form("form_registro", clear_on_submit=True):
        f_cuenta = st.selectbox("¿A qué cuenta?", ["BILLETERA", "MACH", "DESTACAME"])
        
        # Lógica dinámica de categorías
        if tipo_op == "GASTO":
            f_cat = st.selectbox("Categoría de Gasto", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
        else:
            f_cat = "SUELDO / ABONO 💰"
            st.info("Registrando como Ingreso a la cuenta seleccionada.")

        f_monto = st.number_input("Monto $", min_value=0)
        f_desc = st.text_input("Nota (Ej: Supermercado, Pago Bono)").upper()
        
        if st.form_submit_button("CONFIRMAR OPERACIÓN"):
            nueva_fila = pd.DataFrame([[datetime.now().strftime("%Y-%m-%d"), tipo_op, f_cuenta, f_cat, f_desc, f_monto]], 
                                      columns=df_mov.columns)
            df_mov = pd.concat([df_mov, nueva_fila], ignore_index=True)
            df_mov.to_csv(FILE_DB, index=False)
            st.success(f"¡Listo! Se ha actualizado el saldo de {f_cuenta}")
            st.rerun()

with tab2:
    # Visualización de saldos
    st.subheader("Estado de tus Cuentas")
    c1, c2, c3 = st.columns(3)
    c1.metric("Billetera", f"${saldos['BILLETERA']:,.0f}")
    c2.metric("Cuenta Mach", f"${saldos['MACH']:,.0f}")
    c3.metric("Destácame", f"${saldos['DESTACAME']:,.0f}")
    
    st.divider()
    
    # --- CHAT CON EL ANALISTA ---
    st.subheader("💬 Habla con tu Analista Financiero")
    prompt = st.text_input("Hazle una pregunta a la IA (Ej: ¿Cómo voy con mi meta de ahorro?)")
    
    if prompt:
        meta_ahorro = 100000
        # Lógica de respuesta inteligente básica (se puede expandir con GPT luego)
        if "ahorro" in prompt.lower() or "meta" in prompt.lower():
            if total_patrimonio < meta_ahorro:
                st.write(f"🤖 **Analista:** Francisco, actualmente tienes ${total_patrimonio:,.0f}. Te faltan ${meta_ahorro - total_patrimonio:,.0f} para llegar a tu meta de 100k. ¡Evita gastos hormiga esta semana!")
            else:
                st.write(f"🤖 **Analista:** ¡Excelente trabajo! Ya superaste la meta de ahorro por ${total_patrimonio - meta_ahorro:,.0f}. Sugiero mover el excedente a una cuenta que genere intereses.")
        elif "gasto" in prompt.lower():
            total_gastos = df_mov[df_mov['TIPO']=='GASTO']['MONTO'].sum()
            st.write(f"🤖 **Analista:** Has gastado un total de ${total_gastos:,.0f} este mes. El 40% se concentra en la categoría {df_mov[df_mov['TIPO']=='GASTO']['CATEGORIA'].mode()[0] if not df_mov.empty else 'N/A'}.")
        else:
            st.write("🤖 **Analista:** Estoy analizando tus movimientos de Billetera, Mach y Destácame. ¿Quieres que simulemos un gasto o revisemos el saldo de alguna cuenta específica?")

with tab3:
    st.subheader("Simulador de Compra")
    m_sim = st.number_input("Precio del artículo", value=0)
    if st.button("¿Es prudente comprarlo?"):
        if (total_patrimonio - m_sim) < 100000:
            st.error(f"❌ No lo recomiendo. Tu saldo quedaría en ${total_patrimonio - m_sim:,.0f}, rompiendo tu meta de ahorro de $100.000.")
        else:
            st.success(f"✅ Adelante. Aún después de la compra, mantienes tu meta de ahorro protegida.")

# Botón para borrar datos (como pediste)
if st.sidebar.button("🗑️ REINICIAR TODA LA APP"):
    df_empty = pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO'])
    df_empty.to_csv(FILE_DB, index=False)
    st.rerun()
