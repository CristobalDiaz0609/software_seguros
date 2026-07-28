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
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }

    .header-container {
        background-color: #1a3644;
        color: white;
        padding: 20px;
        border-radius: 10px;
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
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

    /* Tarjetas de Resumen */
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
    .metric-value.green { color: #2f855a; }
    .metric-value.red { color: #c53030; }
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
        <div>
            <p class="header-title">Cartera de Clientes</p>
            <p class="header-subtitle">SEGUROS · INDEPENDIENTE</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# BARRA DE HERRAMIENTAS (Acciones rápidas)
# ---------------------------------------------------------
col_acc1, col_acc2 = st.columns([1, 1])

with col_acc1:
    with st.expander("📥 Subir Excel de Clientes / Pólizas"):
        st.write(
            "El archivo Excel debe contener las columnas: **RUT, Nombre, Telefono, Email, Compañia, Poliza, Ramo, Vencimiento, Prima, Comision**"
        )
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo Excel", type=["xlsx", "xls"]
        )

        if uploaded_file and st.button("Procesar e Importar"):
            try:
                df_excel = pd.read_excel(uploaded_file)
                conn = get_connection()
                cursor = conn.cursor()

                for _, row in df_excel.iterrows():
                    # 1. Insertar o actualizar cliente
                    sql_cli = """
                        INSERT INTO clientes (rut, nombre_completo, email, telefono)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE id_cliente=LAST_INSERT_ID(id_cliente);
                    """
                    cursor.execute(
                        sql_cli,
                        (
                            str(row.get("RUT", "")),
                            str(row.get("Nombre", "")),
                            str(row.get("Email", "")),
                            str(row.get("Telefono", "")),
                        ),
                    )
                    id_cliente = cursor.lastrowid

                    # 2. Insertar compañía
                    sql_comp = """
                        INSERT INTO compañias (nombre) VALUES (%s)
                        ON DUPLICATE KEY UPDATE id_compañia=LAST_INSERT_ID(id_compañia);
                    """
                    cursor.execute(
                        sql_comp, (str(row.get("Compañia", "OTRA")),)
                    )
                    id_comp = cursor.lastrowid

                    # 3. Insertar póliza con comisión leída del Excel
                    sql_pol = """
                        INSERT INTO polizas (numero_poliza, id_cliente, id_compañia, ramo, fecha_inicio, fecha_vencimiento, monto_prima_anual, monto_comision, estado)
                        VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, %s, %s, 'Vencida');
                    """
                    cursor.execute(
                        sql_pol,
                        (
                            str(row.get("Poliza", "SN")),
                            id_cliente,
                            id_comp,
                            str(row.get("Ramo", "General")),
                            row.get("Vencimiento"),
                            float(row.get("Prima", 0)),
                            float(row.get("Comision", 0)),
                        ),
                    )

                conn.commit()
                cursor.close()
                conn.close()
                st.success("¡Datos importados con éxito a Aiven!")
                st.rerun()
            except Exception as e:
                st.error(f"Error al importar: {e}")

with col_acc2:
    with st.expander("➕ Crear Nuevo Cliente a Mano"):
        with st.form("form_nuevo_cliente"):
            f_rut = st.text_input("RUT", placeholder="12345678-9")
            f_nombre = st.text_input("Nombre Completo")
            f_tel = st.text_input("Teléfono")
            f_comp = st.text_input("Aseguradora (Compañía)", placeholder="SURA")
            f_poliza = st.text_input("N° de Póliza")
            f_venc = st.date_input("Fecha Vencimiento")
            f_prima = st.number_input("Monto Prima", min_value=0.0)
            f_comision = st.number_input(
                "Monto Comisión Directa", min_value=0.0
            )

            btn_guardar = st.form_submit_button("Guardar en Sistema")

            if btn_guardar and f_rut and f_nombre:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    # Insertar Cliente
                    cursor.execute(
                        "INSERT INTO clientes (rut, nombre_completo, telefono) VALUES (%s, %s, %s) ON DUPLICATE KEY UPDATE id_cliente=LAST_INSERT_ID(id_cliente);",
                        (f_rut, f_nombre, f_tel),
                    )
                    id_c = cursor.lastrowid

                    # Insertar Compañía
                    cursor.execute(
                        "INSERT INTO compañias (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id_compañia=LAST_INSERT_ID(id_compañia);",
                        (f_comp or "GENERAL",),
                    )
                    id_co = cursor.lastrowid

                    # Insertar Póliza
                    cursor.execute(
                        """INSERT INTO polizas (numero_poliza, id_cliente, id_compañia, ramo, fecha_inicio, fecha_vencimiento, monto_prima_anual, monto_comision, estado) 
                           VALUES (%s, %s, %s, 'General', CURRENT_DATE, %s, %s, %s, 'Vigente');""",
                        (
                            f_poliza or "S/N",
                            id_c,
                            id_co,
                            f_venc,
                            f_prima,
                            f_comision,
                        ),
                    )

                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(f"¡Cliente {f_nombre} guardado correctamente!")
                    st.rerun()
                except Exception as err:
                    st.error(f"Error al guardar: {err}")

st.write("")

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
# CONSULTA DE COMISIONES DIRECTAS
# ---------------------------------------------------------
total_comision_cartera = 0.0
total_comision_vencida = 0.0
pólizas_vencidas_cnt = 0

try:
    conn = get_connection()
    query = """
        SELECT 
            c.nombre_completo,
            COALESCE(co.nombre, 'SIN COMPAÑÍA') as compañia,
            COALESCE(p.numero_poliza, '—') as poliza,
            COALESCE(p.monto_prima_anual, 0) as prima,
            COALESCE(p.monto_comision, 0) as comision,
            COALESCE(p.moneda, 'UF') as moneda,
            p.estado,
            p.fecha_vencimiento
        FROM clientes c
        LEFT JOIN polizas p ON c.id_cliente = p.id_cliente
        LEFT JOIN compañias co ON p.id_compañia = co.id_compañia
    """

    if busqueda:
        query += f" WHERE c.nombre_completo LIKE '%{busqueda}%' OR co.nombre LIKE '%{busqueda}%' OR p.numero_poliza LIKE '%{busqueda}%'"

    query += " ORDER BY p.fecha_vencimiento ASC;"

    df = pd.read_sql(query, conn)
    conn.close()

    if not df.empty:
        total_comision_cartera = df["comision"].sum()
        df_vencidas = df[df["estado"] == "Vencida"]
        total_comision_vencida = df_vencidas["comision"].sum()
        pólizas_vencidas_cnt = len(df_vencidas)

except Exception as e:
    df = pd.DataFrame()

# ---------------------------------------------------------
# TARJETAS DE MÉTRICAS (Comisión leída directamente)
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
            <p class="metric-label">COMISIÓN CARTERA</p>
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
# LISTADO
# ---------------------------------------------------------
if not df.empty:
    for idx, row in df.iterrows():
        nombre = str(row["nombre_completo"]).upper()
        aseguradora = str(row["compañia"]).upper()
        poliza = str(row["poliza"])
        prima = row["prima"]
        comision_real = row["comision"]
        moneda = row["moneda"]

        html_card = f"""
        <div class="client-card">
            <div>
                <p class="client-name">{nombre}</p>
                <p class="client-details">{aseguradora} · {poliza}</p>
                <p class="client-price">${prima:,.2f} {moneda} / prima <span style="color:#2f855a; font-size:12px; margin-left:10px;">(Comisión: ${comision_real:,.2f})</span></p>
            </div>
            <div>
                <span class="badge-vencida">Vencida</span>
            </div>
        </div>
        """
        st.markdown(html_card, unsafe_allow_html=True)
else:
    st.info(
        "No se encontraron registros. Usa los módulos de arriba para subir tu Excel o ingresar un cliente a mano."
    )
