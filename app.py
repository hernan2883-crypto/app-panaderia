import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import hashlib

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Pedidos Rey de la Harina", page_icon="🍞", layout="centered")

# --- FUNCIÓN PARA ENCRIPTAR CONTRASEÑAS ---
def encriptar_clave(password):
    # Transforma la clave en un hash irreversible usando SHA-256
    return hashlib.sha256(password.encode()).hexdigest()

# --- CONEXIÓN CON GOOGLE SHEETS ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
try:
    # Leemos el JSON directo como texto desde los secretos de Streamlit
    info_credenciales = json.loads(st.secrets["gcp_json"])
    creds = Credentials.from_service_account_info(info_credenciales, scopes=scope)
    client = gspread.authorize(creds)
    ss = client.open("Planilla_Maestra_Panaderia")
except Exception as e:
    st.error(f"Error de conexión con Google Sheets: {e}")
    st.stop()

# --- INICIALIZACIÓN DEL ESTADO DE SESIÓN ---
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False
if "id_cliente" not in st.session_state:
    st.session_state["id_cliente"] = None
if "nombre_cliente" not in st.session_state:
    st.session_state["nombre_cliente"] = None

# --- INTERFAZ DE LA APP ---
st.title("🍞 El Rey de la Harina")

# 1. FLUJO DE INICIO DE SESIÓN / REGISTRO
if not st.session_state["autenticado"]:
    st.subheader("🔑 Acceso Exclusivo para Clientes")
    st.write("Ingresá tu código asignado para iniciar sesión o registrar tu contraseña por primera vez.")
    
    id_input = st.text_input("Ingresá tu ID de Cliente (Número):", placeholder="Ej: 8366").strip()
    
    if id_input:
        try:
            # Traemos la pestaña de control de Clientes
            sheet_clientes = ss.worksheet("Clientes")
            clientes_data = sheet_clientes.get_all_records()
            
            cliente_encontrado = None
            fila_cliente_idx = 0
            
            # Buscamos al cliente en la base de control
            for idx, c in enumerate(clientes_data):
                if str(c.get("ID_Cliente")).strip() == id_input:
                    cliente_encontrado = c
                    fila_cliente_idx = idx + 2  # +2 por el encabezado en Sheets (index 1)
                    break
            
            if cliente_encontrado:
                # Obtenemos el nombre usando exactamente tu encabezado de columna B
                nombre = cliente_encontrado.get("Nombre / Razón Social", "Cliente")
                clave_guardada = str(cliente_encontrado.get("Clave", "")).strip()
                
                # CASO A: El cliente entra por primera vez (no tiene clave registrada en Columna F)
                if not clave_guardada:
                    st.info(f"¡Hola **{nombre}**! Detectamos que es tu primera vez en la app. Creá tu contraseña personal de acceso:")
                    nueva_clave = st.text_input("Definí tu nueva contraseña propia:", type="password")
                    nueva_clave_confirm = st.text_input("Confirmá tu contraseña:", type="password")
                    
                    if st.button("💾 REGISTRAR CLAVE E INGRESAR", use_container_width=True):
                        if nueva_clave and nueva_clave == nueva_clave_confirm:
                            with st.spinner("Registrando tu clave de forma segura..."):
                                clave_hash = encriptar_clave(nueva_clave)
                                # Guardamos el Hash en la columna F (Columna 6)
                                sheet_clientes.update_cell(fila_cliente_idx, 6, clave_hash)
                                
                                # Logueamos al usuario de forma automática
                                st.session_state["autenticado"] = True
                                st.session_state["id_cliente"] = id_input
                                st.session_state["nombre_cliente"] = nombre
                                st.success("¡Contraseña registrada! Ingresando...")
                                st.rerun()
                        elif nueva_clave != nueva_clave_confirm:
                            st.error("❌ Las contraseñas no coinciden. Verificalas por favor.")
                        else:
                            st.error("❌ Por favor, ingresá una contraseña válida.")
                
                # CASO B: El cliente ya está registrado, le pedimos su clave propia
                else:
                    clave_ingresada = st.text_input("Ingresá tu contraseña de acceso:", type="password")
                    
                    if st.button("🚀 INICIAR SESIÓN", use_container_width=True):
                        if encriptar_clave(clave_ingresada) == clave_guardada:
                            st.session_state["autenticado"] = True
                            st.session_state["id_cliente"] = id_input
                            st.session_state["nombre_cliente"] = nombre
                            st.rerun()
                        else:
                            st.error("❌ Contraseña incorrecta. Si la olvidaste, contactate con nosotros.")
            else:
                st.error(f"❌ El ID de cliente '{id_input}' no figura en nuestro sistema. Por favor, verificalo.")
                
        except gspread.exceptions.WorksheetNotFound:
            st.error("⚠️ Error técnico: No se encontró la pestaña 'Clientes' en la planilla base.")
        except Exception as e:
            st.error(f"Error: {e}")

# 2. SECCIÓN PRIVADA (SOLO CLIENTES AUTENTICADOS)
else:
    # Encabezado de bienvenida y botón de salida
    col_user, col_logout = st.columns([3, 1])
    with col_user:
        st.success(f"Bienvenido/a, **{st.session_state['nombre_cliente']}**")
    with col_logout:
        if st.button("Cerrar Sesión", use_container_width=True):
            st.session_state["autenticado"] = False
            st.session_state["id_cliente"] = None
            st.session_state["nombre_cliente"] = None
            st.rerun()
            
    st.markdown("---")
    
    # Selector de días
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_seleccionado = st.selectbox("¿Para qué día querés ver/modificar tu pedido?", dias_semana)
    
    try:
        sheet_dia = ss.worksheet(dia_seleccionado)
        datos = sheet_dia.get_all_records()
        
        fila_cliente = None
        num_fila = 0
        
        # Buscamos el pedido cargado para este cliente en el día seleccionado
        for idx, fila in enumerate(datos):
            if str(fila.get("ID_Cliente")).strip() == st.session_state["id_cliente"]:
                fila_cliente = fila
                num_fila = idx + 2
                break
                
        if fila_cliente:
            st.write(f"Este es tu pedido agendado para el **{dia_seleccionado}**. Modificá los valores que necesites cambiar:")
            
            def limpiar_valor(val):
                try:
                    return float(str(val).replace(',', '.')) if val else 0.0
                except:
                    return 0.0

            # Los inputs cargan automáticamente el valor que YA está guardado en el Sheets para ese día
            cant_pan = st.number_input("Pan (kg):", min_value=0.0, value=limpiar_valor(fila_cliente.get("Pan")), step=0.5)
            cant_minon = st.number_input("Miñon (kg):", min_value=0.0, value=limpiar_valor(fila_cliente.get("Miñon")), step=0.5)
            cant_galletas = st.number_input("Galletas (kg):", min_value=0.0, value=limpiar_valor(fila_cliente.get("Galletas")), step=0.5)
            cant_figaza = st.number_input("Figaza (kg):", min_value=0.0, value=limpiar_valor(fila_cliente.get("Figaza")), step=0.5)
            cant_negritos = st.number_input("Negritos (kg):", min_value=0.0, value=limpiar_valor(fila_cliente.get("Negritos")), step=0.5)
            
            try:
                val_facturas = int(fila_cliente.get("Facturas", 0)) if fila_cliente.get("Facturas") else 0
            except:
                val_facturas = 0
            cant_facturas = st.number_input("Facturas (docenas):", min_value=0, value=val_facturas, step=1)

            st.markdown("---")
            
            if st.button("💾 GUARDAR CAMBIOS", use_container_width=True):
                with st.spinner("Actualizando tu pedido en el sistema..."):
                    # Mantenemos exactamente las columnas de actualización que ya tenías para tus días
                    sheet_dia.update_cell(num_fila, 3, cant_pan)
                    sheet_dia.update_cell(num_fila, 4, cant_minon)
                    sheet_dia.update_cell(num_fila, 5, cant_galletas)
                    sheet_dia.update_cell(num_fila, 6, cant_figaza)
                    sheet_dia.update_cell(num_fila, 7, cant_negritos)
                    sheet_dia.update_cell(num_fila, 8, cant_facturas)
                    
                    st.balloons()
                    st.success(f"¡Pedido de {dia_seleccionado} modificado con éxito!")
        else:
            st.warning(f"⚠️ No encontramos un pedido base registrado para tu ID el día **{dia_seleccionado}**.")
            
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: No se encontró la pestaña '{dia_seleccionado}' en la planilla.")
    except Exception as e:
        st.error(f"Error: {e}")
