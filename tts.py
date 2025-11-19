from gtts import gTTS
import os
import time
import pygame
import tempfile
import threading

# ⭐ OPTIMIZACIÓN: Inicializar pygame una sola vez con configuración optimizada
try:
    pygame.mixer.pre_init(44100, -16, 2, 512)  # Buffer más pequeño
    pygame.mixer.init()
    print("📊 Pygame mixer inicializado (optimizado)")
except Exception as e:
    print(f"❌ Error inicializando pygame: {e}")

class TTS():
    def __init__(self):
        self.is_playing = False
        self._lock = threading.Lock()  # ⭐ Lock para thread-safety
    
    def process(self, text):
        """⭐ OPTIMIZADO: Generación y reproducción más eficiente"""
        temp_file = None
        try:
            # ⭐ Validación temprana
            if not text or len(text.strip()) < 2:
                print("⚠️ Texto demasiado corto para TTS")
                return None
            
            print(f"📊 Generando audio para: {text[:50]}...")
            
            # ⭐ MEJORA: Usar sufijo específico para mejor compatibilidad
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3', mode='wb') as temp:
                temp_file = temp.name
            
            # ⭐ MEJORA: Configuración optimizada de gTTS
            tts = gTTS(
                text=text, 
                lang='es', 
                slow=False,
                tld='com'  # Usar voz más natural
            )
            tts.save(temp_file)
            print(f"✅ Audio temporal generado")
            
            # Reproducir
            success = self.play_audio(temp_file)
            
            # Cleanup con manejo de errores mejorado
            self._cleanup_temp_file(temp_file)
            
            return "audio_temporal" if success else None
            
        except Exception as e:
            print(f"❌ Error generando audio: {e}")
            if temp_file:
                self._cleanup_temp_file(temp_file)
            return None
    
    def _cleanup_temp_file(self, file_path):
        """⭐ Limpieza segura de archivos temporales"""
        try:
            if file_path and os.path.exists(file_path):
                # Esperar brevemente para asegurar que el archivo no esté en uso
                time.sleep(0.3)
                os.remove(file_path)
                print(f"🗑️ Archivo temporal eliminado")
        except Exception as e:
            print(f"⚠️ No se pudo eliminar archivo temporal: {e}")
    
    def play_audio(self, file_path):
        """⭐ OPTIMIZADO: Reproducción más robusta con lock"""
        try:
            if not os.path.exists(file_path):
                print(f"❌ Archivo no encontrado: {file_path}")
                return False
            
            # ⭐ MEJORA: Lock para evitar reproducción simultánea
            with self._lock:
                # Esperar si ya se está reproduciendo
                while self.is_playing:
                    time.sleep(0.1)
                
                self.is_playing = True
                
                try:
                    # ⭐ MEJORA: Configuración optimizada de reproducción
                    pygame.mixer.music.load(file_path)
                    pygame.mixer.music.set_volume(0.8)  # Volumen reducido ligeramente
                    pygame.mixer.music.play()
                    print("📊 Reproduciendo audio...")
                    
                    # ⭐ MEJORA: Espera más eficiente
                    start_time = time.time()
                    max_duration = 30  # Timeout de seguridad
                    
                    while pygame.mixer.music.get_busy():
                        if time.time() - start_time > max_duration:
                            print("⚠️ Timeout de reproducción, deteniendo")
                            pygame.mixer.music.stop()
                            break
                        time.sleep(0.05)  # Check más frecuente
                    
                    print("✅ Audio reproducido correctamente")
                    return True
                    
                finally:
                    self.is_playing = False
                    # ⭐ Liberar recursos
                    try:
                        pygame.mixer.music.unload()
                    except:
                        pass
            
        except Exception as e:
            print(f"❌ Error reproduciendo audio: {e}")
            self.is_playing = False
            return False
    
    def stop(self):
        """⭐ Detener reproducción actual"""
        try:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
                self.is_playing = False
                print("🛑 Reproducción detenida")
        except Exception as e:
            print(f"⚠️ Error deteniendo audio: {e}")