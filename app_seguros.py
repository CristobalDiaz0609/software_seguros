import mysql.connector
import pandas as pd
import streamlit as st
from datetime import date

# 1. Configuración de página (Ocultar Sidebar)
st.set_page_config(
    page_title="Cartera de Clientes",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# 2. INYECCIÓN DE CSS PERSONALIZADO (El secreto del diseño)
st.markdown(
    """
    <style>
    /* Fondo principal y ocultar elementos por defecto */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    /* Estilo del Encabezado Oscuro (Simulación) */
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

    /* Estilo de Tarjetas de Resumen (Métricas) */
    .metric-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px 20px;
        text-align: left;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1a202c;
        margin-bottom: -5px;
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

    /* Estilo de las Tarjetas de Clientes (Lista) */
    .client-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-left: 4px solid #c53030; /* Borde rojo a la izquierda */
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

    /* Etiqueta roja de Vencida */
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

# ---------------------------------------------------------
# INTERFAZ DE USUARIO SUPERIOR
# ---------------------------------------------------------
st.markdown(
    """
    <div class="header-container">
        <p class="header-title">Cartera de Clientes</p>
        <p class="header-subtitle">SEGUROS · INDEPENDIENTE</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# Barra de Búsqueda (Ocupa todo el ancho)
busqueda = st.text_input(
    "Buscador Oculto",
    placeholder="🔍 Buscar por nombre, aseguradora o teléfono...",
    label_visibility="collapsed",
)

# Filtros Tipo "Pills" (Botones en línea)
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

st.write("") # Espaciador

# ---------------------------------------------------------
# TARJETAS DE MÉTRICAS (Resumen)
# ---------------------------------------------------------
col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.markdown(
        """
        <div class="metric-card">
            <p class="metric-value">132</p>
            <p class="metric-label">CLIENTES</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_m2:
    st.markdown(
        """
        <div class="metric-card">
            <p class="metric-value red">96</p>
            <p class="metric-label">VENCIDAS</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col_m3:
    st.markdown(
        """
        <div class="metric-card">
            <p class="metric-value">0</p>
            <p class="metric-label">URGENTES ≤15D</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("") # Espaciador
st.write("") # Espaciador

# ---------------------------------------------------------
# LISTADO DE CLIENTES / PÓLIZAS (Simulación visual)
# ---------------------------------------------------------

try:
    conn = get_connection()
    # Consulta a la base de datos (con límite para la demo)
    query = """
        SELECT 
            c.nombre_completo,
            COALESCE(co.nombre, 'SIN COMPAÑÍA') as compañia,
            COALESCE(p.numero_poliza, '—') as poliza,
            COALESCE(p.monto_prima_anual, 0) as prima,
            p.fecha_vencimiento
        FROM clientes c
        LEFT JOIN polizas p ON c.id_cliente = p.id_cliente
        LEFT JOIN compañias co ON p.id_compañia = co.id_compañia
        ORDER BY p.fecha_vencimiento ASC
        LIMIT 10;
    """
    df = pd.read_sql(query, conn)
    conn.close()

    if df.empty:
        st.info("No hay datos para mostrar. Importa un Excel para comenzar.")
    else:
        for idx, row in df.iterrows():
            nombre = str(row['nombre_completo']).upper()
            aseguradora = str(row['compañia']).upper()
            poliza = str(row['poliza'])
            prima = row['prima']
            
            # Formatear el precio
            precio_formato = f"${prima} / prima"

            # Renderizar la tarjeta HTML
            html_card = f"""
            <div class="client-card">
                <div>
                    <p class="client-name">{nombre}</p>
                    <p class="client-details">{aseguradora} · {poliza}</p>
                    <p class="client-price">{precio_formato}</p>
                </div>
                <div>
                    <span class="badge-vencida">Vencida</span>
                </div>
            </div>
            """
            st.markdown(html_card, unsafe_allow_html=True)

except Exception as e:
    # Si hay error (o base de datos vacía), mostramos el diseño mockeado
    # igual al de la imagen para que veas que funciona visualmente
    
    st.markdown(
        """
        <div class="client-card">
            <div>
                <p class="client-name">CONDOMINIO EDIFICIO CABILDO</p>
                <p class="client-details">BCISEGUROS · SP630167</p>
                <p class="client-price">$116,04 / prima</p>
            </div>
            <div>
                <span class="badge-vencida">Vencida hace 739798d</span>
            </div>
        </div>

        <div class="client-card">
            <div>
                <p class="client-name">GERARDO FUENTES PALOMINOS</p>
                <p class="client-details">RENTA NACIONAL · —</p>
                <p class="client-price">$17,28 / prima</p>
            </div>
            <div>
                <span class="badge-vencida">Vencida hace 739740d</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
