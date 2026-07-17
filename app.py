import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json
import hashlib
import datetime

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Pedidos Rey de la Harina", page_icon="🍞", layout="centered")

# --- FUNCIÓN PARA ENCRIPTAR CONTRASEÑAS ---
def encriptar_clave(password):
    return hashlib.sha256(password.encode()).hexdigest()

# --- CONEXIÓN CON GOOGLE SHEETS ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
try:
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
            sheet_clientes = ss.worksheet("Clientes")
            clientes_data = sheet_clientes.get_all_records()
            
            cliente_encontrado = None
            fila_cliente_idx = 0
            
            for idx, c in enumerate(clientes_data):
                if str(c.get("ID_Cliente")).strip() == id_input:
                    cliente_encontrado = c
                    fila_cliente_idx = idx + 2
                    break
            
            if cliente_encontrado:
                nombre = cliente_encontrado.get("Nombre / Razón Social", "Cliente")
                clave_guardada = str(cliente_encontrado.get("Clave", "")).strip()
                
                # Registro por primera vez (Columna F / 6)
                if not clave_guardada:
                    st.info(f"¡Hola **{nombre}**! Detectamos que es tu primera vez en la app. Creá tu contraseña personal de acceso:")
                    nueva_clave = st.text_input("Definí tu nueva contraseña propia:", type="password")
                    nueva_clave_confirm = st.text_input("Confirmá tu contraseña:", type="password")
                    
                    if st.button("💾 REGISTRAR CLAVE E INGRESAR", use_container_width=True):
                        if nueva_clave and nueva_clave == nueva_clave_confirm:
                            with st.spinner("Registrando tu clave de forma segura..."):
                                clave_hash = encriptar_clave(nueva_clave)
                                sheet_clientes.update_cell(fila_cliente_idx, 6, clave_hash)
                                
                                st.session_state["autenticado"] = True
                                st.session_state["id_cliente"] = id_input
                                st.session_state["nombre_cliente"] = nombre
                                st.success("¡Contraseña registrada! Ingresando...")
                                st.rerun()
                        elif nueva_clave != nueva_clave_confirm:
                            st.error("❌ Las contraseñas no coinciden. Verificalas por favor.")
                        else:
                            st.error("❌ Por favor, ingresá una contraseña válida.")
                
                # Login normal
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

# 2. SECCIÓN PRIVADA (CLIENTES AUTENTICADOS)
else:
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
    
    # --- CONTROL DE HORARIO Y BLOQUEO ---
    # Obtenemos la hora local de Argentina (UTC-3) para evitar desfases del servidor
    arg_tz = datetime.timezone(datetime.timedelta(hours=-3))
    ahora = datetime.datetime.now(datetime.timezone.utc).astimezone(arg_tz)
    
    # Mostramos la hora oficial al cliente para que no haya dudas
    st.caption(f"🕒 Hora oficial del sistema: **{ahora.strftime('%d/%m/%Y %H:%M')} hs** (Arg)")
    
    dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    dia_seleccionado = st.selectbox("¿Para qué día querés ver/modificar tu pedido?", dias_semana)
    
    # Calculamos si el día seleccionado está bloqueado
    indice_hoy = ahora.weekday()  # Lunes=0, Domingo=6
    indice_seleccionado = dias_semana.index(dia_seleccionado)
    
    # Diferencia de días entre hoy y el día seleccionado
    diff_dias = (indice_seleccionado - indice_hoy) % 7
    
    bloqueado = False
    motivo_bloqueo = ""
    
    if diff_dias == 0:
        bloqueado = True
        motivo_bloqueo = f"Hoy es {dia_seleccionado}. Las entregas de hoy ya están en curso."
    elif diff_dias == 1:
        # Si es para mañana, el límite es hoy antes de las 09:00 AM
        if ahora.time() >= datetime.time(9, 0):
            bloqueado = True
            motivo_bloqueo = f"El pedido para mañana ({dia_seleccionado}) cerró hoy a las 09:00 AM."

    if bloqueado:
        st.error(f"🔒 **PEDIDO BLOQUEADO:** {motivo_bloqueo} Solo podés ver las cantidades agendadas.")
    else:
        st.info("🔓 **Pedido abierto:** Podés realizar modificaciones para este día.")

    st.markdown("---")
    
    try:
        sheet_dia = ss.worksheet(dia_seleccionado)
        datos = sheet_dia.get_all_records()
        
        fila_cliente = None
        num_fila = 0
        
        for idx, fila in enumerate(datos):
            if str(fila.get("ID_Cliente")).strip() == st.session_state["id_cliente"]:
                fila_cliente = fila
                num_fila = idx + 2
                break
                
        if fila_cliente:
            def limpiar_valor(val):
                try:
                    return float(str(val).replace(',', '.')) if val else 0.0
                except:
                    return 0.0

            # Guardamos los valores ORIGINALES para comparar si hay cambios reales
            orig_pan = limpiar_valor(fila_cliente.get("Cant_Pan"))
            orig_minon = limpiar_valor(fila_cliente.get("Cant_Miñon"))
            orig_galletas = limpiar_valor(fila_cliente.get("Cant_Galletas"))
            orig_figaza = limpiar_valor(fila_cliente.get("Cant_Figaza"))
            orig_negritos = limpiar_valor(fila_cliente.get("Cant_Negritos"))
            try:
                orig_facturas = int(fila_cliente.get("Cant_Facturas", 0)) if fila_cliente.get("Cant_Facturas") else 0
            except:
                orig_facturas = 0

            # Inputs (se deshabilitan automáticamente si está bloqueado)
            cant_pan = st.number_input("Pan (kg):", min_value=0.0, value=orig_pan, step=0.5, disabled=bloqueado)
            cant_minon = st.number_input("Miñon (kg):", min_value=0.0, value=orig_minon, step=0.5, disabled=bloqueado)
            cant_galletas = st.number_input("Galletas (kg):", min_value=0.0, value=orig_galletas, step=0.5, disabled=bloqueado)
            cant_figaza = st.number_input("Figaza (kg):", min_value=0.0, value=orig_figaza, step=0.5, disabled=bloqueado)
            cant_negritos = st.number_input("Negritos (kg):", min_value=0.0, value=orig_negritos, step=0.5, disabled=bloqueado)
            cant_facturas = st.number_input("Facturas (docenas):", min_value=0, value=orig_facturas, step=1, disabled=bloqueado)

            st.markdown("---")
            
            # El botón de guardar solo está activo si el día no está bloqueado
            if not bloqueado:
                if st.button("💾 GUARDAR CAMBIOS", use_container_width=True):
                    with st.spinner("Actualizando tu pedido y registrando cambios..."):
                        
                        # 1. DETECTAR CAMBIOS Y PREPARAR HISTORIAL
                        cambios = []
                        if cant_pan != orig_pan:
                            cambios.append(("Pan (kg)", cant_pan))
                        if cant_minon != orig_minon:
                            cambios.append(("Miñon (kg)", cant_minon))
                        if cant_galletas != orig_galletas:
                            cambios.append(("Galletas (kg)", cant_galletas))
                        if cant_figaza != orig_figaza:
                            cambios.append(("Figaza (kg)", cant_figaza))
                        if cant_negritos != orig_negritos:
                            cambios.append(("Negritos (kg)", cant_negritos))
                        if cant_facturas != orig_facturas:
                            cambios.append(("Facturas (docenas)", cant_facturas))
                        
                        # 2. ACTUALIZAR PLANILLA PRINCIPAL
                        sheet_dia.update_cell(num_fila, 3, cant_pan)
                        sheet_dia.update_cell(num_fila, 4, cant_minon)
                        sheet_dia.update_cell(num_fila, 5, cant_galletas)
                        sheet_dia.update_cell(num_fila, 6, cant_figaza)
                        sheet_dia.update_cell(num_fila, 7, cant_negritos)
                        sheet_dia.update_cell(num_fila, 8, cant_facturas)
                        
                        # 3. ESCRIBIR EN EL REGISTRO DE MODIFICACIONES (Si hubo cambios)
                        if cambios:
                            try:
                                sheet_registro = ss.worksheet("Registro_Modificaciones")
                                filas_nuevas = []
                                timestamp_str = ahora.strftime("%Y-%m-%d %H:%M:%S")
                                
                                for producto, nueva_cant in cambios:
                                    # Columnas: Timestamp | ID_Cliente | Cliente | Producto | Nueva_Cantidad | Fecha_Entrega
                                    filas_nuevas.append([
                                        timestamp_str,
                                        st.session_state["id_cliente"],
                                        st.session_state["nombre_cliente"],
                                        producto,
                                        nueva_cant,
                                        dia_seleccionado
                                    ])
                                
                                # Usamos append_rows para enviar todos los registros juntos (ahorra tiempo de carga)
                                sheet_registro.append_rows(filas_nuevas)
                            except Exception as err_reg:
                                st.warning(f"Se actualizó el pedido, pero hubo un inconveniente al guardar el historial: {err_reg}")
                        
                        st.balloons()
                        st.success(f"¡Pedido de {dia_seleccionado} modificado con éxito!")
                        st.rerun()
            else:
                st.warning("⚠️ No se pueden guardar cambios porque el plazo de edición expiró.")
        else:
            st.warning(f"⚠️ No encontramos un pedido base registrado para tu ID el día **{dia_seleccionado}**.")
            
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: No se encontró la pestaña '{dia_seleccionado}' en la planilla.")
    except Exception as e:
        st.error(f"Error: {e}")
