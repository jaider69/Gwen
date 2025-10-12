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

# Inventario en memoria
inventory = [
    {"id": 1, "name": "Arroz", "category": "Granos", "stock": 25, "minStock": 10},
    {"id": 2, "name": "Frijoles", "category": "Granos", "stock": 18, "minStock": 8},
    {"id": 3, "name": "Aceite", "category": "Aceites", "stock": 12, "minStock": 5},
    {"id": 4, "name": "Azúcar", "category": "Endulzantes", "stock": 30, "minStock": 10},
    {"id": 5, "name": "Sal", "category": "Condimentos", "stock": 15, "minStock": 5},
    {"id": 6, "name": "Leche", "category": "Lácteos", "stock": 8, "minStock": 10},
    {"id": 7, "name": "Galletas", "category": "Snacks", "stock": 22, "minStock": 15},
    {"id": 8, "name": "Jabón", "category": "Limpieza", "stock": 14, "minStock": 10},
    {"id": 9, "name": "Atún", "category": "Enlatados", "stock": 15, "minStock": 8}
]

activities = []

@app.route("/gwen")
def gwen():
    return render_template("gwen.html")

# RUTAS PARA EL INVENTARIO
@app.route("/api/inventory", methods=["GET"])
def get_inventory():
    return jsonify(inventory)

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
    
    activities.insert(0, {
        "time": get_current_time(),
        "text": message,
        "type": "add"
    })
    
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
        "text": message,
        "type": "sell"
    })
    
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
        "text": message,
        "type": "update"
    })
    
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
    """Procesar comando de voz internamente"""
    global is_processing
    
    if is_processing:
        print("⚠️ Ya se está procesando un comando, ignorando...")
        return
    
    is_processing = True
    
    try:
        command = command.lower()
        print(f"🎯 Procesando: {command}")
        
        # Limpiar "gwen" del comando si está presente
        wake_words = ['gwen', 'guen', 'wen', 'buen']
        for wake_word in wake_words:
            if command.startswith(wake_word + ' '):
                command = command.replace(wake_word, '').strip()
                print(f"🔧 Comando limpiado: '{command}'")
                break
        
        if any(word in command for word in ["agrega", "añade", "agregar", "pon", "meter"]):
            # Primero intenta extraer cantidad
            quantity = extract_quantity_from_command(command)
            # Luego producto
            product_name = extract_product_from_command(command)
        
            print(f"🔍 Debug - Producto: {product_name}, Cantidad: {quantity}")
        
            if not product_name:
                # Si no encontró producto, busca palabras que puedan ser productos
                words = command.split()
                potential_products = []
                for word in words:
                    if word not in ["agrega", "añade", "agregar", "pon", "meter", "unidades", "de", "unidad", "kilos", "kilo"]:
                        if len(word) > 3:  # Palabras de más de 3 letras
                            potential_products.append(word)
            
                if potential_products:
                    product_name = potential_products[0]
                    print(f"🔍 Producto potencial detectado: {product_name}")
        
            if product_name and quantity:
                existing_product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
            
                if existing_product:
                    old_stock = existing_product["stock"]
                    existing_product["stock"] += quantity
                    message = f"Se agregaron {quantity} unidades de {existing_product['name']}. Stock anterior: {old_stock}, Stock actual: {existing_product['stock']} unidades"
                else:
                    new_product = {
                        "id": len(inventory) + 1,
                        "name": product_name.title(),
                        "category": "General",
                        "stock": quantity,
                        "minStock": 5
                    }
                    inventory.append(new_product)
                    message = f"Nuevo producto agregado: {product_name.title()} con {quantity} unidades"
                
                activities.insert(0, {
                    "time": get_current_time(),
                    "text": message,
                    "type": "add"
                })
            
                update_last_command(True, message)
                speak_response(message)
            else:
                error_msg = "No entendí qué producto o cantidad agregar. Ejemplo: 'Gwen agrega 10 latas de atún'"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        elif any(word in command for word in ["vendí", "vender", "vendido", "vendimos"]):
            product_name = extract_product_from_command(command)
            quantity = extract_quantity_from_command(command)
            
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
                    message = f"Venta registrada: {quantity} unidades de {product['name']}. Stock anterior: {old_stock}, Stock restante: {product['stock']} unidades"
                    
                    activities.insert(0, {
                        "time": get_current_time(),
                        "text": message,
                        "type": "sell"
                    })
                    
                    update_last_command(True, message)
                    speak_response(message)
            else:
                error_msg = "No entendí qué producto o cantidad vender. Ejemplo: 'Gwen vendí 2 paquetes de galletas'"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        elif any(word in command for word in ["actualiza", "actualizar", "cambia"]):
            product_name = extract_product_from_command(command)
            quantity = extract_quantity_from_command(command)
            
            if product_name and quantity:
                product = next((p for p in inventory if p["name"].lower() == product_name.lower()), None)
                
                if product:
                    old_stock = product["stock"]
                    product["stock"] = quantity
                    message = f"Stock actualizado: {product['name']} de {old_stock} a {quantity} unidades"
                    
                    activities.insert(0, {
                        "time": get_current_time(),
                        "text": message,
                        "type": "update"
                    })
                    
                    update_last_command(True, message)
                    speak_response(message)
                else:
                    error_msg = f"Producto '{product_name}' no encontrado"
                    update_last_command(False, error_msg)
                    speak_response(error_msg)
            else:
                error_msg = "No entendí qué producto o cantidad actualizar. Ejemplo: 'Gwen actualiza el stock de leche a 15'"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        elif any(word in command for word in ["inventario", "stock", "productos", "existencias"]):
            total = len(inventory)
            low_stock = len([p for p in inventory if p["stock"] <= p["minStock"]])
            message = f"Tienes {total} productos en inventario. {low_stock} productos con stock bajo."
            update_last_command(True, message)
            speak_response(message)
        
        elif any(word in command for word in ["cuánto", "cuanto", "stock de"]):
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
                error_msg = "No entendí de qué producto quieres saber el stock. Ejemplo: 'Gwen cuánto stock hay de galletas'"
                update_last_command(False, error_msg)
                speak_response(error_msg)
        
        else:
            error_msg = "No entendí el comando. Puedo ayudarte con: agregar, vender, actualizar stock o consultar inventario"
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

# Funciones auxiliares
def get_current_time():
    from datetime import datetime
    return datetime.now().strftime("%H:%M")

def extract_product_from_command(command):
    try:
        if not command:
            return None
            
        products = {
            "arroz": ["arroz", "arroces"],
            "frijoles": ["frijoles", "frijol", "porotos"],
            "aceite": ["aceite", "aceites", "aceite de cocina"],
            "azúcar": ["azúcar", "azucar", "endulzante"],
            "sal": ["sal"],
            "leche": ["leche", "leches", "lácteo", "lacteo"],
            "galletas": ["galletas", "galleta", "bocadillo"],
            "jabón": ["jabón", "jabon", "jabones", "limpieza"],
            "atún": ["atún", "atun", "atunes", "enlatado"],
            "agua": ["agua", "aguas", "botella de agua"],
            "pan": ["pan", "panes", "pan fresco"],
            "huevos": ["huevos", "huevo", "docena de huevos"],
            "café": ["café", "cafe", "cafés"],
            "refresco": ["refresco", "refrescos", "gaseosa", "soda"]
        }
        
        command_lower = command.lower()
        
        # Buscar productos en el comando
        for product_key, variants in products.items():
            for variant in variants:
                if variant in command_lower:
                    return product_key
        
        return None
        
    except Exception as e:
        print(f"Error extrayendo producto: {e}")
        return None
        
    except Exception as e:
        print(f"Error extrayendo producto: {e}")
        return None

def extract_quantity_from_command(command):
    try:
        import re
        numbers = re.findall(r'\d+', command)
        if numbers:
            return int(numbers[0])
        
        number_words = {
            'un': 1, 'una': 1, 'uno': 1,
            'dos': 2, 'tres': 3, 'cuatro': 4, 'cinco': 5,
            'seis': 6, 'siete': 7, 'ocho': 8, 'nueve': 9, 'diez': 10
        }
        
        words = command.lower().split()
        for word in words:
            if word in number_words:
                return number_words[word]
        
        return 1
    except:
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