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

# 2. CSS Personalizado (Look & Feel SaaS)
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
    }
    .header-title { font-size: 24px; font-weight: 700; margin: 0; }
    .header-subtitle { font-size: 12px; color: #a0aec0; margin-top: -5px; text-transform: uppercase; letter-spacing: 1px; }

    .metric-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 15px 20px;
        text-align: left;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-value { font-size: 26px; font-weight: 700; color: #1a202c; margin-bottom: -5px; }
    .metric-value.green { color: #2f855a; }
    .metric-value.red { color: #c53030; }
    .metric-label { font-size: 11px; color: #718096; text-transform: uppercase; letter-spacing: 0.5px; }

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
    .client-name { font-size: 16px; font-weight: 700; color: #1a202c; margin: 0 0 4px 0; }
    .client-details { font-size: 13px; color: #718096; margin: 0 0 6px 0; }
    .client-price { font-size: 13px; font-weight: 600; color: #2d3748; margin: 0; }
    .badge-vencida { background-color: #c53030; color: white; padding: 4px 10px; border-radius: 12px; font-size: 11px; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


# 3. Conexión a BD en Aiven
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=int(st.secrets["mysql"]["port"]),
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
    )


# Encabezado principal
st.markdown(
    """
    <div class="header-container">
        <p class="header-title">Cartera de Clientes</p>
        <p class="header-subtitle">SEGUROS · INDEPENDIENTE</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------
# MÓDULO DE IMPORTACIÓN DE EXCEL INTELIGENTE
# ---------------------------------------------------------
col_acc1, col_acc2 = st.columns([1, 1])

with col_acc1:
    with st.expander("📥 Subir Planilla Excel"):
        st.caption("Carga tu archivo de cartera (.xlsx) en cualquier formato.")
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo Excel (.xlsx)", type=["xlsx", "xls"]
        )

        if uploaded_file:
            try:
                # 1. Leer primeras filas para encontrar la cabecera real
                df_raw = pd.read_excel(uploaded_file)

                header_row = 0
                if "Unnamed:" in str(df_raw.columns[0]):
                    for idx in range(min(15, len(df_raw))):
                        row_text = (
                            " ".join(df_raw.iloc[idx].astype(str))
                            .lower()
                            .strip()
                        )
                        if any(
                            k in row_text
                            for k in [
                                "compa",
                                "corredor",
                                "vigencia",
                                "nombre",
                                "cliente",
                                "ren.",
                            ]
                        ):
                            header_row = idx + 1
                            break
                    df_excel = pd.read_excel(uploaded_file, header=header_row)
                else:
                    df_excel = df_raw

                # Limpieza de filas vacías
                df_excel = df_excel.dropna(how="all").reset_index(drop=True)

                # 2. Mapeo dinámico de nombres de columnas
                col_map = {}
                for col in df_excel.columns:
                    c_clean = str(col).strip().lower()
                    if "compa" in c_clean:
                        col_map[col] = "Compañia"
                    elif (
                        "vigencia" in c_clean
                        or "venc" in c_clean
                        or "ren." in c_clean
                    ):
                        col_map[col] = "Vencimiento"
                    elif (
                        "nombre" in c_clean
                        or "cliente" in c_clean
                        or "corredor" in c_clean
                    ):
                        col_map[col] = "Nombre"
                    elif "prima" in c_clean:
                        col_map[col] = "Prima"
                    elif "comision" in c_clean or "comisi" in c_clean:
                        col_map[col] = "Comision"
                    elif "poliza" in c_clean or "póliza" in c_clean:
                        col_map[col] = "Poliza"
                    elif "ramo" in c_clean or "tipo" in c_clean:
                        col_map[col] = "Ramo"

                df_excel = df_excel.rename(columns=col_map)

                st.write("🔍 **Vista previa procesada (Encabezados detectados):**")
                st.dataframe(df_excel.head(5), use_container_width=True)

                if st.button("🚀 Confirmar e Importar a Aiven"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    registros_procesados = 0

                    for _, row in df_excel.iterrows():
                        rut_val = str(row.get("RUT", "SIN RUT")).strip()
                        nombre_val = str(
                            row.get("Nombre", "CLIENTE SIN NOMBRE")
                        ).strip()
                        tel_val = str(row.get("Telefono", "")).strip()
                        email_val = str(row.get("Email", "")).strip()
                        comp_val = str(row.get("Compañia", "GENERAL")).strip()
                        poliza_val = str(row.get("Poliza", "S/N")).strip()
                        ramo_val = str(row.get("Ramo", "General")).strip()

                        # Manejo seguro de fechas
                        raw_venc = row.get("Vencimiento")
                        try:
                            venc_val = pd.to_datetime(raw_venc).strftime(
                                "%Y-%m-%d"
                            )
                        except Exception:
                            venc_val = datetime.now().strftime("%Y-%m-%d")

                        # Manejo numérico
                        try:
                            prima_val = float(row.get("Prima", 0))
                        except (ValueError, TypeError):
                            prima_val = 0.0

                        try:
                            comision_val = float(row.get("Comision", 0))
                        except (ValueError, TypeError):
                            comision_val = 0.0

                        # Insertar Cliente
                        cursor.execute(
                            "INSERT INTO clientes (rut, nombre_completo, email, telefono) VALUES (%s, %s, %s, %s);",
                            (rut_val, nombre_val, email_val, tel_val),
                        )
                        id_cliente = cursor.lastrowid

                        # Insertar Compañía
                        cursor.execute(
                            "INSERT INTO compañias (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id_compañia=LAST_INSERT_ID(id_compañia);",
                            (comp_val,),
                        )
                        id_comp = cursor.lastrowid

                        # Insertar Póliza
                        cursor.execute(
                            """INSERT INTO polizas (numero_poliza, id_cliente, id_compañia, ramo, fecha_inicio, fecha_vencimiento, monto_prima_anual, monto_comision, estado)
                               VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, %s, %s, 'Vencida');""",
                            (
                                poliza_val,
                                id_cliente,
                                id_comp,
                                ramo_val,
                                venc_val,
                                prima_val,
                                comision_val,
                            ),
                        )

                        registros_procesados += 1

                    conn.commit()
                    cursor.close()
                    conn.close()

                    st.success(
                        f"🎉 ¡Se importaron {registros_procesados} pólizas correctamente a Aiven!"
                    )
                    st.rerun()

            except Exception as e:
                st.error(f"Error procesando el archivo Excel: {e}")

# Módulo de creación manual
with col_acc2:
    with st.expander("➕ Crear Nuevo Cliente a Mano"):
        tipo_seguro = st.selectbox(
            "Tipo de Seguro (Ramo):",
            [
                "🚗 Auto / Vehículo",
                "🏠 Vivienda / Hogar",
                "🏥 Salud / Vida",
                "📋 Otro / General",
            ],
        )

        with st.form("form_nuevo_cliente"):
            c_nombre = st.text_input(
                "Nombre Completo del Cliente", placeholder="Ej: Juan Pérez Soto"
            )
            c_tel = st.text_input("Teléfono de Contacto")
            c_email = st.text_input("Correo Electrónico")

            p_comp = st.text_input("Aseguradora", placeholder="SURA")
            p_poliza = st.text_input("N° de Póliza")
            p_venc = st.date_input("Fecha Vencimiento")
            p_prima = st.number_input("Monto Prima", min_value=0.0)
            p_comision = st.number_input("Monto Comisión", min_value=0.0)

            materia_especifica = ""
            if "Auto" in tipo_seguro:
                patente = st.text_input("Patente", placeholder="AA1234")
                modelo = st.text_input(
                    "Modelo / Año", placeholder="Toyota RAV4 2022"
                )
                materia_especifica = f"Patente: {patente.upper()} - {modelo}"
            elif "Vivienda" in tipo_seguro:
                direccion_prop = st.text_input(
                    "Dirección Propiedad",
                    placeholder="Av. Providencia 1234, Dpto 502",
                )
                materia_especifica = f"Propiedad: {direccion_prop}"
            elif "Salud" in tipo_seguro:
                cargas = st.text_input(
                    "Cargas / Beneficiarios",
                    placeholder="Ej: Cónyuge + 2 Hijos",
                )
                materia_especifica = f"Cobertura: {cargas}"
            else:
                materia_especifica = st.text_input(
                    "Materia Asegurada", placeholder="Descripción general"
                )

            btn_guardar = st.form_submit_button("Guardar en Sistema")

            if btn_guardar and c_nombre:
                try:
                    conn = get_connection()
                    cursor = conn.cursor()

                    cursor.execute(
                        "INSERT INTO clientes (rut, nombre_completo, email, telefono) VALUES ('SIN RUT', %s, %s, %s);",
                        (c_nombre, c_email, c_tel),
                    )
                    id_c = cursor.lastrowid

                    cursor.execute(
                        "INSERT INTO compañias (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id_compañia=LAST_INSERT_ID(id_compañia);",
                        (p_comp or "GENERAL",),
                    )
                    id_co = cursor.lastrowid

                    ramo_nombre = tipo_seguro.split(" ")[1]

                    cursor.execute(
                        "INSERT INTO polizas (numero_poliza, id_cliente, id_compañia, ramo, materia_asegurada, fecha_inicio, fecha_vencimiento, monto_prima_anual, monto_comision, estado) VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s, %s, %s, 'Vigente');",
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
                    st.success(f"¡Cliente **{c_nombre}** guardado con éxito!")
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
# CÁLCULOS Y LISTADO DE CLIENTES
# ---------------------------------------------------------
total_comision_mes_actual = 0.0
total_comision_mes_anterior = 0.0
variacion_comision = 0.0

try:
    conn = get_connection()

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

    query_mes_actual = f"SELECT COALESCE(SUM(monto_comision), 0) as total FROM polizas WHERE fecha_vencimiento >= '{primer_dia_mes_actual}' AND fecha_vencimiento <= LAST_DAY('{primer_dia_mes_actual}');"
    query_mes_anterior = f"SELECT COALESCE(SUM(monto_comision), 0) as total FROM polizas WHERE fecha_vencimiento >= '{primer_dia_mes_anterior}' AND fecha_vencimiento <= '{ultimo_dia_mes_anterior}';"

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

# Tarjetas Métricas
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(
        """<div class="metric-card"><p class="metric-value">—</p><p class="metric-label">CLIENTES</p></div>""",
        unsafe_allow_html=True,
    )

with col_m2:
    st.markdown(
        f"""<div class="metric-card"><p class="metric-value green">${total_comision_mes_actual:,.2f}</p><p class="metric-label">COMISIÓN ESTE MES</p></div>""",
        unsafe_allow_html=True,
    )

with col_m3:
    st.markdown(
        f"""<div class="metric-card"><p class="metric-value">${total_comision_mes_anterior:,.2f}</p><p class="metric-label">COMISIÓN MES ANTERIOR</p></div>""",
        unsafe_allow_html=True,
    )

with col_m4:
    color_var = "green" if variacion_comision >= 0 else "red"
    signo = "+" if variacion_comision >= 0 else ""
    st.markdown(
        f"""<div class="metric-card"><p class="metric-value {color_var}">{signo}${variacion_comision:,.2f}</p><p class="metric-label">DIFERENCIA MENSUAL</p></div>""",
        unsafe_allow_html=True,
    )

st.write("")
st.write("")

# Renderizado del listado
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
        "No hay registros. Sube una planilla Excel o ingresa un cliente a mano para comenzar."
    )
