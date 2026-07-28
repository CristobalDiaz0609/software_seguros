import re
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

# 2. CSS Personalizado
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
        background: linear-gradient(135deg, #1a3644 0%, #2a4d60 100%);
        color: white;
        padding: 22px 25px;
        border-radius: 12px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    }
    .header-title { font-size: 26px; font-weight: 800; margin: 0; letter-spacing: -0.5px; }
    .header-subtitle { font-size: 12px; color: #cbd5e0; margin-top: -3px; text-transform: uppercase; letter-spacing: 1.5px; }

    .metric-card {
        background-color: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 16px 20px;
        text-align: left;
        box-shadow: 0 2px 5px rgba(0,0,0,0.03);
    }
    .metric-value { font-size: 26px; font-weight: 800; color: #1a202c; margin-bottom: -5px; }
    .metric-value.green { color: #276749; }
    .metric-value.red { color: #9b2c2c; }
    .metric-label { font-size: 11px; color: #718096; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }

    .edit-box {
        background-color: #f8fafc;
        border-left: 5px solid #2b6cb0;
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .badge-section {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 12px;
    }
    .badge-blue { background-color: #ebf8ff; color: #2b6cb0; border: 1px solid #bee3f8; }
    .badge-purple { background-color: #faf5ff; color: #6b46c1; border: 1px solid #e9d8fd; }
    .badge-green { background-color: #f0fff4; color: #276749; border: 1px solid #c6f6d5; }

    .materia-banner {
        background-color: #ebf8ff;
        border-left: 4px solid #2b6cb0;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 15px;
        font-weight: 700;
        color: #2c5282;
    }

    div.stButton > button[kind="primary"], div.stFormSubmitButton > button {
        background: linear-gradient(135deg, #2f855a 0%, #276749 100%) !important;
        color: white !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 10px 24px !important;
        box-shadow: 0 2px 6px rgba(47, 133, 90, 0.3) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stFormSubmitButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px rgba(47, 133, 90, 0.4) !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 3. Conexión a BD
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=int(st.secrets["mysql"]["port"]),
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
    )


def deduplicate_columns(columns):
    seen = {}
    new_cols = []
    for col in columns:
        col_str = str(col).strip()
        if col_str in seen:
            seen[col_str] += 1
            new_cols.append(f"{col_str}_{seen[col_str]}")
        else:
            seen[col_str] = 0
            new_cols.append(col_str)
    return new_cols


def parse_custom_date(val):
    if pd.isna(val):
        return datetime.now().strftime("%Y-%m-%d")
    val_str = str(val).strip()

    match = re.search(r"(\d{1,2}\s+[a-zA-Z]+\s+\d{4})", val_str)
    if match:
        val_str = match.group(1)

    try:
        return pd.to_datetime(val_str, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


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

# ---------------------------------------------------------
# MÓDULO DE IMPORTACIÓN DE EXCEL
# ---------------------------------------------------------
col_acc1, col_acc2 = st.columns([1, 1])

with col_acc1:
    with st.expander("📥 Subir Planilla Excel"):
        st.caption("Carga tu archivo de cartera (.xlsx / .xls)")
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo Excel", type=["xlsx", "xls"]
        )

        if uploaded_file:
            try:
                df_raw = pd.read_excel(uploaded_file, header=None)

                header_idx = None
                for idx, row in df_raw.iterrows():
                    cells_as_str = [
                        str(cell) for cell in row.values if pd.notna(cell)
                    ]
                    row_str = " ".join(cells_as_str).lower().strip()

                    if ("asegurado" in row_str or "nombre" in row_str) and (
                        "compañ" in row_str or "poliza" in row_str
                    ):
                        header_idx = idx
                        break

                if header_idx is not None:
                    df_excel = pd.read_excel(uploaded_file, header=header_idx)
                else:
                    df_excel = pd.read_excel(uploaded_file)

                df_excel.columns = deduplicate_columns(df_excel.columns)

                # MAPEO EXPRESO PARA RIESGO ASEGURADO Y RAMO
                col_map = {}
                for col in df_excel.columns:
                    c_clean = str(col).lower().strip()

                    # Prioridad 1: Riesgo Asegurado (Marca, Modelo, Patente)
                    if "riesgo" in c_clean:
                        col_map[col] = "Materia_Asegurada"
                    elif "ramo" in c_clean or "tipo" in c_clean:
                        col_map[col] = "Ramo"
                    elif "rut" in c_clean and "RUT" not in col_map.values():
                        col_map[col] = "RUT"
                    elif (
                        "nombre" in c_clean or "asegurado" in c_clean
                    ) and "Nombre" not in col_map.values():
                        col_map[col] = "Nombre"
                    elif (
                        "compañí" in c_clean or "compañi" in c_clean
                    ) and "Compañia" not in col_map.values():
                        col_map[col] = "Compañia"
                    elif (
                        "poliza" in c_clean or "póliza" in c_clean
                    ) and "Poliza" not in col_map.values():
                        col_map[col] = "Poliza"
                    elif (
                        "vigencia" in c_clean
                        or "venc" in c_clean
                        or "ren." in c_clean
                    ) and "Vencimiento" not in col_map.values():
                        col_map[col] = "Vencimiento"
                    elif (
                        "prima" in c_clean and "Prima" not in col_map.values()
                    ):
                        col_map[col] = "Prima"
                    elif (
                        "comision" in c_clean or "comisi" in c_clean
                    ) and "Comision" not in col_map.values():
                        col_map[col] = "Comision"
                    elif (
                        "telefono" in c_clean or "teléfono" in c_clean
                    ) and "Telefono" not in col_map.values():
                        col_map[col] = "Telefono"
                    elif (
                        "correo" in c_clean or "email" in c_clean
                    ) and "Email" not in col_map.values():
                        col_map[col] = "Email"

                df_excel = df_excel.rename(columns=col_map)
                df_excel.columns = deduplicate_columns(df_excel.columns)

                if "Nombre" in df_excel.columns:
                    df_excel = df_excel[
                        df_excel["Nombre"].notna()
                        & ~df_excel["Nombre"]
                        .astype(str)
                        .str.contains(
                            "Ventas|Total|Nombre", case=False, na=False
                        )
                    ]

                st.success(
                    f"📊 **Planilla lista:** Se detectaron **{len(df_excel)} registros** válidos para importar."
                )
                st.dataframe(df_excel.head(10), use_container_width=True)

                if st.button("🚀 Confirmar e Importar Todos a Aiven"):
                    conn = get_connection()
                    cursor = conn.cursor()
                    registros_procesados = 0

                    for i, r in df_excel.iterrows():
                        raw_nombre = r.get("Nombre")
                        nombre_val = (
                            str(raw_nombre).strip()
                            if pd.notna(raw_nombre)
                            else "CLIENTE SIN NOMBRE"
                        )

                        if (
                            not nombre_val
                            or nombre_val.lower() == "nan"
                            or nombre_val.lower() == "none"
                        ):
                            continue

                        raw_rut = r.get("RUT")
                        rut_val = (
                            str(raw_rut).strip()
                            if pd.notna(raw_rut)
                            else "SIN RUT"
                        )

                        raw_tel = r.get("Telefono")
                        tel_val = (
                            str(raw_tel).strip()
                            if pd.notna(raw_tel) and str(raw_tel) != "nan"
                            else ""
                        )

                        raw_email = r.get("Email")
                        email_val = (
                            str(raw_email).strip()
                            if pd.notna(raw_email) and str(raw_email) != "nan"
                            else ""
                        )

                        raw_comp = r.get("Compañia")
                        comp_val = (
                            str(raw_comp).strip()
                            if pd.notna(raw_comp)
                            else "GENERAL"
                        )

                        raw_pol = r.get("Poliza")
                        poliza_val = (
                            str(raw_pol).strip() if pd.notna(raw_pol) else "S/N"
                        )

                        raw_ramo = r.get("Ramo")
                        ramo_val = (
                            str(raw_ramo).strip()
                            if pd.notna(raw_ramo)
                            else "General"
                        )

                        # Extraer Riesgo Asegurado (Suzuki Swift, Ford Edge, Kia Frontier...)
                        raw_materia = r.get("Materia_Asegurada")
                        if pd.notna(raw_materia) and str(raw_materia) != "nan":
                            materia_val = str(raw_materia).strip()
                        else:
                            materia_val = ""

                        venc_val = parse_custom_date(r.get("Vencimiento"))

                        try:
                            prima_val = float(
                                str(r.get("Prima", 0))
                                .replace(",", ".")
                                .replace("$", "")
                            )
                        except (ValueError, TypeError):
                            prima_val = 0.0

                        try:
                            comision_val = float(
                                str(r.get("Comision", 0))
                                .replace(",", ".")
                                .replace("$", "")
                            )
                        except (ValueError, TypeError):
                            comision_val = 0.0

                        # 1. Insertar / Actualizar Cliente
                        if rut_val != "SIN RUT" and rut_val != "nan":
                            cursor.execute(
                                """
                                INSERT INTO clientes (rut, nombre_completo, email, telefono) 
                                VALUES (%s, %s, %s, %s)
                                ON DUPLICATE KEY UPDATE 
                                    id_cliente=LAST_INSERT_ID(id_cliente),
                                    nombre_completo=VALUES(nombre_completo);
                            """,
                                (rut_val, nombre_val, email_val, tel_val),
                            )
                            id_cliente = cursor.lastrowid
                        else:
                            cursor.execute(
                                "INSERT INTO clientes (rut, nombre_completo, email, telefono) VALUES (%s, %s, %s, %s);",
                                (
                                    f"SIN-RUT-{i}-{registros_procesados}",
                                    nombre_val,
                                    email_val,
                                    tel_val,
                                ),
                            )
                            id_cliente = cursor.lastrowid

                        # 2. Insertar Compañía
                        cursor.execute(
                            "INSERT INTO compañias (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id_compañia=LAST_INSERT_ID(id_compañia);",
                            (comp_val,),
                        )
                        id_comp = cursor.lastrowid

                        # 3. Insertar Póliza (Soporta múltiples vehículos por cliente)
                        cursor.execute(
                            """
                            INSERT INTO polizas (numero_poliza, id_cliente, id_compañia, ramo, materia_asegurada, fecha_inicio, fecha_vencimiento, monto_prima_anual, monto_comision, estado)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s, %s, %s, 'Vencida');
                        """,
                            (
                                poliza_val,
                                id_cliente,
                                id_comp,
                                ramo_val,
                                materia_val,
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
                    "Riesgo Asegurado", placeholder="Descripción del bien"
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

# FILTROS
filtro_seleccionado = st.pills(
    "Filtrar por estado",
    [
        "Todos",
        "Vencidas",
        "Vence ≤15 días",
        "Vence ≤30 días",
        "Al día / Vigente",
    ],
    default="Todos",
    label_visibility="collapsed",
)

st.write("")

# ---------------------------------------------------------
# CÁLCULOS Y CONSULTA
# ---------------------------------------------------------
total_clientes = 0
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
            p.id_poliza,
            c.id_cliente,
            c.rut,
            c.nombre_completo,
            c.email,
            c.telefono,
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
        WHERE 1=1
    """

    if busqueda:
        query_base += f" AND (c.nombre_completo LIKE '%{busqueda}%' OR co.nombre LIKE '%{busqueda}%' OR p.numero_poliza LIKE '%{busqueda}%' OR p.materia_asegurada LIKE '%{busqueda}%')"

    if filtro_seleccionado == "Vencidas":
        query_base += f" AND (p.fecha_vencimiento < '{hoy.strftime('%Y-%m-%d')}' OR p.estado = 'Vencida')"
    elif filtro_seleccionado == "Vence ≤15 días":
        fecha_15 = (hoy + timedelta(days=15)).strftime("%Y-%m-%d")
        query_base += f" AND p.fecha_vencimiento BETWEEN '{hoy.strftime('%Y-%m-%d')}' AND '{fecha_15}'"
    elif filtro_seleccionado == "Vence ≤30 días":
        fecha_30 = (hoy + timedelta(days=30)).strftime("%Y-%m-%d")
        query_base += f" AND p.fecha_vencimiento BETWEEN '{hoy.strftime('%Y-%m-%d')}' AND '{fecha_30}'"
    elif filtro_seleccionado == "Al día / Vigente":
        query_base += f" AND p.fecha_vencimiento >= '{hoy.strftime('%Y-%m-%d')}'"

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

    if not df.empty:
        total_clientes = df["id_cliente"].nunique()

except Exception as e:
    df = pd.DataFrame()

# Tarjetas Métricas
col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.markdown(
        f"""<div class="metric-card"><p class="metric-value">{total_clientes}</p><p class="metric-label">CLIENTES</p></div>""",
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

# ---------------------------------------------------------
# LISTADO DESPLEGABLE MOSTRANDO RIESGO ASEGURADO REAL
# ---------------------------------------------------------
if not df.empty:
    for idx, row in df.iterrows():
        id_poliza = row["id_poliza"]
        id_cliente = row["id_cliente"]
        nombre = str(row["nombre_completo"]).upper()
        aseguradora = str(row["compañia"]).upper()
        poliza = str(row["poliza"])
        ramo = str(row["ramo"]).upper()
        materia = str(row["materia"]).strip()
        prima = float(row["prima"])
        comision_real = float(row["comision"])
        rut = str(row["rut"])
        email = (
            ""
            if str(row["email"]).lower() == "nan"
            else str(row["email"] or "")
        )
        tel = (
            ""
            if str(row["telefono"]).lower() == "nan"
            else str(row["telefono"] or "")
        )

        venc_raw = row["fecha_vencimiento"]
        try:
            venc_date = (
                pd.to_datetime(venc_raw).date()
                if pd.notna(venc_raw)
                else datetime.now().date()
            )
        except Exception:
            venc_date = datetime.now().date()

        label_tarjeta = f"👤 {nombre}  |  {aseguradora} · Póliza: {poliza} ({ramo})"

        with st.expander(label_tarjeta):
            st.markdown('<div class="edit-box">', unsafe_allow_html=True)

            # Banner Informativo con el Riesgo Asegurado exacto (Suzuki Swift, Ford Edge, Kia Frontier...)
            texto_riesgo = (
                materia if materia else "Sin riesgo/materia especificada"
            )
            st.markdown(
                f'<div class="materia-banner">🚗 <b>Riesgo Asegurado:</b> {texto_riesgo}</div>',
                unsafe_allow_html=True,
            )

            with st.form(key=f"form_edit_{id_poliza}_{idx}"):
                st.markdown("## ✏️ Editar Información de la Póliza")
                st.write("")

                c1, c2, c3 = st.columns(3)

                with c1:
                    st.markdown(
                        '<span class="badge-section badge-blue">👤 Cliente</span>',
                        unsafe_allow_html=True,
                    )
                    edit_nombre = st.text_input("Nombre Completo", value=nombre)
                    edit_rut = st.text_input("RUT", value=rut)
                    edit_tel = st.text_input("Teléfono", value=tel)
                    edit_email = st.text_input("Email", value=email)

                with c2:
                    st.markdown(
                        '<span class="badge-section badge-purple">📜 Póliza & Bien</span>',
                        unsafe_allow_html=True,
                    )
                    edit_comp = st.text_input("Aseguradora", value=aseguradora)
                    edit_poliza = st.text_input("N° Póliza", value=poliza)
                    edit_ramo = st.text_input("Ramo / Tipo", value=ramo)
                    edit_materia = st.text_input(
                        "Riesgo Asegurado (Marca/Modelo/Patente)",
                        value=materia,
                    )

                with c3:
                    st.markdown(
                        '<span class="badge-section badge-green">💰 Finanzas & Fecha</span>',
                        unsafe_allow_html=True,
                    )
                    edit_prima = st.number_input(
                        "Monto Prima", min_value=0.0, value=prima
                    )
                    edit_comision = st.number_input(
                        "Monto Comisión", min_value=0.0, value=comision_real
                    )
                    edit_venc = st.date_input(
                        "Fecha Vencimiento", value=venc_date
                    )

                st.write("")
                btn_guardar_cambios = st.form_submit_button(
                    "💾 Guardar Cambios"
                )

                if btn_guardar_cambios:
                    try:
                        conn = get_connection()
                        cursor = conn.cursor()

                        # 1. Actualizar Cliente
                        cursor.execute(
                            """
                            UPDATE clientes 
                            SET nombre_completo = %s, rut = %s, telefono = %s, email = %s 
                            WHERE id_cliente = %s
                        """,
                            (
                                edit_nombre,
                                edit_rut,
                                edit_tel,
                                edit_email,
                                id_cliente,
                            ),
                        )

                        # 2. Actualizar o Insertar Compañía
                        cursor.execute(
                            "INSERT INTO compañias (nombre) VALUES (%s) ON DUPLICATE KEY UPDATE id_compañia=LAST_INSERT_ID(id_compañia);",
                            (edit_comp,),
                        )
                        id_comp_actualizada = cursor.lastrowid

                        # 3. Actualizar Póliza
                        cursor.execute(
                            """
                            UPDATE polizas 
                            SET numero_poliza = %s, id_compañia = %s, ramo = %s, materia_asegurada = %s, 
                                monto_prima_anual = %s, monto_comision = %s, fecha_vencimiento = %s 
                            WHERE id_poliza = %s
                        """,
                            (
                                edit_poliza,
                                id_comp_actualizada,
                                edit_ramo,
                                edit_materia,
                                edit_prima,
                                edit_comision,
                                edit_venc,
                                id_poliza,
                            ),
                        )

                        conn.commit()
                        cursor.close()
                        conn.close()

                        st.success(
                            "¡Información de la póliza actualizada con éxito!"
                        )
                        st.rerun()

                    except Exception as err:
                        st.error(f"Error al actualizar la póliza: {err}")

            st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("No hay registros que coincidan con el filtro seleccionado.")
