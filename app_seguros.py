import mysql.connector
import pandas as pd
import streamlit as st

# 1. Configuración de pantalla
st.set_page_config(
    page_title="SegurosApp - Buscador Express",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded",
)


# 2. Conexión a MySQL en Aiven
def get_connection():
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        port=int(st.secrets["mysql"]["port"]),
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
    )


# Sidebar / Menú Lateral
st.sidebar.title("🛡️ SegurosApp")
menu = st.sidebar.radio(
    "Menú Principal",
    [
        "⚡ Buscador Express",
        "📊 Dashboard & Vencimientos",
        "➕ Nuevo Cliente / Póliza",
        "📥 Importador Excel",
    ],
)

# ---------------------------------------------------------
# VISTA PRINCIPAL: BUSCADOR EXPRESS
# ---------------------------------------------------------
if menu == "⚡ Buscador Express":
    st.title("⚡ Buscador Universal de Clientes y Pólizas")
    st.markdown(
        "Ingresa cualquier dato para obtener la ficha completa de inmediato."
    )

    # Campo de búsqueda principal
    busqueda = st.text_input(
        "🔍 Buscar por RUT, Nombre, N° de Póliza o Patente/Materia:",
        placeholder="Ej: 12345678-9, Juan Pérez, POL-9982, AB1234...",
    )

    if busqueda:
        try:
            conn = get_connection()

            # Query SQL universal que busca en múltiples campos con LIKE
            query_busqueda = f"""
                SELECT 
                    c.id_cliente,
                    c.rut,
                    c.nombre_completo,
                    c.email,
                    c.telefono,
                    c.direccion,
                    p.id_poliza,
                    p.numero_poliza,
                    co.nombre AS compañia,
                    p.ramo,
                    p.materia_asegurada,
                    p.fecha_inicio,
                    p.fecha_vencimiento,
                    p.monto_prima_anual,
                    p.moneda,
                    p.estado
                FROM clientes c
                LEFT JOIN polizas p ON c.id_cliente = p.id_cliente
                LEFT JOIN compañias co ON p.id_compañia = co.id_compañia
                WHERE c.rut LIKE '%{busqueda}%' 
                   OR c.nombre_completo LIKE '%{busqueda}%'
                   OR p.numero_poliza LIKE '%{busqueda}%'
                   OR p.materia_asegurada LIKE '%{busqueda}%'
                ORDER BY c.nombre_completo ASC, p.fecha_vencimiento DESC;
            """

            df_resultados = pd.read_sql(query_busqueda, conn)
            conn.close()

            if not df_resultados.empty:
                # Agrupar resultados por cliente único
                clientes_unicos = df_resultados[
                    "id_cliente"
                ].unique()

                st.success(
                    f"🎯 Se encontraron **{len(clientes_unicos)}** cliente(s) coincidentes:"
                )

                for id_cli in clientes_unicos:
                    # Filtrar datos de este cliente específico
                    df_cli = df_resultados[df_resultados["id_cliente"] == id_cli]
                    cliente_info = df_cli.iloc[0]

                    # Tarjeta visual del cliente (Ficha)
                    with st.expander(
                        f"👤 {cliente_info['nombre_completo']} — RUT: {cliente_info['rut']}",
                        expanded=True,
                    ):
                        c1, c2, c3 = st.columns(3)
                        c1.markdown(f"**Email:** {cliente_info['email'] or 'N/I'}")
                        c2.markdown(f"**Teléfono:** {cliente_info['telefono'] or 'N/I'}")
                        c3.markdown(f"**Dirección:** {cliente_info['direccion'] or 'N/I'}")

                        st.markdown("---")
                        st.subheader("📜 Pólizas Asociadas")

                        # Revisar si tiene pólizas
                        df_polizas = df_cli.dropna(subset=["numero_poliza"])

                        if not df_polizas.empty:
                            # Formatear la tabla de pólizas del cliente
                            tabla_polizas = df_polizas[
                                [
                                    "numero_poliza",
                                    "compañia",
                                    "ramo",
                                    "materia_asegurada",
                                    "fecha_vencimiento",
                                    "monto_prima_anual",
                                    "moneda",
                                    "estado",
                                ]
                            ].rename(
                                columns={
                                    "numero_poliza": "N° Póliza",
                                    "compañia": "Aseguradora",
                                    "ramo": "Ramo",
                                    "materia_asegurada": "Materia / Patente",
                                    "fecha_vencimiento": "Vencimiento",
                                    "monto_prima_anual": "Prima",
                                    "moneda": "Moneda",
                                    "estado": "Estado",
                                }
                            )

                            st.dataframe(
                                tabla_polizas,
                                use_container_width=True,
                                hide_index=True,
                            )
                        else:
                            st.info("Este cliente no tiene pólizas registradas aún.")
            else:
                st.warning(
                    f"❌ No se encontró ningún cliente o póliza con el término: **'{busqueda}'**"
                )

        except Exception as e:
            st.error(f"Error en la búsqueda: {e}")
    else:
        st.info("💡 Escribe en la barra de arriba para iniciar la búsqueda rápida.")

# ---------------------------------------------------------
# VISTA 2: DASHBOARD & VENCIMIENTOS
# ---------------------------------------------------------
elif menu == "📊 Dashboard & Vencimientos":
    st.title("📊 Resumen y Vencimientos")
    st.write("Vista para analizar alertas periódicas de vencimiento.")

# ---------------------------------------------------------
# VISTA 3: NUEVO REGISTRO
# ---------------------------------------------------------
elif menu == "➕ Nuevo Cliente / Póliza":
    st.title("➕ Ingrese Datos Manualmente")

# ---------------------------------------------------------
# VISTA 4: IMPORTADOR EXCEL
# ---------------------------------------------------------
elif menu == "📥 Importador Excel":
    st.title("📥 Importación Masiva")
