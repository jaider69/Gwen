from groq import Groq
import os
from dotenv import load_dotenv
import speech_recognition as sr
import threading
import time

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
        
        # UNA SOLA instancia de reconocedor y micrófono
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        self.is_running = False
        self.listen_thread = None
        
        # Configuración MEJORADA del reconocedor
        self.recognizer.pause_threshold = 1.5  # Más tiempo entre frases
        self.recognizer.energy_threshold = 1500  # Más sensible
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.operation_timeout = 15  # Timeout más largo
        
        # Calibrar UNA VEZ
        print("🔧 Calibrando micrófono...")
        try:
            with self.microphone as source:
                print("   Ajustando ruido ambiente (2 segundos)...")
                self.recognizer.adjust_for_ambient_noise(source, duration=2)
                print(f"   ✅ Energy threshold: {self.recognizer.energy_threshold}")
        except Exception as e:
            print(f"⚠️ Advertencia al calibrar: {e}")
    
    def transcribe(self, audio):
        """Transcribir archivo de audio usando Groq Whisper"""
        try:
            audio.save("audio.mp3")
            with open("audio.mp3", "rb") as audio_file:
                transcription = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    language="es",
                    response_format="text"
                )
            print(f"✅ Transcripción exitosa: {transcription}")
            return transcription
        except Exception as e:
            print(f"❌ Error en transcripción: {e}")
            return ""
    
    def start_wake_word_system(self, on_command_callback):
        """
        Sistema completo: escucha 'Gwen', graba comando, procesa
        """
        if self.is_running:
            print("⚠️ El sistema ya está corriendo")
            return
        
        self.is_running = True
        
        def listen_loop():
            print("\n" + "="*60)
            print("🎯 SISTEMA DE VOZ INICIADO")
            print("👂 ESCUCHANDO ACTIVAMENTE...")
            print("   Di 'Gwen' claramente para activar")
            print("="*60 + "\n")
            
            consecutive_errors = 0
            max_errors = 10
            
            while self.is_running:
                try:
                    print("🎤 [Esperando audio...]", end=" ", flush=True)
                    
                    # PASO 1: Escuchar por "Gwen" - TIEMPO MÁS LARGO
                    with self.microphone as source:
                        try:
                            audio = self.recognizer.listen(
                                source, 
                                timeout=5,  # 5 segundos de timeout
                                phrase_time_limit=6   # 6 segundos para frase
                            )
                            print("✓ Audio capturado")
                        except sr.WaitTimeoutError:
                            print("⏱️ Timeout (silencio)")
                            continue
                    
                    # Reconocer si dijo "Gwen"
                    try:
                        print("🔍 Reconociendo...", end=" ", flush=True)
                        text = self.recognizer.recognize_google(audio, language='es-ES').lower()
                        print(f"📝 Texto: '{text}'")
                        
                        # Buscar "Gwen" o variantes - AMPLIADO para mejor detección
                        wake_words = [
                            'gwen', 'guen', 'wen', 'guin', 'güen', 'gwyn', 'when',
                            'gwen', 'gen', 'jen', 'guen', 'gwen', 'glenn', 'glen',
                            'guen', 'bueno', 'guén', 'huén', 'wen', 'wend', 'gwend',
                            'quenel', 'quenl', 'queen', 'quen', 'guen', 'gween'
                        ]
                        
                        detected = False
                        detected_word = None
                        
                        # Buscar coincidencias exactas primero
                        for wake in wake_words:
                            if wake in text:
                                detected = True
                                detected_word = wake
                                break
                        
                        # Si no encuentra exacto, buscar palabras que empiecen similar
                        if not detected:
                            words = text.split()
                            for word in words:
                                # Buscar palabras que empiecen con 'g', 'w', 'b' y tengan 'en' o 'uen'
                                if (word.startswith(('g', 'w', 'b', 'q', 'h')) and 
                                    ('en' in word or 'uen' in word or 'wen' in word or 'gen' in word)):
                                    detected = True
                                    detected_word = word
                                    break
                        
                        if detected:
                            print("\n" + "🎯"*20)
                            print("🎯 ¡¡¡GWEN DETECTADO!!!")
                            print("🎯"*20 + "\n")
                            
                            consecutive_errors = 0  # Resetear errores
                            
                            # NUEVO: Verificar si el comando está en la misma frase
                            # Remover "gwen" y sus variantes del texto
                            command_in_same_phrase = text
                            for wake in wake_words:
                                command_in_same_phrase = command_in_same_phrase.replace(wake, '').strip()
                            
                            # Si hay texto después de "Gwen", usarlo como comando
                            if command_in_same_phrase and len(command_in_same_phrase) > 3:
                                print(f"✅ COMANDO DETECTADO EN LA MISMA FRASE: '{command_in_same_phrase}'")
                                print(f"⚙️ Procesando comando...")
                                on_command_callback(command_in_same_phrase)
                            else:
                                # PASO 2: Grabar el comando por separado - TIEMPO MÁS LARGO
                                print("🎤 GRABANDO TU COMANDO (habla ahora - tienes 15 segundos)...")
                                time.sleep(0.5)  # Pequeña pausa
                                
                                try:
                                    with self.microphone as source:
                                        # Grabar el comando (15 segundos max) - MÁS TIEMPO
                                        print("   👂 Escuchando comando...")
                                        command_audio = self.recognizer.listen(
                                            source, 
                                            timeout=3,  # 3 segundos para empezar
                                            phrase_time_limit=15  # 15 segundos máximo
                                        )
                                        print("   ✅ Comando capturado")
                                    
                                    # PASO 3: Transcribir el comando
                                    print("📝 Transcribiendo tu comando...")
                                    command_text = self.recognizer.recognize_google(
                                        command_audio, 
                                        language='es-ES'
                                    )
                                    print(f"✅ COMANDO: '{command_text}'")
                                    
                                    # PASO 4: Ejecutar callback con el comando
                                    if command_text and command_text.strip():
                                        print(f"⚙️ Procesando comando...")
                                        on_command_callback(command_text)
                                    else:
                                        print("⚠️ Comando vacío, ignorando")
                                    
                                except sr.WaitTimeoutError:
                                    print("⏱️ No detecté comando después de 'Gwen'")
                                    print("   💡 Tip: Di todo junto: 'Gwen agrega 10 galletas'")
                                    # Dar feedback de error
                                    on_command_callback("comando_no_detectado")
                                except sr.UnknownValueError:
                                    print("❌ No entendí el comando")
                                    print("   💡 Tip: Habla más claro y despacio")
                                    on_command_callback("comando_no_entendido")
                                except sr.RequestError as e:
                                    print(f"❌ Error en API de Google: {e}")
                                    consecutive_errors += 1
                                    on_command_callback("error_servicio_voz")
                            
                            # Pausa antes de volver a escuchar "Gwen"
                            print("\n⏳ Esperando 3 segundos...")
                            time.sleep(3)
                            print("👂 Volviendo a escuchar 'Gwen'...\n")
                        else:
                            # No era "Gwen", continuar escuchando silenciosamente
                            pass
                        
                        consecutive_errors = 0  # Resetear si todo va bien
                    
                    except sr.UnknownValueError:
                        # No se entendió, continuar escuchando
                        print("❓ No entendí (normal)")
                        consecutive_errors = 0  # No es un error real
                        continue
                    except sr.RequestError as e:
                        print(f"❌ Error en API de Google: {e}")
                        consecutive_errors += 1
                        time.sleep(2)
                
                except Exception as e:
                    print(f"\n❌ Error en loop: {e}")
                    import traceback
                    traceback.print_exc()
                    consecutive_errors += 1
                    time.sleep(1)
                
                # Si hay muchos errores consecutivos, avisar
                if consecutive_errors >= max_errors:
                    print("\n" + "❌"*30)
                    print(f"❌ Demasiados errores ({consecutive_errors}). Deteniendo sistema.")
                    print("❌ Posibles causas:")
                    print("   - Problemas de conexión a internet")
                    print("   - Micrófono no funciona correctamente")
                    print("   - API de Google con límite de uso")
                    print("❌"*30)
                    self.is_running = False
                    break
            
            print("\n🔇 Sistema de voz detenido\n")
        
        # Iniciar el thread
        self.listen_thread = threading.Thread(target=listen_loop, daemon=True)
        self.listen_thread.start()
        print("✅ Thread de escucha iniciado")
    
    def stop_all(self):
        """Detener TODO el sistema de voz"""
        print("\n🛑 Deteniendo sistema de voz...")
        self.is_running = False
        
        if self.listen_thread and self.listen_thread.is_alive():
            print("   Esperando que el thread termine...")
            self.listen_thread.join(timeout=3)
        
        print("✅ Sistema de voz detenido completamente\n")