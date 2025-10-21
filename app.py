import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
import json
from transcriber import Transcriber
from llm import LLM
from weather import Weather
from tts import TTS
from pc_command import PcCommand
import threading
import time

# Cargar llaves del archivo .env
load_dotenv()

app = Flask(__name__)

# Variables globales SIMPLIFICADAS
transcriber = None
is_processing = False  # Evitar múltiples grabaciones simultáneas

# Inventario en memoria - AMPLIADO
inventory = [
    {"id": 1, "name": "Arroz", "category": "Granos", "stock": 25, "minStock": 10},
    {"id": 2, "name": "Frijoles", "category": "Granos", "stock": 18, "minStock": 8},
    {"id": 3, "name": "Aceite", "category": "Aceites", "stock": 12, "minStock": 5},
    {"id": 4, "name": "Azúcar", "category": "Endulzantes", "stock": 30, "minStock": 10},
    {"id": 5, "name": "Sal", "category": "Condimentos", "stock": 15, "minStock": 5},
    {"id": 6, "name": "Leche", "category": "Lácteos", "stock": 8, "minStock": 10},
    {"id": 7, "name": "Galletas", "category": "Snacks", "stock": 22, "minStock": 15},
    {"id": 8, "name": "Jabón", "category": "Limpieza", "stock": 14, "minStock": 10},
    {"id": 9, "name": "Atún", "category": "Enlatados", "stock": 15, "minStock": 8},
    {"id": 10, "name": "Café", "category": "Bebidas", "stock": 20, "minStock": 10},
    {"id": 11, "name": "Pan", "category": "Panadería", "stock": 5, "minStock": 10},
    {"id": 12, "name": "Huevos", "category": "Lácteos", "stock": 30, "minStock": 12},
    {"id": 13, "name": "Pasta", "category": "Granos", "stock": 25, "minStock": 10},
    {"id": 14, "name": "Tomate", "category": "Verduras", "stock": 8, "minStock": 15},
    {"id": 15, "name": "Cebolla", "category": "Verduras", "stock": 12, "minStock": 10},
    {"id": 16, "name": "Papa", "category": "Verduras", "stock": 40, "minStock": 20},
    {"id": 17, "name": "Zanahoria", "category": "Verduras", "stock": 18, "minStock": 12},
    {"id": 18, "name": "Pollo", "category": "Carnes", "stock": 10, "minStock": 8},
    {"id": 19, "name": "Carne", "category": "Carnes", "stock": 12, "minStock": 8},
    {"id": 20, "name": "Refresco", "category": "Bebidas", "stock": 35, "minStock": 20},
    {"id": 21, "name": "Agua", "category": "Bebidas", "stock": 50, "minStock": 30},
    {"id": 22, "name": "Yogurt", "category": "Lácteos", "stock": 15, "minStock": 10},
    {"id": 23, "name": "Mantequilla", "category": "Lácteos", "stock": 8, "minStock": 5},
    {"id": 24, "name": "Queso", "category": "Lácteos", "stock": 10, "minStock": 8},
    {"id": 25, "name": "Shampoo", "category": "Higiene", "stock": 12, "minStock": 8},
    {"id": 26, "name": "Pasta Dental", "category": "Higiene", "stock": 18, "minStock": 10},
    {"id": 27, "name": "Papel Higiénico", "category": "Higiene", "stock": 25, "minStock": 15},
    {"id": 28, "name": "Detergente", "category": "Limpieza", "stock": 10, "minStock": 8},
    {"id": 29, "name": "Servilletas", "category": "Limpieza", "stock": 30, "minStock": 20},
    {"id": 30, "name": "Cereal", "category": "Desayuno", "stock": 14, "minStock": 10}
]

# Historial de actividades con datos previos - AMPLIADO
from datetime import datetime, timedelta

def generate_sample_activities():
    """Generar actividades de ejemplo de los últimos días"""
    activities_list = []
    now = datetime.now()
    
    sample_data = [
        # Hoy
        {"hours_ago": 1, "type": "sell", "product": "Pan", "text": "Venta registrada de 5 Pan", "qty": 5},
        {"hours_ago": 2, "type": "add", "product": "Leche", "text": "Se agregaron 10 unidades de Leche", "qty": 10},
        {"hours_ago": 3, "type": "sell", "product": "Refresco", "text": "Venta registrada de 8 Refresco", "qty": 8},
        {"hours_ago": 4, "type": "update", "product": "Galletas", "text": "Stock actualizado: Galletas de 15 a 22 unidades", "qty": 22},
        {"hours_ago": 5, "type": "sell", "product": "Huevos", "text": "Venta registrada de 12 Huevos", "qty": 12},
        
        # Ayer
        {"hours_ago": 26, "type": "add", "product": "Arroz", "text": "Se agregaron 20 unidades de Arroz", "qty": 20},
        {"hours_ago": 28, "type": "sell", "product": "Café", "text": "Venta registrada de 3 Café", "qty": 3},
        {"hours_ago": 30, "type": "sell", "product": "Azúcar", "text": "Venta registrada de 5 Azúcar", "qty": 5},
        {"hours_ago": 32, "type": "add", "product": "Atún", "text": "Se agregaron 15 unidades de Atún", "qty": 15},
        {"hours_ago": 34, "type": "sell", "product": "Jabón", "text": "Venta registrada de 4 Jabón", "qty": 4},
        
        # Hace 2 días
        {"hours_ago": 50, "type": "update", "product": "Agua", "text": "Stock actualizado: Agua de 30 a 50 unidades", "qty": 50},
        {"hours_ago": 52, "type": "sell", "product": "Pasta", "text": "Venta registrada de 6 Pasta", "qty": 6},
        {"hours_ago": 54, "type": "add", "product": "Yogurt", "text": "Se agregaron 15 unidades de Yogurt", "qty": 15},
        {"hours_ago": 56, "type": "sell", "product": "Galletas", "text": "Venta registrada de 10 Galletas", "qty": 10},
        
        # Hace 3 días
        {"hours_ago": 74, "type": "add", "product": "Pollo", "text": "Se agregaron 10 unidades de Pollo", "qty": 10},
        {"hours_ago": 76, "type": "sell", "product": "Carne", "text": "Venta registrada de 5 Carne", "qty": 5},
        {"hours_ago": 78, "type": "add", "product": "Papa", "text": "Se agregaron 50 unidades de Papa", "qty": 50},
        {"hours_ago": 80, "type": "sell", "product": "Tomate", "text": "Venta registrada de 10 Tomate", "qty": 10},
        
        # Hace 4 días
        {"hours_ago": 98, "type": "update", "product": "Frijoles", "text": "Stock actualizado: Frijoles de 10 a 18 unidades", "qty": 18},
        {"hours_ago": 100, "type": "sell", "product": "Aceite", "text": "Venta registrada de 3 Aceite", "qty": 3},
        {"hours_ago": 102, "type": "add", "product": "Shampoo", "text": "Se agregaron 12 unidades de Shampoo", "qty": 12},
        {"hours_ago": 104, "type": "sell", "product": "Pasta Dental", "text": "Venta registrada de 5 Pasta Dental", "qty": 5},
        
        # Hace 5 días
        {"hours_ago": 122, "type": "add", "product": "Papel Higiénico", "text": "Se agregaron 25 unidades de Papel Higiénico", "qty": 25},
        {"hours_ago": 124, "type": "sell", "product": "Detergente", "text": "Venta registrada de 4 Detergente", "qty": 4},
        {"hours_ago": 126, "type": "add", "product": "Servilletas", "text": "Se agregaron 30 unidades de Servilletas", "qty": 30},
        {"hours_ago": 128, "type": "sell", "product": "Cereal", "text": "Venta registrada de 6 Cereal", "qty": 6},
        
        # Hace 6 días
        {"hours_ago": 146, "type": "update", "product": "Queso", "text": "Stock actualizado: Queso de 5 a 10 unidades", "qty": 10},
        {"hours_ago": 148, "type": "sell", "product": "Mantequilla", "text": "Venta registrada de 3 Mantequilla", "qty": 3},
        {"hours_ago": 150, "type": "add", "product": "Cebolla", "text": "Se agregaron 15 unidades de Cebolla", "qty": 15},
        {"hours_ago": 152, "type": "sell", "product": "Zanahoria", "text": "Venta registrada de 7 Zanahoria", "qty": 7},
        
        # Hace 1 semana
        {"hours_ago": 170, "type": "add", "product": "Sal", "text": "Se agregaron 20 unidades de Sal", "qty": 20},
        {"hours_ago": 172, "type": "sell", "product": "Arroz", "text": "Venta registrada de 8 Arroz", "qty": 8},
        {"hours_ago": 174, "type": "add", "product": "Café", "text": "Se agregaron 20 unidades de Café", "qty": 20},
        {"hours_ago": 176, "type": "sell", "product": "Pan", "text": "Venta registrada de 15 Pan", "qty": 15},
        
        # Hace 10 días
        {"hours_ago": 242, "type": "update", "product": "Refresco", "text": "Stock actualizado: Refresco de 20 a 35 unidades", "qty": 35},
        {"hours_ago": 244, "type": "sell", "product": "Agua", "text": "Venta registrada de 20 Agua", "qty": 20},
        {"hours_ago": 246, "type": "add", "product": "Leche", "text": "Se agregaron 25 unidades de Leche", "qty": 25},
        {"hours_ago": 248, "type": "sell", "product": "Huevos", "text": "Venta registrada de 24 Huevos", "qty": 24},
        
        # Hace 2 semanas
        {"hours_ago": 338, "type": "add", "product": "Atún", "text": "Se agregaron 20 unidades de Atún", "qty": 20},
        {"hours_ago": 340, "type": "sell", "product": "Galletas", "text": "Venta registrada de 15 Galletas", "qty": 15},
        {"hours_ago": 342, "type": "add", "product": "Jabón", "text": "Se agregaron 20 unidades de Jabón", "qty": 20},
        {"hours_ago": 344, "type": "sell", "product": "Pasta", "text": "Venta registrada de 10 Pasta", "qty": 10},
        
        # Hace 3 semanas
        {"hours_ago": 506, "type": "update", "product": "Papa", "text": "Stock actualizado: Papa de 30 a 40 unidades", "qty": 40},
        {"hours_ago": 508, "type": "sell", "product": "Tomate", "text": "Venta registrada de 12 Tomate", "qty": 12},
        {"hours_ago": 510, "type": "add", "product": "Cebolla", "text": "Se agregaron 18 unidades de Cebolla", "qty": 18},
        {"hours_ago": 512, "type": "sell", "product": "Zanahoria", "text": "Venta registrada de 8 Zanahoria", "qty": 8},
        
        # Hace 1 mes
        {"hours_ago": 722, "type": "add", "product": "Pollo", "text": "Se agregaron 15 unidades de Pollo", "qty": 15},
        {"hours_ago": 724, "type": "sell", "product": "Carne", "text": "Venta registrada de 8 Carne", "qty": 8},
        {"hours_ago": 726, "type": "add", "product": "Yogurt", "text": "Se agregaron 20 unidades de Yogurt", "qty": 20},
        {"hours_ago": 728, "type": "sell", "product": "Queso", "text": "Venta registrada de 6 Queso", "qty": 6},
    ]
    
    for item in sample_data:
        event_time = now - timedelta(hours=item["hours_ago"])
        activities_list.append({
            "time": event_time.strftime("%H:%M"),
            "date": event_time.strftime("%d/%m/%Y"),
            "fullDate": event_time.isoformat(),
            "text": item["text"],
            "type": item["type"],
            "product": item["product"]
        })
    
    return activities_list

activities = generate_sample_activities()
interactive_products = {1, 6, 7, 9, 11, 20, 21}  # Algunos productos ya marcados como interactivos

@app.route("/gwen")
def gwen():
    return render_template("gwen.html")

# RUTAS PARA EL INVENTARIO
@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory)

@app.route("/api/interactive-products", methods=["GET"])
def get_interactive_products():
    """Obtener solo productos con actividad reciente"""
    interactive_list = [p for p in inventory if p["id"] in interactive_products]
    print(f"🎯 Productos interactivos solicitados:")
    print(f"   IDs en set: {interactive_products}")
    print(f"   Productos encontrados: {len(interactive_list)}")
    for p in interactive_list:
        print(f"   - {p['name']} (ID: {p['id']})")
    return jsonify(interactive_list)

@app.route("/api/alerts", methods=["GET"])
def get_alerts():
    """Obtener alertas de stock bajo y productos próximos a vencer"""
    try:
        # Alertas de stock bajo
        low_stock_alerts = []
        for product in inventory:
            if product["stock"] <= product["minStock"]:
                urgency = "CRÍTICO" if product["stock"] == 0 else "ALTO" if product["stock"] <= product["minStock"] // 2 else "MEDIO"
                low_stock_alerts.append({
                    "id": product["id"],
                    "name": product["name"],
                    "stock": product["stock"],
                    "minStock": product["minStock"],
                    "urgency": urgency
                })
        
        # Alertas de productos próximos a vencer (datos de ejemplo)
        expiring_alerts = [
            {
                "id": 6,
                "name": "Leche",
                "daysUntilExpiry": 3,
                "expiryDate": "2024-01-15",
                "urgency": "CRÍTICO"
            },
            {
                "id": 7,
                "name": "Galletas",
                "daysUntilExpiry": 15,
                "expiryDate": "2024-01-27",
                "urgency": "MEDIO"
            }
        ]
        
        return jsonify({
            "lowStock": low_stock_alerts,
            "expiring": expiring_alerts
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo alertas: {e}")
        return jsonify({
            "lowStock": [],
            "expiring": []
        })


@app.route("/api/inventory/add", methods=["POST"])
def add_product():
    data = request.json
    product_name = data.get("name")
    quantity = data.get("quantity", 1)
    category = data.get("category", "General")
    
    existing_product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
    
    if existing_product:
        existing_product["stock"] += quantity
        message = f"✅ Se agregaron {quantity} unidades de {existing_product['name']}. Stock actual: {existing_product['stock']} unidades"
        product_id = existing_product["id"]
    else:
        new_product = {
            "id": len(inventory) + 1,
            "name": product_name.title(),
            "category": category,
            "stock": quantity,
            "minStock": 5
        }
        inventory.append(new_product)
        message = f"✅ Se agregó nuevo producto: {product_name.title()} con {quantity} unidades"
        product_id = new_product["id"]
    
    activities.insert(0, {
        "time": get_current_time(),
        "date": get_current_date(),
        "fullDate": get_full_datetime(),
        "text": message,
        "type": "add",
        "product": existing_product['name'] if existing_product else product_name.title()
    })
    
    # AGREGAR: Marcar producto como interactivo
    interactive_products.add(product_id)
    print(f"🎯 PRODUCTO MARCADO COMO INTERACTIVO (ADD):")
    print(f"   ID: {product_id}")
    print(f"   Nombre: {existing_product['name'] if existing_product else product_name}")
    print(f"   Total interactivos: {len(interactive_products)}")
    print(f"   Set actual: {interactive_products}")
    
    return jsonify({"success": True, "message": message, "inventory": inventory})

@app.route("/api/inventory/sell", methods=["POST"])
def sell_product():
    data = request.json
    product_name = data.get("name")
    quantity = data.get("quantity", 1)
    
    product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
    
    if not product:
        return jsonify({"success": False, "message": f"❌ Producto '{product_name}' no encontrado en el inventario"}), 404
    
    if product["stock"] < quantity:
        return jsonify({"success": False, "message": f"❌ No hay suficiente stock de {product['name']}. Stock actual: {product['stock']} unidades"}), 400
    
    product["stock"] -= quantity
    message = f"💰 Se registró la venta de {quantity} unidades de {product['name']}. Stock restante: {product['stock']} unidades"
    
    activities.insert(0, {
        "time": get_current_time(),
        "date": get_current_date(),
        "fullDate": get_full_datetime(),
        "text": message,
        "type": "sell",
        "product": product['name']
    })
    
    # AGREGAR: Marcar producto como interactivo
    interactive_products.add(product["id"])
    print(f"🎯 PRODUCTO MARCADO COMO INTERACTIVO (SELL):")
    print(f"   ID: {product['id']}")
    print(f"   Nombre: {product['name']}")
    print(f"   Total interactivos: {len(interactive_products)}")
    print(f"   Set actual: {interactive_products}")
    
    return jsonify({"success": True, "message": message, "inventory": inventory})

@app.route("/api/inventory/update", methods=["POST"])
def update_stock():
    data = request.json
    product_name = data.get("name")
    quantity = data.get("quantity")
    
    product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
    
    if not product:
        return jsonify({"success": False, "message": f"❌ Producto '{product_name}' no encontrado"}), 404
    
    old_stock = product["stock"]
    product["stock"] = quantity
    message = f"🔄 Se actualizó el stock de {product['name']} de {old_stock} a {quantity} unidades"
    
    activities.insert(0, {
        "time": get_current_time(),
        "date": get_current_date(),
        "fullDate": get_full_datetime(),
        "text": message,
        "type": "update",
        "product": product['name']
    })
    
    # AGREGAR: Marcar producto como interactivo
    interactive_products.add(product["id"])
    print(f"🎯 PRODUCTO MARCADO COMO INTERACTIVO (UPDATE):")
    print(f"   ID: {product['id']}")
    print(f"   Nombre: {product['name']}")
    print(f"   Total interactivos: {len(interactive_products)}")
    print(f"   Set actual: {interactive_products}")
    
    return jsonify({"success": True, "message": message, "inventory": inventory})

@app.route("/api/activities", methods=["GET"])
def get_activities():
    return jsonify(activities)

# ============================================
# SISTEMA DE VOZ MEJORADO - CONEXIÓN CON INTERFAZ
# ============================================

# Variable para almacenar el último comando procesado
last_command_result = {"success": False, "message": "", "timestamp": 0}

@app.route("/api/start-voice-system", methods=["POST"])
def start_voice_system():
    """Iniciar el sistema completo de voz controlado por 'Gwen'"""
    global transcriber
    
    try:
        if transcriber:
            try:
                transcriber.stop_all()
                time.sleep(0.5)
            except:
                pass
        
        print("🎯 INICIANDO SISTEMA DE VOZ COMPLETO...")
        improve_voice_recognition_quality()
        transcriber = Transcriber()
        
        def on_command_received(command_text):
            """Callback cuando se recibe un comando después de decir 'Gwen'"""
            print(f"📝 Comando recibido: {command_text}")
            process_voice_command_internal(command_text)
        
        # Iniciar el sistema que escucha "Gwen" y luego graba el comando
        transcriber.start_wake_word_system(on_command_received)
        
        return jsonify({
            "success": True,
            "message": "Sistema de voz activado. Di 'Gwen' seguido de tu comando."
        })
        
    except Exception as e:
        print(f"❌ Error iniciando sistema de voz: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Error: {str(e)}"})

@app.route("/api/stop-voice-system", methods=["POST"])
def stop_voice_system():
    """Detener el sistema de voz"""
    global transcriber
    
    try:
        if transcriber:
            transcriber.stop_all()
            transcriber = None
        
        return jsonify({"success": True, "message": "Sistema de voz detenido"})
    except Exception as e:
        print(f"❌ Error deteniendo sistema: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/get-last-command", methods=["GET"])
def get_last_command():
    """Obtener el resultado del último comando procesado"""
    global last_command_result
    return jsonify(last_command_result)

def update_last_command(success, message):
    """Actualizar el último comando procesado"""
    global last_command_result
    last_command_result = {
        "success": success,
        "message": message,
        "timestamp": time.time()
    }

def process_voice_command_internal(command):
    """Procesar comando de voz internamente - MEJORADO"""
    global is_processing
    
    if is_processing:
        print("⚠️ Ya se está procesando un comando, ignorando...")
        return
    
    is_processing = True
    
    try:
        command = command.lower().strip()
        print(f"🎯 Procesando: {command}")
        
        # LIMPIAR "gwen" y todas sus variantes del comando
        wake_words_to_clean = [
            'gwen', 'guen', 'wen', 'when', 'buen', 'bwen',
            'bendy', 'bendi', 'wendy', 'wendi', 'vendi', 'vendy',
            'o bendy', 'o bendi', 'o wendy', 'o wendi', 'o gwen', 'o guen',
            'o wen', 'o when', 'o buen', 'o bwen'
        ]
        
        for wake_word in wake_words_to_clean:
            # Remover del inicio
            if command.startswith(wake_word + ' '):
                command = command[len(wake_word):].strip()
                print(f"🧹 Limpiado '{wake_word}' del inicio: '{command}'")
                break
            elif command.startswith(wake_word):
                command = command[len(wake_word):].strip()
                print(f"🧹 Limpiado '{wake_word}' pegado: '{command}'")
                break
        
        # Remover "o" al inicio si quedó suelto
        if command.startswith('o '):
            command = command[2:].strip()
            print(f"🧹 Limpiado 'o' sobrante: '{command}'")
        
        print(f"📝 Comando limpio: '{command}'")
        
        # ============================================
        # COMANDO: AGREGAR PRODUCTO
        # ============================================
        if any(word in command for word in ["agrega", "añade", "agregar", "pon", "meter", "mete"]):
            quantity = extract_quantity_from_command(command)
            product_name = extract_product_from_command(command)
            
            print(f"📝 Extraído - Producto: '{product_name}', Cantidad: {quantity}")
            
            if product_name and quantity:
                existing_product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if existing_product:
                    old_stock = existing_product["stock"]
                    existing_product["stock"] += quantity
                    message = f"Se agregaron {quantity} unidades de {existing_product['name']}"
                    product_id = existing_product["id"]
                else:
                    new_product = {
                        "id": len(inventory) + 1,
                        "name": product_name.title(),
                        "category": "General",
                        "stock": quantity,
                        "minStock": 5
                    }
                    inventory.append(new_product)
                    message = f"Se agregaron {quantity} unidades de {product_name.title()}"
                    product_id = new_product["id"]
                
                activities.insert(0, {
                    "time": get_current_time(),
                    "date": get_current_date(),
                    "fullDate": get_full_datetime(),
                    "text": message,
                    "type": "add",
                    "product": existing_product['name'] if existing_product else product_name.title()
                })
                
                # MARCAR COMO INTERACTIVO
                interactive_products.add(product_id)
                print(f"🎯 PRODUCTO INTERACTIVO AGREGADO: ID {product_id}")
                
                update_last_command(True, message)
                speak_response(message)
            else:
                if not product_name:
                    error_msg = f"No entendí qué producto agregar en: '{command}'. Ejemplo: 'agrega 10 latas de atún'"
                elif not quantity:
                    error_msg = f"No entendí cuántas unidades agregar de {product_name}. Ejemplo: 'agrega 5 de {product_name}'"
                else:
                    error_msg = "No entendí el comando completo. Ejemplo: 'agrega 10 latas de atún'"
                
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        # ============================================
        # COMANDO: VENDER PRODUCTO
        # ============================================
        elif any(word in command for word in ["vendí", "vender", "vendido", "vendimos", "vende"]):
            product_name = extract_product_from_command(command)
            quantity = extract_quantity_from_command(command)
            
            print(f"📝 Extraído - Producto: '{product_name}', Cantidad: {quantity}")
            
            if product_name and quantity:
                product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if not product:
                    error_msg = f"Producto '{product_name}' no encontrado en el inventario"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
                elif product["stock"] < quantity:
                    error_msg = f"No hay suficiente stock de {product['name']}. Stock actual: {product['stock']} unidades, intentaste vender: {quantity}"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
                else:
                    old_stock = product["stock"]
                    product["stock"] -= quantity
                    message = f"Venta registrada de {quantity} {product['name']}"
                    
                    activities.insert(0, {
                        "time": get_current_time(),
                        "date": get_current_date(),
                        "fullDate": get_full_datetime(),
                        "text": message,
                        "type": "sell",
                        "product": product['name']
                    })
                    
                    # MARCAR COMO INTERACTIVO
                    interactive_products.add(product["id"])
                    print(f"🎯 PRODUCTO INTERACTIVO AGREGADO: ID {product['id']}")
                    
                    update_last_command(True, message)
                    speak_response(message)
            else:
                if not product_name:
                    error_msg = f"No entendí qué producto vender en: '{command}'. Ejemplo: 'vendí 2 paquetes de galletas'"
                else:
                    error_msg = "No entendí la cantidad. Ejemplo: 'vendí 2 paquetes de galletas'"
                
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        # ============================================
        # COMANDO: ACTUALIZAR STOCK
        # ============================================
        elif any(word in command for word in ["actualiza", "actualizar", "cambia", "cambiar", "modifica"]):
            product_name = extract_product_from_command(command)
            quantity = extract_quantity_from_command(command)
            
            print(f"📝 Extraído - Producto: '{product_name}', Cantidad: {quantity}")
            
            if product_name and quantity:
                product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if product:
                    old_stock = product["stock"]
                    product["stock"] = quantity
                    message = f"Stock actualizado: {product['name']} de {old_stock} a {quantity} unidades"
                    
                    activities.insert(0, {
                        "time": get_current_time(),
                        "date": get_current_date(),
                        "fullDate": get_full_datetime(),
                        "text": message,
                        "type": "update",
                        "product": product['name']
                    })
                    
                    # MARCAR COMO INTERACTIVO
                    interactive_products.add(product["id"])
                    print(f"🎯 PRODUCTO INTERACTIVO AGREGADO: ID {product['id']}")
                    
                    update_last_command(True, message)
                    speak_response(message)
                else:
                    error_msg = f"Producto '{product_name}' no encontrado"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
            else:
                error_msg = f"No entendí qué producto o cantidad actualizar en: '{command}'. Ejemplo: 'actualiza el stock de leche a 15'"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        # ============================================
        # COMANDO: CONSULTAR INVENTARIO GENERAL
        # ============================================
        elif any(word in command for word in ["inventario", "stock", "productos", "existencias"]):
            total = len(inventory)
            low_stock = len([p for p in inventory if p["stock"] <= p["minStock"]])
            message = f"Tienes {total} productos en inventario. {low_stock} productos con stock bajo."
            update_last_command(True, message)
            speak_response(message)
        
        # ============================================
        # COMANDO: CONSULTAR STOCK DE PRODUCTO ESPECÍFICO
        # ============================================
        elif any(word in command for word in ["cuánto", "cuanto", "stock de", "hay de"]):
            product_name = extract_product_from_command(command)
            
            if product_name:
                product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                if product:
                    stock_status = "BAJO" if product["stock"] <= product["minStock"] else "OK"
                    message = f"{product['name']}: {product['stock']} unidades. Mínimo: {product['minStock']}. Estado: {stock_status}"
                    update_last_command(True, message)
                    speak_response(message)
                else:
                    error_msg = f"Producto '{product_name}' no encontrado"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
            else:
                error_msg = f"No entendí de qué producto quieres saber el stock en: '{command}'. Ejemplo: 'cuánto stock hay de galletas'"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        # ============================================
        # COMANDO NO RECONOCIDO
        # ============================================
        else:
            error_msg = f"No entendí el comando: '{command}'. Puedo ayudarte con: agregar, vender, actualizar stock o consultar inventario"
            update_last_command(False, error_msg)
            speak_response(error_msg)
    
    except Exception as e:
        print(f"❌ Error procesando comando: {e}")
        import traceback
        traceback.print_exc()
        error_msg = "Hubo un error procesando tu comando. Intenta de nuevo."
        update_last_command(False, error_msg)
        speak_response(error_msg)
    
    finally:
        is_processing = False

def speak_response(text):
    """Generar y reproducir respuesta de voz"""
    try:
        clean_text = clean_text_for_tts(text)
        print(f"🔊 Hablando: {clean_text}")
        
        # Crear instancia de TTS y procesar
        tts = TTS()
        tts.process(clean_text)
        
        # Actualizar la interfaz después de hablar
        threading.Timer(1.0, update_interface).start()
        
    except Exception as e:
        print(f"❌ Error generando voz: {e}")
        import traceback
        traceback.print_exc()

def update_interface():
    """Actualizar la interfaz web después de un comando"""
    try:
        print("🔄 Actualizando interfaz web...")
        # Esta función puede ser extendida para notificar a la interfaz vía WebSockets
        # Por ahora, la interfaz se actualiza cuando el usuario recarga o hace nuevas peticiones
        pass
    except Exception as e:
        print(f"⚠️ Error actualizando interfaz: {e}")

# ============================================
# RUTAS DE VOZ EXISTENTES (PARA BOTONES)
# ============================================

@app.route("/api/process-voice", methods=["POST"])
def process_voice_command():
    """Procesar comando de voz desde la interfaz web (botones)"""
    try:
        data = request.json
        command = data.get("command", "")
        
        print(f"🎯 Comando desde interfaz: {command}")
        
        if not command or command.strip() == "":
            return jsonify({
                "success": False, 
                "message": "No se recibió ningún comando. Por favor, intenta de nuevo."
            })
        
        # Procesar el comando inmediatamente
        process_voice_command_internal(command)
        
        # Esperar un momento y devolver el último resultado
        time.sleep(1)
        return jsonify(last_command_result)
            
    except Exception as e:
        print(f"❌ Error procesando comando: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            "success": False, 
            "message": f"Error procesando comando: {str(e)}"
        })

@app.route("/api/gwen-voice", methods=["POST"])
def gwen_voice_response():
    """Generar respuesta de voz para texto específico"""
    try:
        data = request.json
        text = data.get("text", "")
        
        print(f"🔊 Generando voz para: {text}")
        
        if not text or text.strip() == "":
            return jsonify({"success": False, "message": "No hay texto para convertir a voz"})
        
        clean_text = clean_text_for_tts(text)
        tts_file = TTS().process(clean_text)
        
        return jsonify({
            "success": True, 
            "message": "Audio generado exitosamente",
            "file": tts_file,
            "original_text": text
        })
        
    except Exception as e:
        print(f"❌ Error generando voz: {e}")
        return jsonify({"success": False, "message": f"Error generando voz: {str(e)}"})

@app.route("/api/check-awake", methods=["GET"])
def check_awake():
    """Verificar si el servidor detectó wake word"""
    global last_command_result
    try:
        # Simular detección (debes implementar la lógica real según tu sistema)
        is_awake = last_command_result.get("success", False) and last_command_result.get("timestamp", 0) > time.time() - 5
        return jsonify({"awake": is_awake})
    except Exception as e:
        return jsonify({"awake": False})

@app.route("/api/start-wake-word", methods=["POST"])
def start_wake_word():
    """Iniciar detección de wake word en el servidor"""
    try:
        # Aquí deberías iniciar tu sistema de wake word del servidor
        print("🎯 Servidor: Wake word system iniciado")
        return jsonify({"success": True, "message": "Wake word system iniciado"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route("/api/stop-wake-word", methods=["POST"])
def stop_wake_word():
    """Detener detección de wake word en el servidor"""
    try:
        # Aquí deberías detener tu sistema de wake word del servidor
        print("🎯 Servidor: Wake word system detenido")
        return jsonify({"success": True, "message": "Wake word system detenido"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

# Funciones auxiliares
def get_current_time():
    from datetime import datetime
    return datetime.now().strftime("%H:%M")

def get_current_date():
    from datetime import datetime
    return datetime.now().strftime("%d/%m/%Y")

def get_full_datetime():
    from datetime import datetime
    return datetime.now().isoformat()

def improve_voice_recognition_quality():
    """Mejorar la calidad del reconocimiento de voz"""
    print("🎧 Optimizando reconocimiento de voz...")
    
    # Sugerencias para el usuario
    tips = [
        "💡 Habla en un entorno tranquilo",
        "💡 Di 'Gwen' seguido inmediatamente de tu comando",
        "💡 Ejemplo: 'Gwen agrega 10 latas de atún'",
        "💡 Habla claro y a velocidad normal",
        "💡 Mantén el micrófono a 10-20 cm de tu boca"
    ]
    
    for tip in tips:
        print(tip)

def extract_product_from_command(command):
    """Extracción MEJORADA de productos con múltiples estrategias"""
    try:
        if not command:
            return None
        
        # Diccionario de productos con MUCHAS más variantes
        products = {
            "arroz": ["arroz", "arroces", "arro", "arros", "aros", "a rroz"],
            "frijoles": ["frijoles", "frijol", "porotos", "frij", "frijole", "frijol", "fríjol"],
            "aceite": ["aceite", "aceites", "acei", "aceit", "aceyte", "asete", "aseite"],
            "azúcar": ["azúcar", "azucar", "endulzante", "azu", "azuc", "asucar"],
            "sal": ["sal", "sales"],
            "leche": ["leche", "leches", "lácteo", "lacteo", "lech", "lechee"],
            "galletas": ["galletas", "galleta", "bocadillo", "galle", "galletta", "gallet", "ga", "gal", "galeta"],
            "jabón": ["jabón", "jabon", "jabones", "limpieza", "jab", "javon", "xabon"],
            "atún": ["atún", "atun", "atunes", "enlatado", "tun", "latas de atún", "atum"],
            "café": ["café", "cafe", "cafés", "caf", "cafecito"],
            "pan": ["pan", "panes", "pan fresco", "panecillo", "panecitos"],
            "huevos": ["huevos", "huevo", "docena", "docena de huevos", "huev", "huebo"],
            "pasta": ["pasta", "pastas", "fideos", "spaguetti", "macarrones", "espagueti"],
            "tomate": ["tomate", "tomates", "jitomate", "tomatito"],
            "cebolla": ["cebolla", "cebollas", "cebo"],
            "papa": ["papa", "papas", "patatas", "patata"],
            "zanahoria": ["zanahoria", "zanahorias", "zanah"],
            "pollo": ["pollo", "pollos", "pechuga"],
            "carne": ["carne", "carnes", "res", "bistec"],
            "refresco": ["refresco", "refrescos", "gaseosa", "soda", "refres", "coca"],
            "agua": ["agua", "aguas", "botella", "botella de agua", "agu", "h2o"],
            "yogurt": ["yogurt", "yogur", "yogurth", "yogu"],
            "mantequilla": ["mantequilla", "manteca", "mantequilla", "mante"],
            "queso": ["queso", "quesos"],
            "shampoo": ["shampoo", "champu", "champú", "shamp"],
            "pasta dental": ["pasta dental", "pasta de dientes", "crema dental", "dentífrico"],
            "papel higiénico": ["papel higiénico", "papel", "papel de baño", "higiénico"],
            "detergente": ["detergente", "jabón líquido", "deter"],
            "servilletas": ["servilletas", "servilleta", "toallas de papel"],
            "cereal": ["cereal", "cereales"]
        }
        
        command_lower = command.lower().strip()
        
        # Limpiar palabras comunes que no son productos
        stop_words = ['agrega', 'añade', 'agregar', 'pon', 'meter', 'vendí', 'vender', 
                      'vendido', 'vendimos', 'actualiza', 'actualizar', 'cambia',
                      'unidades', 'de', 'unidad', 'kilos', 'kilo', 'latas', 'paquetes',
                      'el', 'la', 'los', 'las', 'un', 'una', 'unos', 'unas',
                      'stock', 'cuánto', 'cuanto', 'hay', 'tengo', 'tenemos']
        
        print(f"🔍 Buscando producto en: '{command_lower}'")
        
        # ESTRATEGIA 1: Coincidencia exacta de variantes
        for product_key, variants in products.items():
            for variant in variants:
                if variant in command_lower:
                    # Verificar que sea una palabra completa o parte significativa
                    if len(variant) >= 3:
                        print(f"🎯 EXACTO: '{variant}' -> '{product_key}'")
                        return product_key
        
        # ESTRATEGIA 2: Analizar palabra por palabra
        words = command_lower.split()
        best_match = None
        best_similarity = 0
        
        for word in words:
            # Ignorar palabras muy cortas o stop words
            if len(word) <= 2 or word in stop_words:
                continue
            
            # Comparar con cada producto
            for product_key, variants in products.items():
                for variant in variants:
                    # Coincidencia por inicio
                    if variant.startswith(word) and len(word) >= 3:
                        print(f"🎯 INICIO: '{word}' -> '{product_key}' (de '{variant}')")
                        return product_key
                    
                    # Coincidencia por similitud
                    similarity = calculate_word_similarity(word, variant)
                    if similarity > best_similarity and similarity >= 0.7:
                        best_similarity = similarity
                        best_match = product_key
                        print(f"📊 Similitud: '{word}' ≈ '{variant}' ({similarity:.2%})")
        
        if best_match and best_similarity >= 0.7:
            print(f"✅ MEJOR MATCH: '{best_match}' ({best_similarity:.2%})")
            return best_match
        
        # ESTRATEGIA 3: Buscar secuencias de 2-3 palabras (para "latas de atún")
        for i in range(len(words) - 1):
            phrase = ' '.join(words[i:i+3])
            for product_key, variants in products.items():
                for variant in variants:
                    if variant in phrase or phrase in variant:
                        if len(variant) >= 4:
                            print(f"🎯 FRASE: '{phrase}' -> '{product_key}'")
                            return product_key
        
        # ESTRATEGIA 4: Fonética simple (casos especiales)
        phonetic_map = {
            'gallet': 'galletas',
            'xabon': 'jabón',
            'aseite': 'aceite',
            'lechee': 'leche',
            'arros': 'arroz'
        }
        
        for word in words:
            if word in phonetic_map:
                print(f"🎯 FONÉTICA: '{word}' -> '{phonetic_map[word]}'")
                return phonetic_map[word]
        
        print(f"❌ No se detectó producto en: '{command_lower}'")
        print(f"   Palabras analizadas: {[w for w in words if w not in stop_words]}")
        return None
        
    except Exception as e:
        print(f"❌ Error extrayendo producto: {e}")
        import traceback
        traceback.print_exc()
        return None


def calculate_word_similarity(word1, word2):
    """Calcular similitud entre dos palabras usando múltiples métodos"""
    from difflib import SequenceMatcher
    
    # Método 1: SequenceMatcher
    similarity1 = SequenceMatcher(None, word1, word2).ratio()
    
    # Método 2: Letras comunes
    set1 = set(word1)
    set2 = set(word2)
    common = len(set1 & set2)
    total = len(set1 | set2)
    similarity2 = common / total if total > 0 else 0
    
    # Método 3: Subsecuencia común más larga
    def lcs_length(s1, s2):
        m, n = len(s1), len(s2)
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                if s1[i-1] == s2[j-1]:
                    dp[i][j] = dp[i-1][j-1] + 1
                else:
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])
        return dp[m][n]
    
    lcs = lcs_length(word1, word2)
    similarity3 = (2 * lcs) / (len(word1) + len(word2)) if (len(word1) + len(word2)) > 0 else 0
    
    # Retornar el promedio ponderado
    return (similarity1 * 0.4 + similarity2 * 0.3 + similarity3 * 0.3)


def extract_quantity_from_command(command):
    """Extracción MEJORADA de cantidades"""
    try:
        import re
        
        # Buscar números directos
        numbers = re.findall(r'\d+', command)
        if numbers:
            quantity = int(numbers[0])
            print(f"🔢 Cantidad detectada (número): {quantity}")
            return quantity
        
        # Palabras numéricas expandidas
        number_words = {
            'un': 1, 'una': 1, 'uno': 1,
            'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
            'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9,
            'diez': 10, 'once': 11, 'doce': 12, 'docena': 12,
            'quince': 15, 'veinte': 20, 'treinta': 30,
            'media': 0.5, 'medio': 0.5
        }
        
        words = command.lower().split()
        for i, word in enumerate(words):
            if word in number_words:
                quantity = number_words[word]
                
                # Verificar si es "media docena" o "medio kilo"
                if word in ['media', 'medio'] and i + 1 < len(words):
                    next_word = words[i + 1]
                    if 'docena' in next_word:
                        quantity = 6
                    elif 'kilo' in next_word:
                        quantity = 0.5
                
                print(f"🔢 Cantidad detectada (palabra): {quantity}")
                return int(quantity) if quantity >= 1 else 1
        
        # Si no se encuentra, retornar 1
        print(f"🔢 Sin cantidad específica, usando: 1")
        return 1
        
    except Exception as e:
        print(f"⚠️ Error extrayendo cantidad: {e}")
        return 1

def clean_text_for_tts(text):
    import re
    clean_text = re.sub(r'[^\w\s¡!¿?.,;:()\-]', '', text)
    
    clean_text = clean_text.replace('✅', 'Listo')
    clean_text = clean_text.replace('💰', 'Venta registrada')
    clean_text = clean_text.replace('🔄', 'Actualizado')
    clean_text = clean_text.replace('📊', 'Informe')
    clean_text = clean_text.replace('📦', 'Stock')
    clean_text = clean_text.replace('❌', 'Error')
    clean_text = clean_text.replace('⚠️', 'Atención')
    
    # Limpiar espacios múltiples
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    return clean_text

@app.route("/api/test-microphone", methods=["GET"])
def test_microphone():
    """Probar si el micrófono funciona"""
    try:
        import speech_recognition as sr
        r = sr.Recognizer()
        m = sr.Microphone()
        
        with m as source:
            r.adjust_for_ambient_noise(source, duration=1)
        
        return jsonify({
            "success": True,
            "message": "Micrófono funcionando correctamente",
            "energy_threshold": r.energy_threshold
        })
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"Error: {str(e)}"
        })

if __name__ == "__main__":
    app.run(debug=True)