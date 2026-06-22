import requests
import logging
from django.utils import timezone
from core.models import ConfiguracionSRI
from pedidos.models import Factura

logger = logging.getLogger(__name__)

def enviar_factura_sri(factura_id):
    try:
        factura = Factura.objects.get(id=factura_id)
        config = ConfiguracionSRI.objects.first()
        
        if not config or not config.api_token:
            logger.error("Configuración SRI o Token no definido.")
            return False, "Configuración SRI no definida."

        url = config.api_url
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Token {config.api_token}"
        }

        # Validaciones del cliente
        cliente = factura.cliente
        
        # Identificación
        identificacion = factura.ruc_ci or "9999999999999"
        
        # Determinar tipo de identificación
        tipo_id = "05" # Cédula por defecto
        if cliente and getattr(cliente, 'tipo_identificacion', None):
            tipo_id = cliente.tipo_identificacion
        else:
            if identificacion == "9999999999999":
                tipo_id = "07" # Consumidor Final
            elif len(identificacion) == 13:
                tipo_id = "04" # RUC
            elif len(identificacion) == 10:
                tipo_id = "05" # Cédula
            else:
                tipo_id = "06" # Pasaporte u otro

        # Construir Items
        items = []
        if factura.origen == 'cafeteria' and factura.pedido:
            for item in factura.pedido.items.all():
                porcentaje_iva = float(getattr(item.producto, 'porcentaje_iva', 15.00))
                
                # Desglosar el IVA del precio unitario (El precio en BD incluye IVA)
                precio_con_iva = float(item.precio_unitario)
                if porcentaje_iva > 0:
                    precio_sin_iva = precio_con_iva / (1 + (porcentaje_iva / 100.0))
                else:
                    precio_sin_iva = precio_con_iva

                items.append({
                    "main_code": item.producto.codigo_principal or f"PROD-{item.producto.id}",
                    "description": item.producto.nombre,
                    "quantity": float(item.cantidad),
                    "unit_price": round(precio_sin_iva, 6),
                    "discount": 0.00,
                    "tax_rate": porcentaje_iva
                })
        elif factura.origen == 'hostal' and factura.reserva:
            reserva = factura.reserva
            
            # Obtener el IVA configurado en la habitación (por defecto 15.00)
            porcentaje_iva_hab = float(getattr(reserva.habitacion, 'porcentaje_iva', 15.00))
            
            precio_con_iva_hostal = float(reserva.precio_total)
            
            # Desglosar
            if porcentaje_iva_hab > 0:
                precio_sin_iva_hostal = precio_con_iva_hostal / (1 + (porcentaje_iva_hab / 100.0))
            else:
                precio_sin_iva_hostal = precio_con_iva_hostal
            
            items.append({
                "main_code": f"HOST-HAB-{reserva.habitacion.numero}",
                "description": f"Servicio de alojamiento - Habitación {reserva.habitacion.numero}",
                "quantity": 1.0,
                "unit_price": round(precio_sin_iva_hostal, 6),
                "discount": 0.00,
                "tax_rate": porcentaje_iva_hab
            })

        if not items:
            return False, "No hay items para facturar."

        payload = {
            "issue_date": timezone.localtime(factura.fecha_emision).strftime("%Y-%m-%d"),
            "customer_identification_type": tipo_id,
            "customer_identification": identificacion,
            "customer_name": factura.razon_social or "CONSUMIDOR FINAL",
            "customer_address": factura.direccion or "Ecuador",
            "customer_phone": getattr(cliente, 'telefono', None) or "0999999999",
            "payment_methods": [
                {
                    "payment_method_code": factura.metodo_pago_sri
                }
            ],
            "items": items
        }

        if factura.correo and factura.correo.strip():
            payload["customer_email"] = factura.correo.strip()

        response = requests.post(url, json=payload, headers=headers)
        logger.info(f"Respuesta SRI API {response.status_code}: {response.text}")
        
        if response.status_code in [200, 201]:
            data = response.json()
            if data.get("success") or "invoice" in data:
                inv_data = data.get("invoice", {})
                status_from_api = inv_data.get('status', '').upper()
                factura.estado_sri = 'autorizado' if status_from_api == 'AUTORIZADO' else 'pendiente'
                factura.clave_acceso = inv_data.get('access_key')
                
                numero = inv_data.get('number', '')
                if '-' in numero:
                    parts = numero.split('-')
                    if len(parts) == 3:
                        factura.establecimiento = parts[0]
                        factura.punto_emision = parts[1]
                        factura.secuencial = parts[2]
                        
                factura.fecha_autorizacion = timezone.now()
                factura.save()
                return True, f"Factura en estado: {status_from_api}"
            else:
                factura.estado_sri = 'rechazado'
                factura.save()
                return False, data.get("message", "Error desconocido del SRI")
        else:
            logger.error(f"Error API SRI: {response.status_code} - {response.text}")
            factura.estado_sri = 'rechazado'
            factura.save()
            return False, f"Error HTTP {response.status_code}"
            
    except Exception as e:
        logger.exception("Excepción enviando factura al SRI")
        return False, str(e)
