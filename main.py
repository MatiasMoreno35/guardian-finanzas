import streamlit as st
import pandas as pd
import os
from datetime import datetime
from google.colab import drive

# 1. Conexión a Drive y Limpieza de Datos (Reinicio solicitado)
drive.mount('/content/drive')
PATH_BASE = '/content/drive/My Drive/Finanzas_Guardian_2026/'
if not os.path.exists(PATH_BASE):
    os.makedirs(PATH_BASE)

# Archivos (Se sobreescriben para empezar de cero si así lo decides)
FILE_MOVIMIENTOS = PATH_BASE + 'movimientos_v4.csv'
FILE_SALDOS_INICIALES = PATH_BASE + 'saldos_iniciales.csv'

def inicializar_sistema(borrar=False):
    if borrar or not os.path.exists(FILE_MOVIMIENTOS):
        pd.DataFrame(columns=['FECHA', 'TIPO', 'CUENTA', 'CATEGORIA', 'DESC', 'MONTO', 'QUINCENA']).to_csv(FILE_MOVIMIENTOS, index=False)
    if borrar or not os.path.exists(FILE_SALDOS_INICIALES):
        pd.DataFrame(columns=['CUENTA', 'SALDO']).to_csv(FILE_SALDOS_INICIALES, index=False)

# LLAMAR CON TRUE PARA REINICIAR TODO
inicializar_sistema(borrar=False) 

# --- LÓGICA DE IA Y ANÁLISIS ---

def inteligencia_financiera(df_mov, saldos_act):
    total_gastos = df_mov[df_mov['TIPO'] == 'GASTO']['MONTO'].sum()
    total_ingresos = df_mov[df_mov['TIPO'] == 'INGRESO']['MONTO'].sum()
    ahorro_meta = 100000
    
    # Simulación de IA de análisis
    consejos = []
    if total_gastos > (total_ingresos * 0.7):
        consejos.append("⚠️ **IA alerta:** Tus gastos superan el 70% de tus ingresos. Estás en zona de riesgo para tu ahorro de $100k.")
    
    # Análisis de cuentas
    cuenta_baja = [c for c, s in saldos_act.items() if s < 20000]
    if cuenta_baja:
        consejos.append(f"🔌 **IA sugiere:** Tus cuentas {', '.join(cuenta_baja)} están bajo los $20.000. Prioriza usarlas solo para emergencias.")

    return consejos

# --- INTERFAZ STREAMLIT ---

st.set_page_config(page_title="Guardian $100K", page_icon="🛡️")

st.title("🛡️ Guardian Financiero Pro")
st.sidebar.header("Configuración de Cuentas")

# Ingreso de Saldos Actuales (Tu Realidad Hoy)
with st.sidebar.expander("💰 Saldos en mis Cuentas"):
    billetera = st.number_input("Billetera Física", value=0)
    mach = st.number_input("Cuenta Mach", value=0)
    destacame = st.number_input("Cuenta Destácame", value=0)
    if st.button("Actualizar Saldos"):
        df_s = pd.DataFrame([['BILLETERA', billetera], ['MACH', mach], ['DESTACAME', destacame]], columns=['CUENTA', 'SALDO'])
        df_s.to_csv(FILE_SALDOS_INICIALES, index=False)
        st.success("Saldos actualizados")

# Pestañas de la App
tab1, tab2, tab3 = st.tabs(["📝 Registro", "📊 Análisis IA", "🔮 Simulador"])

with tab1:
    st.subheader("Nuevo Movimiento")
    col1, col2 = st.columns(2)
    with col1:
        tipo = st.selectbox("Tipo", ["GASTO", "INGRESO", "AHORRO"])
        cuenta = st.selectbox("Desde/Hacia cuenta", ["BILLETERA", "MACH", "DESTACAME"])
    with col2:
        cat = st.selectbox("Categoría", ["COLEGIO 🏫", "CUOTAS 💳", "CUENTAS 💡", "TRANSPORTE 🚗", "COMIDA 🍕", "VARIOS 🧩"])
        monto = st.number_input("Monto $", min_value=0)
    
    desc = st.text_input("Descripción").upper()
    fecha = st.date_input("Fecha", datetime.now())
    
    if st.button("GUARDAR EN DRIVE"):
        q = "Q1" if fecha.day <= 15 else "Q2"
        df = pd.read_csv(FILE_MOVIMIENTOS)
        nuevo = pd.DataFrame([[fecha, tipo, cuenta, cat, desc, monto, q]], columns=df.columns)
        pd.concat([df, nuevo], ignore_index=True).to_csv(FILE_MOVIMIENTOS, index=False)
        st.balloons()
        st.success(f"Registrado en {cuenta}")

with tab2:
    st.subheader("Análisis de la IA")
    df_mov = pd.read_csv(FILE_MOVIMIENTOS)
    df_s = pd.read_csv(FILE_SALDOS_INICIALES)
    saldos_dict = dict(zip(df_s.CUENTA, df_s.SALDO))
    
    # Mostrar Balance
    total_actual = sum(saldos_dict.values())
    st.metric("Patrimonio Total Actual", f"${total_actual:,.0f}")
    
    # Insights de IA
    mensajes_ia = inteligencia_financiera(df_mov, saldos_dict)
    for msg in mensajes_ia:
        st.info(msg)

    # Gráfico de Gastos
    if not df_mov.empty:
        st.write("Distribución de Gastos")
        df_gastos = df_mov[df_mov['TIPO'] == 'GASTO']
        st.bar_chart(df_gastos.groupby('CATEGORIA')['MONTO'].sum())

with tab3:
    st.subheader("¿Puedo gastar?")
    m_sim = st.number_input("Costo del gasto futuro", value=0)
    if st.button("Consultar IA"):
        total_ahorro_mes = 100000
        if (total_actual - m_sim) < total_ahorro_mes:
            st.error(f"❌ NO. Tu saldo bajaría de los $100.000 de ahorro. Aborta la misión.")
        else:
            st.success(f"✅ SÍ. Te sobrarían ${(total_actual - m_sim - total_ahorro_mes):,.0f} después de tu ahorro.")
