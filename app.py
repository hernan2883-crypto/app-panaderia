import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import json

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Pedidos Rey de la Harina", page_icon="🍞", layout="centered")

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

# --- INTERFAZ DE LA APP ---
st.title("🍞 El Rey de la Harina")
st.subheader("Gestión de Pedidos para Clientes")

dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
dia_seleccionado = st.selectbox("¿Para qué día querés modificar tu pedido?", dias_semana)

id_cliente = st.text_input("Ingresá tu ID de Cliente (Número):", placeholder="Ej: 8366").strip()

if id_cliente:
    try:
        sheet_dia = ss.worksheet(dia_seleccionado)
        datos = sheet_dia.get_all_records()
        
        fila_cliente = None
        num_fila = 0
        
        for idx, fila in enumerate(datos):
            if str(fila.get("ID_Cliente")).strip() == id_cliente:
                fila_cliente = fila
                num_fila = idx + 2
                break
                
        if fila_cliente:
            st.success(f"Bienvenido/a, **{fila_cliente.get('Cliente', 'Cliente')}**")
            st.markdown("---")
            st.write(f"Modificá tus kilos para el día **{dia_seleccionado}**:")

            def limpiar_valor(val):
                try:
                    return float(str(val).replace(',', '.')) if val else 0.0
                except:
                    return 0.0

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
            
            if st.button("💾 GUARDAR PEDIDO", use_container_width=True):
                with st.spinner("Actualizando planilla..."):
                    sheet_dia.update_cell(num_fila, 3, cant_pan)
                    sheet_dia.update_cell(num_fila, 4, cant_minon)
                    sheet_dia.update_cell(num_fila, 5, cant_galletas)
                    sheet_dia.update_cell(num_fila, 6, cant_figaza)
                    sheet_dia.update_cell(num_fila, 7, cant_negritos)
                    sheet_dia.update_cell(num_fila, 8, cant_facturas)
                    
                    st.balloons()
                    st.success(f"¡Pedido guardado con éxito!")
        else:
            st.error(f"No se encontró el ID de cliente '{id_cliente}' en {dia_seleccionado}.")
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Error: No se encontró la pestaña '{dia_seleccionado}' en la planilla.")
    except Exception as e:
        st.error(f"Error: {e}")
