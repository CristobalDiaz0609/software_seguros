import pandas as pd
import mysql.connector
import streamlit as st

# Configuración de la página
st.set_page_config(
    page_title="Gestión de Seguros", page_icon="🛡️", layout="wide"
)


# Conexión a la base de datos en Aiven usando st.secrets
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=st.secrets["mysql"]["port"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
    )


st.title("🛡️ Sistema de Gestión para Aseguradores")

# Navegación lateral
menu = st.sidebar.radio(
    "Navegación",
    [
        "Dashboard & Vencimientos",
        "Cargar Excel (Importador)",
        "Directorio de Clientes",
    ],
)

# ---------------------------------------------------------
# VISTA 1: DASHBOARD & VENCIMIENTOS
# ---------------------------------------------------------
if menu == "Dashboard & Vencimientos":
    st.header("📌 Resumen de Pólizas y Alertas")

    try:
        conn = get_connection()
        # Traer pólizas próximas a vencer (próximos 30 días)
        query_alertas = """
            SELECT p.numero_poliza, c.nombre_completo AS cliente, p.ramo, p.fecha_vencimiento, p.monto_prima_anual
            FROM polizas p
            JOIN clientes c ON p.id_cliente = c.id_cliente
            WHERE p.fecha_vencimiento BETWEEN CURRENT_DATE AND DATE_ADD(CURRENT_DATE, INTERVAL 30 DAY)
            ORDER BY p.fecha_vencimiento ASC;
        """
        df_vencimientos = pd.read_sql(query_alertas, conn)
        conn.close()

        col1, col2 = st.columns(2)
        col1.metric("Pólizas por Vencer (30 días)", len(df_vencimientos))

        st.subheader("⚠️ Alertador de Renovaciones Pendientes")
        if not df_vencimientos.empty:
            st.dataframe(df_vencimientos, use_container_width=True)
        else:
            st.info("No hay pólizas por vencer en los próximos 30 días.")

    except Exception as e:
        st.error(f"Error al conectar con la base de datos: {e}")

# ---------------------------------------------------------
# VISTA 2: IMPORTADOR DE EXCEL
# ---------------------------------------------------------
elif menu == "Cargar Excel (Importador)":
    st.header("📥 Importar Planilla de Clientes/Pólizas")
    st.write(
        "Sube un archivo Excel (.xlsx) con las columnas: **RUT**, **Nombre**, **Email**, **Telefono**"
    )

    uploaded_file = st.file_uploader(
        "Selecciona tu planilla Excel", type=["xlsx", "xls"]
    )

    if uploaded_file:
        df = pd.read_excel(uploaded_file)
        st.write("Vista previa de los datos a importar:")
        st.dataframe(df.head())

        if st.button("Guardar en Base de Datos"):
            try:
                conn = get_connection()
                cursor = conn.cursor()
                registros_cargados = 0

                for _, row in df.iterrows():
                    sql = """
                        INSERT INTO clientes (rut, nombre_completo, email, telefono)
                        VALUES (%s, %s, %s, %s)
                        ON DUPLICATE KEY UPDATE nombre_completo=VALUES(nombre_completo);
                    """
                    val = (
                        str(row["RUT"]),
                        str(row["Nombre"]),
                        str(row.get("Email", "")),
                        str(row.get("Telefono", "")),
                    )
                    cursor.execute(sql, val)
                    registros_cargados += 1

                conn.commit()
                cursor.close()
                conn.close()

                st.success(
                    f"¡Se importaron correctamente {registros_cargados} clientes a Aiven!"
                )
            except Exception as e:
                st.error(f"Error durante el guardado: {e}")

# ---------------------------------------------------------
# VISTA 3: DIRECTORIO DE CLIENTES
# ---------------------------------------------------------
elif menu == "Directorio de Clientes":
    st.header("👥 Lista de Clientes Registrados")

    try:
        conn = get_connection()
        df_clientes = pd.read_sql(
            "SELECT id_cliente, rut, nombre_completo, email, telefono FROM clientes",
            conn,
        )
        conn.close()

        st.dataframe(df_clientes, use_container_width=True)
    except Exception as e:
        st.error(f"Error al cargar clientes: {e}")
