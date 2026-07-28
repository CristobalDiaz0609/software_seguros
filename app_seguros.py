import mysql.connector
import pandas as pd
import streamlit as st

# 1. Configuración de página
st.set_page_config(
    page_title="Cartera de Clientes & Comisiones",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. INYECCIÓN DE CSS PERSONALIZADO
st.markdown(
    """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    .header-container {
        background-color: #1a3644;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
    }
    .header-title {
        font-size: 24px;
        font-weight: 700;
        margin: 0;
    }
    .header-subtitle {
        font-size: 12px;
        color: #a0aec0;
        margin-top: -5px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Tarjetas de Métricas Métricas Financieras */
    .metric-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px 20px;
        text-align: left;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 26px;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: -5px;
    }
    .metric-value.green {
        color: #2f855a;
    }
    .metric-value.red {
        color: #c53030;
    }
    .metric-label {
        font-size: 11px;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }

    /* Tarjetas de Lista */
    .client-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #c53030;
        border-radius: 8px;
        padding: 16px 20px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .client-name {
        font-size: 16px;
        font-weight: 700;
        color: #1a202c;
        margin: 0 0 4px 0;
    }
    .client-details {
        font-size: 13px;
        color: #718096;
        margin: 0 0 6px 0;
    }
    .client-price {
        font-size: 13px;
        font-weight: 600;
        color: #2d3748;
        margin: 0;
    }
    .badge-vencida {
        background-color: #c53030;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 3. CONEXIÓN A BASE DE DATOS
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=int(st.secrets["mysql"]["port"]),
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
    )


# Encabezado
st.markdown(
    """
    <div class="header-container">
        <p class="header-title">Cartera de Clientes</p>
        <p class="header-subtitle">SEGUROS · INDEPENDIENTE</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Buscador Principal
busqueda = st.text_input(
    "Buscador Oculto",
    placeholder="🔍 Buscar por nombre, aseguradora o teléfono...",
    label_visibility="collapsed",
)

# Filtros Pills
col_f1, col_f2, col_f3, col_f4, col_f5 = st.columns([1, 1.2, 1.5, 1.5, 1])
with col_f1:
    st.button("Todos", use_container_width=True)
with col_f2:
    st.button("Vencidas", use_container_width=True)
with col_f3:
    st.button("Vence ≤15 días", use_container_width=True)
with col_f4:
    st.button("Vence ≤30 días", use_container_width=True)
with col_f5:
    st.button("Al día", use_container_width=True)

st.write("")

# ---------------------------------------------------------
# CONSULTA A LA BD & CÁLCULO DE COMISIONES
# ---------------------------------------------------------
total_comision_cartera = 0.0
total_comision_vencida = 0.0
pólizas_vencidas_cnt = 0

try:
    conn = get_connection()
    # Consulta trayendo primas y estado
    query = """
        SELECT 
            c.nombre_completo,
            COALESCE(co.nombre, 'SIN COMPAÑÍA') as compañia,
            COALESCE(p.numero_poliza, '—') as poliza,
            COALESCE(p.monto_prima_anual, 0) as prima,
            COALESCE(p.moneda, 'UF') as moneda,
            p.estado,
            p.fecha_vencimiento
        FROM clientes c
        LEFT JOIN polizas p ON c.id_cliente = p.id_cliente
        LEFT JOIN compañias co ON p.id_compañia = co.id_compañia;
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        # Porcentaje promedio de comisión por defecto (12% si no está definido individualmente)
        PORCENTAJE_COMISION = 0.12

        # Asumimos que la comisión estimada es el 12% de la prima
        df["comision"] = df["prima"] * PORCENTAJE_COMISION

        total_comision_cartera = df["comision"].sum()

        # Filtrar comisión en riesgo (Vencidas)
        df_vencidas = df[df["estado"] == "Vencida"]
        total_comision_vencida = df_vencidas["comision"].sum()
        pólizas_vencidas_cnt = len(df_vencidas)

except Exception as e:
    df = pd.DataFrame()

# ---------------------------------------------------------
# TARJETAS DE MÉTRICAS (FINANCIERAS & COMISIONES)
# ---------------------------------------------------------
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(
        """
        <div class="metric-card">
            <p class="metric-value">—</p>
            <p class="metric-label">CLIENTES</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m2:
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="metric-value green">${total_comision_cartera:,.2f}</p>
            <p class="metric-label">COMISIÓN CARTERA (EST.)</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="metric-value red">${total_comision_vencida:,.2f}</p>
            <p class="metric-label">COMISIÓN EN RIESGO</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m4:
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="metric-value red">{pólizas_vencidas_cnt}</p>
            <p class="metric-label">PÓLIZAS VENCIDAS</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.write("")

# ---------------------------------------------------------
# RENDERIZADO DE LAS TARJETAS DE CLIENTE
# ---------------------------------------------------------
if not df.empty:
    for idx, row in df.iterrows():
        nombre = str(row["nombre_completo"]).upper()
        aseguradora = str(row["compañia"]).upper()
        poliza = str(row["poliza"])
        prima = row["prima"]
        comision_item = row.get("comision", prima * 0.12)
        moneda = row["moneda"]

        html_card = f"""
        <div class="client-card">
            <div>
                <p class="client-name">{nombre}</p>
                <p class="client-details">{aseguradora} · {poliza}</p>
                <p class="client-price">${prima:,.2f} {moneda} / prima <span style="color:#2f855a; font-size:12px; margin-left:10px;">(Comisión: ${comision_item:,.2f})</span></p>
            </div>
            <div>
                <span class="badge-vencida">Vencida</span>
            </div>
        </div>
        """
        st.markdown(html_card, unsafe_allow_html=True)
else:
    st.info("Sin registros para mostrar. Los datos se actualizarán al conectar.")
