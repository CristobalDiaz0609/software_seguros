import re
from datetime import datetime, timedelta
import urllib.parse
import mysql.connector
import pandas as pd
import plotly.express as px
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
    .metric-value { font-size: 24px; font-weight: 800; color: #1a202c; margin-bottom: -5px; }
    .metric-value.green { color: #276749; }
    .metric-value.red { color: #9b2c2c; }
    .metric-label { font-size: 10px; color: #718096; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; }

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

    /* Estilos Botones de Contacto Directo */
    .btn-contact {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 8px 16px;
        font-size: 14px;
        font-weight: 700;
        border-radius: 8px;
        text-decoration: none !important;
        margin-right: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.06);
        transition: all 0.2s ease;
    }
    .btn-ws {
        background-color: #25D366;
        color: white !important;
    }
    .btn-ws:hover {
        background-color: #1ebc57;
        transform: translateY(-1px);
    }
    .btn-email {
        background-color: #3182ce;
        color: white !important;
    }
    .btn-email:hover {
        background-color: #2b6cb0;
        transform: translateY(-1px);
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


def parse_custom_date(val):
    if not val or pd.isna(val) or str(val).lower() in ["nan", "none", "null", ""]:
        return datetime.now().strftime("%Y-%m-%d")
    val_str = str(val).strip()

    match = re.search(r"(\d{1,2}\s+[a-zA-Z]+\s+\d{4})", val_str)
    if match:
        val_str = match.group(1)

    try:
        return pd.to_datetime(val_str, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return datetime.now().strftime("%Y-%m-%d")


def clean_val(val, default=""):
    if pd.isna(val) or val is None:
        return default
    s = str(val).strip()
    if s.lower() in ["nan", "none", "null", "<na>"]:
        return default
    return s


def format_chile_phone(tel_raw):
    """Limpia el teléfono para dejarlo en formato WhatsApp internacional (+56)"""
    digits = re.sub(r"\D", "", str(tel_raw))
    if not digits:
        return ""
    if len(digits) == 9 and digits.startswith("9"):
        return f"56{digits}"
    elif len(digits) == 8:
        return f"569{digits}"
    elif len(digits) == 11 and digits.startswith("56"):
        return digits
    return digits


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
# MÓDULOS SUPERIORES (IMPORTAR, CREAR Y COMPLETAR DATOS)
# ---------------------------------------------------------
col_acc1, col_acc2, col_acc3 = st.columns([1, 1, 1])

with col_acc1:
    with st.expander("📥 Subir Planilla Excel"):
        st.caption("Carga tu archivo de cartera (.xlsx / .xls)")
        uploaded_file = st.file_uploader(
            "Selecciona tu archivo Excel", type=["xlsx", "xls"]
        )

        limpiar_bd = st.checkbox(
            "⚠️ Vaciar datos antiguos antes de importar (Recomendado)",
            value=True,
        )

        if uploaded_file:
            try:
                df_raw = pd.read_excel(uploaded_file, header=None)
                df_raw = df_raw.fillna("")

                header_idx = None
                for idx, row in df_raw.iterrows():
                    row_str = " ".join([str(c).lower().strip() for c in row.values])
                    if "ramo" in row_str and ("riesgo" in row_str or "asegurado" in row_str or "nombre" in row_str):
                        header_idx = idx
                        break

                if header_idx is not None:
                    headers = [str(c).strip() for c in df_raw.iloc[header_idx].values]
                    df_excel = df_raw.iloc[header_idx + 1:].copy()
                    df_excel.columns = headers
                else:
                    df_excel = df_raw.copy()

                seen = {}
                new_cols = []
                for col in df_excel.columns:
                    c_str = str(col).strip()
                    if c_str in seen:
                        seen[c_str] += 1
                        new_cols.append(f"{c_str}_{seen[c_str]}")
                    else:
                        seen[c_str] = 0
                        new_cols.append(c_str)
                df_excel.columns = new_cols

                col_map = {}
                for col in df_excel.columns:
                    c_clean = str(col).lower().strip()

                    if "riesgo" in c_clean:
                        col_map[col] = "Materia_Asegurada"
                    elif "ramo" in c_clean:
                        col_map[col] = "Ramo"
                    elif "rut" in c_clean and "RUT" not in col_map.values():
                        col_map[col] = "RUT"
                    elif ("nombre" in c_clean or "asegurado" in c_clean) and "Nombre" not in col_map.values():
                        col_map[col] = "Nombre"
                    elif ("compañí" in c_clean or "compañi" in c_clean) and "Compañia" not in col_map.values():
                        col_map[col] = "Compañia"
                    elif ("poliza" in c_clean or "póliza" in c_clean) and "Poliza" not in col_map.values():
                        col_map[col] = "Poliza"
                    elif ("venc" in c_clean or "ren." in c_clean or "vigencia" in c_clean) and "Vencimiento" not in col_map.values():
                        col_map[col] = "Vencimiento"
                    elif "prima" in c_clean and "Prima" not in col_map.values():
                        col_map[col] = "Prima"
                    elif ("comision" in c_clean or "comisi" in c_clean) and "Comision" not in col_map.values():
                        col_map[col] = "Comision"
                    elif ("telefono" in c_clean or "teléfono" in c_clean) and "Telefono" not in col_map.values():
                        col_map[col] = "Telefono"
                    elif ("correo" in c_clean or "email" in c_clean) and "Email" not in col_map.values():
                        col_map[col] = "Email"

                df_excel = df_excel.rename(columns=col_map)

                if "Nombre" in df_excel.columns:
                    df_excel = df_excel[
                        df_excel["Nombre"].astype(str).str.strip().ne("") & 
                        ~df_excel["Nombre"].astype(str).str.contains("Ventas|Total|Nombre|Asegurado", case=False, na=False)
                    ]

                st.success(f"📊 **Planilla detectada correctamente:** {len(df_excel)} registros listos para importar.")
                st.dataframe(df_excel.head(10), use_container_width=True)

                if st.button("🚀 Confirmar e Importar Todos a Aiven"):
                    conn = get_connection()
                    cursor = conn.cursor()

                    if limpiar_bd:
                        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
                        cursor.execute("TRUNCATE TABLE polizas;")
                        cursor.execute("TRUNCATE TABLE clientes;")
                        cursor.execute("TRUNCATE TABLE compañias;")
                        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

                    registros_procesados = 0

                    for i, (_, r) in enumerate(df_excel.iterrows()):
                        nombre_val = clean_val(r.get("Nombre"), "CLIENTE SIN NOMBRE")
                        if not nombre_val or nombre_val == "CLIENTE SIN NOMBRE":
                            continue

                        rut_val = clean_val(r.get("RUT"), f"SIN-RUT-{i}-{registros_procesados}")
                        tel_val = clean_val(r.get("Telefono"), "")
                        email_val = clean_val(r.get("Email"), "")
                        comp_val = clean_val(r.get("Compañia"), "GENERAL")
                        poliza_val = clean_val(r.get("Poliza"), "S/N")
                        ramo_val = clean_val(r.get("Ramo"), "General")
                        materia_val = clean_val(r.get("Materia_Asegurada"), "")

                        venc_val = parse_custom_date(r.get("Vencimiento"))

                        try:
                            prima_str = str(r.get("Prima", "0")).replace(",", ".").replace("$", "").strip()
                            prima_val = float(prima_str) if prima_str else 0.0
                        except (ValueError, TypeError):
                            prima_val = 0.0

                        try:
                            com_str = str(r.get("Comision", "0")).replace(",", ".").replace("$", "").strip()
                            comision_val = float(com_str) if com_str else 0.0
                        except (ValueError, TypeError):
                            comision_val = 0.0

                        cursor.execute("SELECT id_cliente FROM clientes WHERE rut = %s;", (rut_val,))
                        row_c = cursor.fetchone()
                        if row_c:
                            id_cliente = row_c[0]
                        else:
                            cursor.execute(
                                "INSERT INTO clientes (rut, nombre_completo, email, telefono) VALUES (%s, %s, %s, %s);",
                                (rut_val, nombre_val, email_val, tel_val)
                            )
                            id_cliente = cursor.lastrowid

                        cursor.execute("SELECT id_compañia FROM compañias WHERE nombre = %s;", (comp_val,))
                        row_co = cursor.fetchone()
                        if row_co:
                            id_comp = row_co[0]
                        else:
                            cursor.execute("INSERT INTO compañias (nombre) VALUES (%s);", (comp_val,))
                            id_comp = cursor.lastrowid

                        cursor.execute(
                            """
                            INSERT INTO polizas (numero_poliza, id_cliente, id_compañia, ramo, materia_asegurada, fecha_inicio, fecha_vencimiento, monto_prima_anual, monto_comision, estado)
                            VALUES (%s, %s, %s, %s, %s, CURRENT_DATE, %s, %s, %s, 'Vencida');
                            """,
                            (poliza_val, id_cliente, id_comp, ramo_val, materia_val, venc_val, prima_val, comision_val)
                        )

                        registros_procesados += 1

                    conn.commit()
                    cursor.close()
                    conn.close()

                    st.success(f"🎉 ¡Se importaron {registros_procesados} pólizas correctamente!")
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
            c_nombre = st.text_input("Nombre Completo del Cliente", placeholder="Ej: Juan Pérez Soto")
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
                modelo = st.text_input("Modelo / Año", placeholder="Toyota RAV4 2022")
                materia_especifica = f"Patente: {patente.upper()} - {modelo}"
            elif "Vivienda" in tipo_seguro:
                direccion_prop = st.text_input("Dirección Propiedad", placeholder="Av. Providencia 1234, Dpto 502")
                materia_especifica = f"Propiedad: {direccion_prop}"
            elif "Salud" in tipo_seguro:
                cargas = st.text_input("Cargas / Beneficiarios", placeholder="Ej: Cónyuge + 2 Hijos")
                materia_especifica = f"Cobertura: {cargas}"
            else:
                materia_especifica = st.text_input("Riesgo Asegurado", placeholder="Descripción del bien")

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

# MÓDULO COMPLETAR DATOS FALTANTES (CON FILTRO DE FECHA DE VENCIMIENTO)
with col_acc3:
    with st.expander("🛠️ Completar Datos FALTANTES"):
        st.caption("Filtra y completa directamente celdas incompletas")
        filtro_faltante = st.selectbox(
            "Selecciona el dato que falta:",
            [
                "📜 Póliza Faltante",
                "📅 Fecha Vencimiento Faltante",
                "🆔 RUT Faltante",
                "📞 Teléfono Faltante",
                "✉️ Email Faltante",
                "🏢 Aseguradora Faltante",
                "🚗 Riesgo / Patente Faltante",
                "⚠️ Cualquier Dato Faltante",
            ],
            key="sb_faltante",
        )

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
# CONSULTA AUTÓNOMA PARA DATOS FALTANTES (SIN BLOQUEO DE FILTROS)
# ---------------------------------------------------------
if 'sb_faltante' in st.session_state:
    tipo_f = st.session_state['sb_faltante']
    try:
        conn_f = get_connection()
        query_audit = """
            SELECT 
                p.id_poliza as ID_Poliza,
                c.id_cliente as ID_Cliente,
                c.nombre_completo as Nombre,
                c.rut as RUT,
                c.telefono as Telefono,
                c.email as Email,
                COALESCE(co.nombre, '') as Aseguradora,
                COALESCE(p.numero_poliza, '') as N_Poliza,
                COALESCE(p.ramo, '') as Ramo,
                COALESCE(p.materia_asegurada, '') as Riesgo_Patente,
                p.fecha_vencimiento as Fecha_Vencimiento
            FROM clientes c
            LEFT JOIN polizas p ON c.id_cliente = p.id_cliente
            LEFT JOIN compañias co ON p.id_compañia = co.id_compañia
            WHERE 1=1
        """
        df_global_audit = pd.read_sql(query_audit, conn_f)
        conn_f.close()

        if not df_global_audit.empty:
            df_f = df_global_audit.copy()

            if "Póliza" in tipo_f:
                df_f = df_f[df_f['N_Poliza'].isin(['—', 'S/N', '', 'nan', 'None', '0', 'SIN POLIZA'])]
            elif "Fecha Vencimiento" in tipo_f:
                df_f = df_f[df_f['Fecha_Vencimiento'].isna() | (df_f['Fecha_Vencimiento'].astype(str) == '')]
            elif "RUT" in tipo_f:
                df_f = df_f[df_f['RUT'].str.contains('SIN-RUT|SIN RUT|^$', na=True, case=False)]
            elif "Teléfono" in tipo_f:
                df_f = df_f[df_f['Telefono'].isin(['', 'nan', 'None', '0'])]
            elif "Email" in tipo_f:
                df_f = df_f[df_f['Email'].isin(['', 'nan', 'None'])]
            elif "Aseguradora" in tipo_f:
                df_f = df_f[df_f['Aseguradora'].isin(['GENERAL', 'SIN COMPAÑÍA', '', 'nan', 'None'])]
            elif "Riesgo" in tipo_f:
                df_f = df_f[df_f['Riesgo_Patente'].isin(['', 'nan', 'None'])]
            elif "Cualquier" in tipo_f:
                df_f = df_f[
                    df_f['N_Poliza'].isin(['—', 'S/N', '', 'SIN POLIZA']) |
                    df_f['Fecha_Vencimiento'].isna() |
                    df_f['RUT'].str.contains('SIN-RUT|SIN RUT|^$', na=True, case=False) |
                    df_f['Telefono'].isin(['', 'nan', 'None']) |
                    df_f['Email'].isin(['', 'nan', 'None']) |
                    df_f['Aseguradora'].isin(['GENERAL', 'SIN COMPAÑÍA', '']) |
                    df_f['Riesgo_Patente'].isin(['', 'nan', 'None'])
                ]

            st.markdown(f"#### 🛠️ Auditoría de Datos: {tipo_f} ({len(df_f)} registros incompletos)")

            if not df_f.empty:
                df_editable = df_f[['ID_Poliza', 'ID_Cliente', 'Nombre', 'RUT', 'Telefono', 'Email', 'Aseguradora', 'N_Poliza', 'Ramo', 'Riesgo_Patente', 'Fecha_Vencimiento']].copy()
                df_editable.columns = ['ID_Poliza', 'ID_Cliente', 'Nombre', 'RUT', 'Teléfono', 'Email', 'Aseguradora', 'N° Póliza', 'Ramo', 'Riesgo / Patente', 'Fecha Vencimiento']

                st.caption("✍️ **Edita directamente las celdas abajo y presiona Guardar:**")
                edited_df = st.data_editor(
                    df_editable,
                    disabled=['ID_Poliza', 'ID_Cliente'],
                    hide_index=True,
                    use_container_width=True,
                    key=f"editor_global_{tipo_f}"
                )

                if st.button("💾 Guardar Cambios Masivos en Aiven"):
                    try:
                        conn_sav = get_connection()
                        cursor_sav = conn_sav.cursor()

                        for _, row in edited_df.iterrows():
                            # 1. Actualizar Cliente
                            cursor_sav.execute("""
                                UPDATE clientes 
                                SET nombre_completo = %s, rut = %s, telefono = %s, email = %s 
                                WHERE id_cliente = %s;
                            """, (row['Nombre'], row['RUT'], row['Teléfono'], row['Email'], row['ID_Cliente']))

                            # 2. Obtener / Crear Compañía
                            comp_name = str(row['Aseguradora']).strip() or "GENERAL"
                            cursor_sav.execute("SELECT id_compañia FROM compañias WHERE nombre = %s;", (comp_name,))
                            r_c = cursor_sav.fetchone()
                            if r_c:
                                id_co_act = r_c[0]
                            else:
                                cursor_sav.execute("INSERT INTO compañias (nombre) VALUES (%s);", (comp_name,))
                                id_co_act = cursor_sav.lastrowid

                            # 3. Formatear Fecha
                            f_venc = parse_custom_date(row['Fecha Vencimiento'])

                            # 4. Actualizar Póliza
                            cursor_sav.execute("""
                                UPDATE polizas 
                                SET numero_poliza = %s, id_compañia = %s, ramo = %s, materia_asegurada = %s, fecha_vencimiento = %s
                                WHERE id_poliza = %s;
                            """, (row['N° Póliza'], id_co_act, row['Ramo'], row['Riesgo / Patente'], f_venc, row['ID_Poliza']))

                        conn_sav.commit()
                        cursor_sav.close()
                        conn_sav.close()
                        st.success("🎉 ¡Todos los datos editados han sido actualizados con éxito!")
                        st.rerun()
                    except Exception as err_m:
                        st.error(f"Error actualizando registros: {err_m}")
            else:
                st.success("✅ ¡Excelente! No hay registros incompletos para este filtro en toda la base de datos.")

        st.write("---")
    except Exception as e_aud:
        st.error(f"Error consultando datos incompletos: {e_aud}")

# ---------------------------------------------------------
# CÁLCULOS Y CONSULTA PRINCIPAL
# ---------------------------------------------------------
total_clientes = 0
total_polizas = 0
total_comision_mes_actual = 0.0
total_comision_mes_anterior = 0.0
variacion_comision = 0.0

try:
    conn = get_connection()

    hoy = datetime.now()
    primer_dia_mes_actual = hoy.replace(day=1).strftime("%Y-%m-%d")
    ultimo_dia_mes_anterior = (hoy.replace(day=1) - timedelta(days=1)).strftime("%Y-%m-%d")
    primer_dia_mes_anterior = ((hoy.replace(day=1) - timedelta(days=1)).replace(day=1)).strftime("%Y-%m-%d")

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
    variacion_comision = total_comision_mes_actual - total_comision_mes_anterior

    if not df.empty:
        total_clientes = df["id_cliente"].nunique()
        total_polizas = len(df)

except Exception as e:
    df = pd.DataFrame()

# ---------------------------------------------------------
# TARJETAS MÉTRICAS (KPIs)
# ---------------------------------------------------------
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

with col_m1:
    st.markdown(f"""<div class="metric-card"><p class="metric-value">{total_clientes}</p><p class="metric-label">CLIENTES</p></div>""", unsafe_allow_html=True)

with col_m2:
    st.markdown(f"""<div class="metric-card"><p class="metric-value" style="color:#2b6cb0;">{total_polizas}</p><p class="metric-label">TOTAL PÓLIZAS</p></div>""", unsafe_allow_html=True)

with col_m3:
    st.markdown(f"""<div class="metric-card"><p class="metric-value green">${total_comision_mes_actual:,.2f}</p><p class="metric-label">COMISIÓN ESTE MES</p></div>""", unsafe_allow_html=True)

with col_m4:
    st.markdown(f"""<div class="metric-card"><p class="metric-value">${total_comision_mes_anterior:,.2f}</p><p class="metric-label">COMISIÓN MES ANTERIOR</p></div>""", unsafe_allow_html=True)

with col_m5:
    color_var = "green" if variacion_comision >= 0 else "red"
    signo = "+" if variacion_comision >= 0 else ""
    st.markdown(f"""<div class="metric-card"><p class="metric-value {color_var}">{signo}${variacion_comision:,.2f}</p><p class="metric-label">DIFERENCIA MENSUAL</p></div>""", unsafe_allow_html=True)

st.write("")

# ---------------------------------------------------------
# SECCIÓN DE GRÁFICOS VISUALES
# ---------------------------------------------------------
if not df.empty:
    with st.expander("📊 Ver Análisis Gráfico de Cartera", expanded=False):
        col_g1, col_g2 = st.columns(2)

        with col_g1:
            st.markdown("##### 🏢 Pólizas por Compañía Aseguradora")
            df_comp = df.groupby("compañia")["id_poliza"].count().reset_index()
            df_comp.columns = ["Compañía", "Cantidad"]
            df_comp = df_comp.sort_values(by="Cantidad", ascending=True)

            fig_comp = px.bar(
                df_comp,
                x="Cantidad",
                y="Compañía",
                orientation="h",
                text="Cantidad",
                color_discrete_sequence=["#2b6cb0"],
            )
            fig_comp.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=280,
                xaxis_title="",
                yaxis_title="",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_comp, use_container_width=True)

        with col_g2:
            st.markdown("##### 🚗 Distribución por Ramo / Tipo de Seguro")
            df_ramo = df.groupby("ramo")["id_poliza"].count().reset_index()
            df_ramo.columns = ["Ramo", "Cantidad"]

            fig_ramo = px.pie(
                df_ramo,
                values="Cantidad",
                names="Ramo",
                hole=0.4,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig_ramo.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                height=280,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_ramo, use_container_width=True)

st.write("")

# ---------------------------------------------------------
# LISTADO DESPLEGABLE CON BOTONES DINÁMICOS DE CONTACTO
# ---------------------------------------------------------
if not df.empty:
    for idx, row in df.iterrows():
        id_poliza = row["id_poliza"]
        id_cliente = row["id_cliente"]
        nombre = str(row["nombre_completo"]).upper()
        aseguradora = str(row["compañia"]).upper()
        poliza = str(row["poliza"])
        ramo = str(row["ramo"]).upper()
        materia = clean_val(row["materia"], "")
        prima = float(row["prima"])
        comision_real = float(row["comision"])
        rut = str(row["rut"])
        email = clean_val(row["email"], "")
        tel = clean_val(row["telefono"], "")

        venc_raw = row["fecha_vencimiento"]
        try:
            venc_date = pd.to_datetime(venc_raw).date() if pd.notna(venc_raw) else datetime.now().date()
            venc_str = venc_date.strftime("%d/%m/%Y")
        except Exception:
            venc_date = datetime.now().date()
            venc_str = venc_date.strftime("%d/%m/%Y")

        label_tarjeta = f"👤 {nombre}  |  {aseguradora} · Póliza: {poliza} ({ramo})"

        with st.expander(label_tarjeta):
            st.markdown('<div class="edit-box">', unsafe_allow_html=True)

            texto_riesgo = materia if materia else "Sin riesgo/materia especificada"
            st.markdown(f'<div class="materia-banner">🚗 <b>Riesgo Asegurado:</b> {texto_riesgo}</div>', unsafe_allow_html=True)

            # MÓDULO DE CONTACTO DIRECTO (WHATSAPP / CORREO)
            phone_formatted = format_chile_phone(tel)
            msg_ws = f"Hola {nombre.title()}, te saludo de Seguros Patagonia. Te contacto para recordarte que tu póliza N° {poliza} correspondiente a {texto_riesgo} vence el {venc_str}. ¿Te ayudo con la renovación?"
            ws_url = f"https://wa.me/{phone_formatted}?text={urllib.parse.quote(msg_ws)}" if phone_formatted else ""

            email_subject = f"Recordatorio de Renovación de Póliza {poliza} - Seguros Patagonia"
            email_body = f"Estimado/a {nombre.title()},\n\nEsperando que se encuentre muy bien, le escribimos para recordarle que su póliza N° {poliza} ({texto_riesgo}) con la compañía {aseguradora} tiene fecha de vencimiento para el {venc_str}.\n\nQuedamos a su entera disposición para coordinar la renovación y revisar las mejores condiciones para su cobertura.\n\nSaludos cordiales,\nSeguros Patagonia"
            mailto_url = f"mailto:{email}?subject={urllib.parse.quote(email_subject)}&body={urllib.parse.quote(email_body)}" if email else ""

            st.markdown("##### 🚀 Acciones Rápidas de Contacto")
            btn_html = "<div style='margin-bottom: 20px;'>"
            has_action = False

            if ws_url:
                btn_html += f'<a href="{ws_url}" target="_blank" class="btn-contact btn-ws">💬 Recordar por WhatsApp</a>'
                has_action = True

            if mailto_url:
                btn_html += f'<a href="{mailto_url}" target="_blank" class="btn-contact btn-email">✉️ Enviar Correo de Renovación</a>'
                has_action = True

            if not has_action:
                btn_html += '<span style="color:#a0aec0; font-size:13px; font-style:italic;">⚠️ No hay teléfono ni correo registrado para contacto directo.</span>'

            btn_html += "</div>"
            st.markdown(btn_html, unsafe_allow_html=True)

            # Formulario de Edición Individual
            with st.form(key=f"form_edit_{id_poliza}_{idx}"):
                st.markdown("## ✏️ Editar Información de la Póliza")
                st.write("")

                c1, c2, c3 = st.columns(3)

                with c1:
                    st.markdown('<span class="badge-section badge-blue">👤 Cliente</span>', unsafe_allow_html=True)
                    edit_nombre = st.text_input("Nombre Completo", value=nombre)
                    edit_rut = st.text_input("RUT", value=rut)
                    edit_tel = st.text_input("Teléfono", value=tel)
                    edit_email = st.text_input("Email", value=email)

                with c2:
                    st.markdown('<span class="badge-section badge-purple">📜 Póliza & Bien</span>', unsafe_allow_html=True)
                    edit_comp = st.text_input("Aseguradora", value=aseguradora)
                    edit_poliza = st.text_input("N° Póliza", value=poliza)
                    edit_ramo = st.text_input("Ramo / Tipo", value=ramo)
                    edit_materia = st.text_input("Riesgo Asegurado (Marca/Modelo/Patente)", value=materia)

                with c3:
                    st.markdown('<span class="badge-section badge-green">💰 Finanzas & Fecha</span>', unsafe_allow_html=True)
                    edit_prima = st.number_input("Monto Prima", min_value=0.0, value=prima)
                    edit_comision = st.number_input("Monto Comisión", min_value=0.0, value=comision_real)
                    edit_venc = st.date_input("Fecha Vencimiento", value=venc_date)

                st.write("")
                btn_guardar_cambios = st.form_submit_button("💾 Guardar Cambios")

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
                            (edit_nombre, edit_rut, edit_tel, edit_email, id_cliente)
                        )

                        # 2. Actualizar o Insertar Compañía
                        cursor.execute("SELECT id_compañia FROM compañias WHERE nombre = %s;", (edit_comp,))
                        r_co = cursor.fetchone()
                        if r_co:
                            id_comp_actualizada = r_co[0]
                        else:
                            cursor.execute("INSERT INTO compañias (nombre) VALUES (%s);", (edit_comp,))
                            id_comp_actualizada = cursor.lastrowid

                        # 3. Actualizar Póliza
                        cursor.execute(
                            """
                            UPDATE polizas 
                            SET numero_poliza = %s, id_compañia = %s, ramo = %s, materia_asegurada = %s, 
                                monto_prima_anual = %s, monto_comision = %s, fecha_vencimiento = %s 
                            WHERE id_poliza = %s
                            """,
                            (edit_poliza, id_comp_actualizada, edit_ramo, edit_materia, edit_prima, edit_comision, edit_venc, id_poliza)
                        )

                        conn.commit()
                        cursor.close()
                        conn.close()

                        st.success("¡Información de la póliza actualizada con éxito!")
                        st.rerun()

                    except Exception as err:
                        st.error(f"Error al actualizar la póliza: {err}")

            st.markdown("</div>", unsafe_allow_html=True)

else:
    st.info("No hay registros que coincidan con el filtro seleccionado.")
