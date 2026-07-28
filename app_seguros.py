from datetime import datetime, timedelta
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

    /* Tarjetas de Métricas */
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

                    # 3. Insertar póliza
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

# FORMULARIO DINÁMICO SEGÚN TIPO DE SEGURO
with col_acc2:
    with st.expander("➕ Crear Nuevo Cliente a Mano"):
        # Selección previa del tipo de seguro (Ramo)
        tipo_seguro = st.selectbox(
            "Selecciona el Tipo de Seguro (Ramo):",
            [
                "🚗 Auto / Vehículo",
                "🏠 Vivienda / Hogar",
                "🏥 Salud / Vida",
                "📋 Otro / General",
            ],
        )

        with st.form("form_nuevo_cliente_dinamico"):
            st.subheader("👤 Datos del Cliente")
            c_rut = st.text_input("RUT", placeholder="12345678-9")
            c_nombre = st.text_input("Nombre Completo")
            c_tel = st.text_input("Teléfono")
            c_email = st.text_input("Correo Electrónico")

            st.subheader("📜 Datos de la Póliza")
            p_comp = st.text_input("Aseguradora (Compañía)", placeholder="SURA")
            p_poliza = st.text_input("N° de Póliza")
            p_venc = st.date_input("Fecha Vencimiento")
            p_prima = st.number_input("Monto Prima", min_value=0.0)
            p_comision = st.number_input("Monto Comisión", min_value=0.0)

            # Campos dinámicos según la selección
            materia_especifica = ""
            if "Auto" in tipo_seguro:
                st.subheader("🚗 Especificación del Vehículo")
                patente = st.text_input(
                    "Patente del Vehículo", placeholder="AA1234"
                )
                modelo = st.text_input(
                    "Marca / Modelo / Año", placeholder="Toyota RAV4 2022"
                )
                materia_especifica = f"Patente: {patente.upper()} - {modelo}"

            elif "Vivienda" in tipo_seguro:
                st.subheader("🏠 Especificación de la Vivienda")
                direccion_prop = st.text_input(
                    "Dirección de la Propiedad",
                    placeholder="Av. Providencia 1234, Dpto 502",
                )
                materia_especifica = f"Propiedad: {direccion_prop}"

            elif "Salud" in tipo_seguro:
                st.subheader("🏥 Especificación de Salud / Vida")
                cargas = st.text_input(
                    "Cargas / Beneficiarios",
                    placeholder="Ej: Cónyuge + 2 Hijos",
                )
                materia_especifica = f"Cobertura: {cargas}"

            else:
                materia_especifica = st.text_input(
                    "Materia Asegurada", placeholder="Descripción general"
                )

            btn_guardar = st.form_submit_button("Guardar Cliente y Póliza")

            if btn_guardar and c_rut and c_nombre:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    # Insertar Cliente
                    cursor.execute(
                        """INSERT INTO clientes (rut, nombre_completo, email, telefono) 
                           VALUES (%s, %s, %s, %s) 
                           ON DUPLICATE KEY UPDATE id_cliente=LAST_INSERT_ID(id_cliente);""",
                        (c_rut, c_nombre, c_email, c_tel),
                    )
                    id_c = cursor.lastrowid

                    # Insertar Compañía
                    cursor.execute(
                        """INSERT INTO compañias (nombre) VALUES (%s) 
                           ON DUPLICATE KEY UPDATE id_compañia=LAST_INSERT_ID(id_compañia);""",
                        (p_comp or "GENERAL",),
                    )
                    id_co = cursor.lastrowid

                    # Extraer nombre limpio del ramo
                    ramo_nombre = tipo_seguro.split(" ")[1]

                    # Insertar Póliza guardando los detalles en 'materia_asegurada'
                    cursor.execute(
                        """INSERT INTO polizas (numero_poliza, id_cliente, id_compañia, ramo, materia_asegurada, fecha_inicio, fecha_vencimiento, monto_prima_anual, monto_comision, estado) 
                           VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s, %s, %s, 'Vigente');""",
                        (
                            p_poliza or "S/N",
                            id_c,
                            id_co,
                            ramo_nombre,
                            materia_especifica,
                            p_venc,
                            p_prima,
                            p_comision,
                        ),
                    )

                    conn.commit()
                    cursor.close()
                    conn.close()
                    st.success(
                        f"¡Cliente **{c_nombre}** y seguro de **{ramo_nombre}** guardados con éxito!"
                    )
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
# CONSULTA DE COMISIONES MES ACTUAL VS MES ANTERIOR
# ---------------------------------------------------------
total_comision_mes_actual = 0.0
total_comision_mes_anterior = 0.0
variacion_comision = 0.0

try:
    conn = get_connection()

    # Cálculo dinámico de fechas
    hoy = datetime.now()
    primer_dia_mes_actual = hoy.replace(day=1).strftime("%Y-%m-%d")

    ultimo_dia_mes_anterior = (hoy.replace(day=1) - timedelta(days=1)).strftime(
        "%Y-%m-%d"
    )
    primer_dia_mes_anterior = (
        (hoy.replace(day=1) - timedelta(days=1))
        .replace(day=1)
        .strftime("%Y-%m-%d")
    )

    # 1. Query general para el listado (incluyendo materia_asegurada)
    query_base = """
        SELECT 
            c.nombre_completo,
            COALESCE(co.nombre, 'SIN COMPAÑÍA') as compañia,
            COALESCE(p.numero_poliza, '—') as poliza,
            COALESCE(p.ramo, 'General') as ramo,
            COALESCE(p.materia_asegurada, '') as materia,
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
        query_base += f" WHERE c.nombre_completo LIKE '%{busqueda}%' OR co.nombre LIKE '%{busqueda}%' OR p.numero_poliza LIKE '%{busqueda}%' OR p.materia_asegurada LIKE '%{busqueda}%'"

    query_base += " ORDER BY p.fecha_vencimiento ASC;"

    df = pd.read_sql(query_base, conn)

    # 2. Queries para KPIs comparativos
    query_mes_actual = f"""
        SELECT COALESCE(SUM(monto_comision), 0) as total 
        FROM polizas 
        WHERE fecha_vencimiento >= '{primer_dia_mes_actual}' 
          AND fecha_vencimiento <= LAST_DAY('{primer_dia_mes_actual}');
    """

    query_mes_anterior = f"""
        SELECT COALESCE(SUM(monto_comision), 0) as total 
        FROM polizas 
        WHERE fecha_vencimiento >= '{primer_dia_mes_anterior}' 
          AND fecha_vencimiento <= '{ultimo_dia_mes_anterior}';
    """

    df_actual = pd.read_sql(query_mes_actual, conn)
    df_anterior = pd.read_sql(query_mes_anterior, conn)
    conn.close()

    total_comision_mes_actual = float(df_actual["total"].iloc[0])
    total_comision_mes_anterior = float(df_anterior["total"].iloc[0])
    variacion_comision = (
        total_comision_mes_actual - total_comision_mes_anterior
    )

except Exception as e:
    df = pd.DataFrame()

# ---------------------------------------------------------
# TARJETAS DE MÉTRICAS (KPIs COMPARATIVOS)
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
            <p class="metric-value green">${total_comision_mes_actual:,.2f}</p>
            <p class="metric-label">COMISIÓN ESTE MES</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m3:
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="metric-value">${total_comision_mes_anterior:,.2f}</p>
            <p class="metric-label">COMISIÓN MES ANTERIOR</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_m4:
    color_var = "green" if variacion_comision >= 0 else "red"
    signo = "+" if variacion_comision >= 0 else ""
    st.markdown(
        f"""
        <div class="metric-card">
            <p class="metric-value {color_var}">{signo}${variacion_comision:,.2f}</p>
            <p class="metric-label">DIFERENCIA MENSUAL</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

st.write("")
st.write("")

# ---------------------------------------------------------
# LISTADO CON DETALLE DINÁMICO
# ---------------------------------------------------------
if not df.empty:
    for idx, row in df.iterrows():
        nombre = str(row["nombre_completo"]).upper()
        aseguradora = str(row["compañia"]).upper()
        poliza = str(row["poliza"])
        ramo = str(row["ramo"]).upper()
        materia = str(row["materia"])
        prima = row["prima"]
        comision_real = row["comision"]
        moneda = row["moneda"]

        # Mostrar la materia asegurada si existe (Patente, Dirección, Cargas)
        detalle_materia = f" ({materia})" if materia else ""

        html_card = f"""
        <div class="client-card">
            <div>
                <p class="client-name">{nombre}</p>
                <p class="client-details">{aseguradora} · {poliza} · <span style="color:#1a3644; font-weight:600;">{ramo}</span>{detalle_materia}</p>
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
