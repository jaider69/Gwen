from groq import Groq
import os
from dotenv import load_dotenv
import speech_recognition as sr
import threading
import time
import queue
from difflib import SequenceMatcher

class Transcriber:
    def __init__(self, groq_client=None):
        load_dotenv()
        
        if groq_client:
            self.client = groq_client
        else:
            api_key = os.getenv('GROQ_API_KEY')
            if not api_key:
                print("❌ ERROR: GROQ_API_KEY no encontrada en .env")
                raise ValueError("GROQ_API_KEY no configurada")
            print(f"✅ Groq API Key cargada: {api_key[:20]}...")
            self.client = Groq(api_key=api_key)
        
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_running = False
        self.listen_thread = None
        self.audio_queue = queue.Queue()
        
        # Configuración optimizada
        self.recognizer.pause_threshold = 1.8
        self.recognizer.energy_threshold = 80
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.1
        self.recognizer.dynamic_energy_adjustment_ratio = 2.5
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.1
        self.recognizer.non_speaking_duration = 1.5
        
        # ⭐ WAKE WORDS RESTRINGIDAS - Solo estas 6
        self.wake_words = {
            'wen',
            'gwen', 
            'gueen',
            'genn',
            'uen',
            'bueno'
        }
        
        # ⭐ COMANDOS COMPUESTOS ESPECIALES (wake word + vendí en una palabra)
        self.compound_commands = {
            'gendy': 'vendí',
            'wendy': 'vendí',
            'gwendi': 'vendí',
            'gendi': 'vendí'
        }
        
        self._calibrate_microphone()
    
    def _calibrate_microphone(self):
        """Calibración con máxima sensibilidad"""
        print("🔧 Calibrando micrófono...")
        try:
            with self.microphone as source:
                print("   📊 Analizando ruido ambiente (4 segundos)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=4)
                
                if self.recognizer.energy_threshold > 200:
                    self.recognizer.energy_threshold = 100
                elif self.recognizer.energy_threshold < 50:
                    self.recognizer.energy_threshold = 80
                
                print(f"   ✅ Energy threshold: {self.recognizer.energy_threshold}")
                print(f"   ✅ Pause threshold: {self.recognizer.pause_threshold}s")
                
        except Exception as e:
            print(f"⚠️ Advertencia al calibrar: {e}")
            self.recognizer.energy_threshold = 100
    
    def _calculate_similarity(self, word1, word2):
        """Calcular similitud entre dos palabras"""
        similarity1 = SequenceMatcher(None, word1.lower(), word2.lower()).ratio()
        
        set1 = set(word1.lower())
        set2 = set(word2.lower())
        common = len(set1 & set2)
        total = len(set1 | set2)
        similarity2 = common / total if total > 0 else 0
        
        if word1.lower().startswith(word2.lower()[:2]) or word2.lower().startswith(word1.lower()[:2]):
            similarity3 = 0.7
        else:
            similarity3 = 0
        
        return max(similarity1, similarity2, similarity3)
    
    def _detect_compound_command(self, text):
        """
        Detectar comandos compuestos especiales (gendy = gwen + vendí)
        Retorna: (es_compuesto, acción_expandida, resto_del_texto)
        """
        if not text:
            return False, None, None
        
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        if not words:
            return False, None, None
        
        first_word = words[0]
        
        # Buscar coincidencia exacta
        for compound, action in self.compound_commands.items():
            if first_word == compound:
                rest = ' '.join(words[1:])
                print(f"🎯 COMANDO COMPUESTO: '{compound}' → 'gwen {action} {rest}'")
                return True, action, rest
            
            # Similitud alta para variaciones de pronunciación
            if len(first_word) >= 4:
                similarity = self._calculate_similarity(first_word, compound)
                if similarity >= 0.80:
                    rest = ' '.join(words[1:])
                    print(f"🎯 COMANDO COMPUESTO SIMILAR: '{first_word}' ≈ '{compound}' ({similarity:.2%}) → 'gwen {action} {rest}'")
                    return True, action, rest
        
        return False, None, None
    
    def _has_command_words(self, text):
        """
        ⭐ NUEVA FUNCIÓN: Verificar si el texto contiene palabras de comando
        Solo se activa Gwen si hay un comando presente
        """
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Palabras clave que indican comandos válidos
        command_keywords = [
            # Acciones
            'agrega', 'agregar', 'añade', 'añadir', 'pon', 'poner', 'mete', 'meter',
            'vendí', 'vender', 'vende', 'vendido', 'vendimos',
            'actualiza', 'actualizar', 'cambia', 'cambiar', 'modifica', 'modificar',
            'muestra', 'mostrar', 'ver', 'consultar', 'buscar', 'filtra', 'filtrar',
            'cuánto', 'cuanto', 'hay',
            
            # Tipos de movimientos
            'venta', 'ventas', 'salida', 'salidas',
            'entrada', 'entradas', 'compra', 'compras',
            'movimiento', 'movimientos', 'historial',
            
            # Temporales
            'hoy', 'ayer', 'semana', 'mes',
            
            # Productos comunes (para detectar contexto)
            'arroz', 'frijol', 'aceite', 'azúcar', 'sal', 'leche', 'galleta',
            'jabón', 'atún', 'café', 'pan', 'huevo', 'pasta', 'tomate',
            'cebolla', 'papa', 'zanahoria', 'pollo', 'carne', 'refresco',
            'agua', 'yogurt', 'mantequilla', 'queso', 'shampoo',
            
            # Números (indica cantidad)
            'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez',
            'once', 'doce', 'quince', 'veinte', 'treinta', 'docena',
            
            # Unidades
            'unidad', 'unidades', 'kilo', 'kilos', 'gramo', 'gramos',
            'litro', 'litros', 'paquete', 'paquetes', 'lata', 'latas',
            'bolsa', 'bolsas', 'caja', 'cajas'
        ]
        
        # Verificar si contiene números
        if any(char.isdigit() for char in text_lower):
            print(f"   ✅ Tiene números - Es comando válido")
            return True
        
        # Verificar palabras clave
        for keyword in command_keywords:
            if keyword in text_lower:
                print(f"   ✅ Contiene '{keyword}' - Es comando válido")
                return True
        
        print(f"   ❌ No contiene palabras de comando")
        return False
    
    def _is_wake_word_detected(self, text):
        """
        ⭐ DETECCIÓN MEJORADA: Solo activa si tiene wake word + comando
        """
        if not text or len(text.strip()) < 3:
            return False
        
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        print(f"🔍 Analizando: '{text_lower}'")
        
        # CASO ESPECIAL 1: Comandos compuestos (siempre válidos)
        is_compound, _, rest = self._detect_compound_command(text_lower)
        if is_compound:
            # Verificar que tenga algo después del comando compuesto
            if rest and len(rest) >= 2:
                print(f"✅ Comando compuesto con parámetros: '{rest}'")
                return True
            else:
                print(f"❌ Comando compuesto sin parámetros")
                return False
        
        # CASO NORMAL: Wake word + comando
        wake_word_found = False
        wake_word_position = -1
        
        # Buscar wake word en las primeras 3 palabras
        for i, word in enumerate(words[:3]):
            # Coincidencia exacta
            if word in self.wake_words:
                wake_word_found = True
                wake_word_position = i
                print(f"🎯 Wake word encontrada: '{word}' en posición {i}")
                break
            
            # Similitud alta (>=70%)
            for wake_word in self.wake_words:
                if len(word) >= 2:
                    similarity = self._calculate_similarity(word, wake_word)
                    if similarity >= 0.70:
                        wake_word_found = True
                        wake_word_position = i
                        print(f"🎯 Wake word similar: '{word}' ≈ '{wake_word}' ({similarity:.2%})")
                        break
            
            if wake_word_found:
                break
        
        if not wake_word_found:
            print(f"❌ No se encontró wake word en las primeras palabras")
            return False
        
        # ⭐ VALIDACIÓN CRÍTICA: Debe tener comando después de la wake word
        remaining_text = ' '.join(words[wake_word_position + 1:])
        
        if not remaining_text or len(remaining_text) < 2:
            print(f"❌ Wake word sin comando: '{text_lower}'")
            return False
        
        # Verificar que el texto restante tenga palabras de comando
        if self._has_command_words(remaining_text):
            print(f"✅ Wake word + comando válido: '{remaining_text}'")
            return True
        else:
            print(f"❌ Wake word detectada pero sin comando válido")
            return False
    
    def _extract_command_after_wake_word(self, text):
        """Extraer y expandir comando"""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        print(f"🔧 Extrayendo comando de: '{text_lower}'")
        
        # CASO 1: Comando compuesto - expandir automáticamente
        is_compound, action, rest = self._detect_compound_command(text_lower)
        
        if is_compound:
            if rest and len(rest) >= 2:
                expanded_command = f"{action} {rest}".strip()
                print(f"   ✅ COMANDO EXPANDIDO: '{expanded_command}'")
                return expanded_command
            else:
                print(f"   ❌ Comando compuesto sin parámetros")
                return None
        
        # CASO 2: Wake word normal - remover y extraer comando
        words = text_lower.split()
        
        # Buscar posición de wake word
        wake_word_position = -1
        for i, word in enumerate(words[:3]):
            if word in self.wake_words:
                wake_word_position = i
                break
            
            for wake_word in self.wake_words:
                if self._calculate_similarity(word, wake_word) >= 0.70:
                    wake_word_position = i
                    break
            
            if wake_word_position != -1:
                break
        
        if wake_word_position == -1:
            print(f"   ❌ No se encontró wake word")
            return None
        
        # Extraer todo después de la wake word
        command = ' '.join(words[wake_word_position + 1:])
        
        if command and len(command) >= 3:
            print(f"   ✅ Comando extraído: '{command}'")
            return command
        
        print(f"   ❌ Comando muy corto o vacío")
        return None
    
    def _record_audio(self, timeout=10, phrase_time_limit=30):
        """Grabación con timeouts máximos"""
        try:
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.3)
                
                print(f"🎤 Grabando... (max {phrase_time_limit}s)")
                
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )
                
                print(f"✅ Audio capturado ({len(audio.frame_data)} bytes)")
                return audio
                
        except sr.WaitTimeoutError:
            print("⏱️ Timeout - no se detectó audio")
            return None
        except Exception as e:
            print(f"❌ Error grabando: {e}")
            return None
    
    def _transcribe_audio(self, audio):
        """Transcribir audio con múltiples métodos"""
        if not audio:
            return None
        
        # Google ES
        try:
            print("🔄 Transcribiendo con Google (es-ES)...")
            text = self.recognizer.recognize_google(audio, language='es-ES')
            if text:
                print(f"✅ Google: '{text}'")
                return text.lower().strip()
        except sr.UnknownValueError:
            print("❓ Google no entendió")
        except sr.RequestError as e:
            print(f"⚠️ Error Google API: {e}")
        
        # Google MX
        try:
            print("🔄 Google (es-MX)...")
            text = self.recognizer.recognize_google(audio, language='es-MX')
            if text:
                print(f"✅ Google MX: '{text}'")
                return text.lower().strip()
        except:
            pass
        
        # Groq Whisper
        try:
            print("🔄 Groq Whisper...")
            return self._transcribe_with_groq(audio)
        except Exception as e:
            print(f"❌ Groq falló: {e}")
        
        return None
    
    def _transcribe_with_groq(self, audio):
        """Transcribir usando Groq Whisper"""
        try:
            temp_file = "temp_audio.wav"
            with open(temp_file, "wb") as f:
                f.write(audio.get_wav_data())
            
            with open(temp_file, "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language="es",
                    response_format="text",
                    temperature=0.2
                )
            
            try:
                os.remove(temp_file)
            except:
                pass
            
            result = transcription.strip()
            if result:
                print(f"✅ Groq: '{result}'")
                return result.lower()
            return None
            
        except Exception as e:
            print(f"❌ Error Groq: {e}")
            return None
    
    def start_wake_word_system(self, on_command_callback):
        """Sistema de escucha con activación condicional"""
        if self.is_running:
            print("⚠️ Sistema ya corriendo")
            return
        
        self.is_running = True
        
        def listen_loop():
            print("\n" + "="*60)
            print("🎯 SISTEMA DE VOZ ACTIVADO")
            print("📋 Wake words: wen, gwen, gueen, genn, uen, bueno")
            print("⭐ Especiales: gendy, wendy, gwendi, gendi = 'gwen vendí'")
            print("")
            print("💡 IMPORTANTE: Debes decir wake word + comando")
            print("   ✅ 'Gwen vendí 5 galletas'")
            print("   ✅ 'Gendy 3 leches'")
            print("   ✅ 'Uen agrega 10 arroz'")
            print("   ❌ 'Gwen' (solo, sin comando)")
            print("="*60 + "\n")
            
            consecutive_errors = 0
            max_errors = 3
            successful_detections = 0
            
            while self.is_running:
                try:
                    audio = self._record_audio(timeout=10, phrase_time_limit=30)
                    
                    if audio is None:
                        continue
                    
                    text = self._transcribe_audio(audio)
                    
                    if not text or len(text.strip()) < 3:
                        print("⚠️ Texto muy corto")
                        continue
                    
                    print(f"\n🔊 Transcrito: '{text}'")
                    
                    # Verificar wake word CON comando
                    if self._is_wake_word_detected(text):
                        print("🎉 ¡ACTIVADO!")
                        successful_detections += 1
                        
                        command = self._extract_command_after_wake_word(text)
                        
                        if command and len(command) >= 3:
                            print(f"✅ Ejecutando: '{command}'")
                            consecutive_errors = 0
                            on_command_callback(command)
                            time.sleep(2)
                        else:
                            print("❌ No se pudo extraer comando válido")
                    else:
                        print("❌ No cumple criterios de activación")
                    
                    consecutive_errors = 0
                    
                except KeyboardInterrupt:
                    print("\n🛑 Detenido")
                    break
                except Exception as e:
                    print(f"❌ Error: {e}")
                    consecutive_errors += 1
                    time.sleep(0.5)
                    
                    if consecutive_errors >= max_errors:
                        print(f"⚠️ Recalibrando...")
                        self._calibrate_microphone()
                        consecutive_errors = 0
                        time.sleep(2)
            
            print(f"\n📊 Detecciones: {successful_detections}")
            print("🔇 Sistema detenido")
        
        self.listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listen_thread.start()
        print("✅ Sistema iniciado")
    
    def stop_all(self):
        """Detener sistema"""
        print("🛑 Deteniendo...")
        self.is_running = False
        if self.listen_thread:
            self.listen_thread.join(timeout=2)
        print("✅ Detenido")