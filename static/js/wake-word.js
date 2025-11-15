class WakeWordManager {
    constructor() {
        this.isListening = false;
        this.recognition = null;
        this.checkInterval = null;
        this.serverAvailable = false;
        this.audioInteracted = false;
        this.lastDetectionTime = 0;
        this.detectionCooldown = 3000; // 3 segundos entre detecciones

        // ⭐ WAKE WORDS RESTRINGIDAS (solo estas 6)
        this.wakeWords = new Set([
            'wen',
            'gwen', 
            'gueen',
            'genn',
            'uen',
            'bueno'
        ]);

        // ⭐ COMANDOS COMPUESTOS ESPECIALES
        this.compoundCommands = {
            'gendy': 'vendí',
            'wendy': 'vendí',
            'gwendi': 'vendí',
            'gendi': 'vendí'
        };
    }

    async startListening() {
        try {
            console.log("🚀 INICIANDO SISTEMA DE WAKE WORD ACTUALIZADO...");
            this.updateUI('🔄 Iniciando sistema...', 'loading');

            this.showVoiceTips();
            await this.ensureAudioPermissions();
            
            this.serverAvailable = await this.checkServer();
            
            if (this.serverAvailable) {
                console.log("✅ Servidor disponible - usando wake word del servidor");
                return await this.startServerWakeWord();
            } else {
                console.log("⚠️ Servidor no disponible - usando wake word local");
                return this.startLocalWakeWord();
            }

        } catch (error) {
            console.error('❌ Error crítico:', error);
            return this.startLocalWakeWord();
        }
    }

    showVoiceTips() {
        console.log("🎧 CONSEJOS PARA MEJOR DETECCIÓN:");
        console.log("💡 Di wake word + comando juntos");
        console.log("💡 Ejemplo: 'Gwen vendí 5 galletas'");
        console.log("💡 Rápido: 'Gendy 3 leches' = 'Gwen vendí 3 leches'");
        console.log("💡 Habla claro y a velocidad normal");
        console.log("💡 Wake words: wen, gwen, gueen, genn, uen, bueno");
    }

    async ensureAudioPermissions() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            stream.getTracks().forEach(track => track.stop());
            this.audioInteracted = true;
            console.log("✅ Permisos de audio concedidos");
        } catch (error) {
            console.warn("⚠️ Permisos de audio no concedidos:", error);
        }
    }

    async checkServer() {
        try {
            const response = await fetch('/api/check-awake', { 
                signal: AbortSignal.timeout(2000) 
            });
            return response.ok;
        } catch (error) {
            return false;
        }
    }

    async startServerWakeWord() {
        try {
            const response = await fetch('/api/start-wake-word', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            if (!response.ok) throw new Error(`HTTP ${response.status}`);

            const data = await response.json();
            if (data.success) {
                this.isListening = true;
                this.startServerCheck();
                this.updateUI('🎯 Escuchando... Di wake word + comando', 'listening');
                console.log("✅ WAKE WORD DEL SERVIDOR ACTIVADO");
                return true;
            } else {
                throw new Error(data.message);
            }
        } catch (error) {
            console.error('❌ Error con servidor:', error);
            this.serverAvailable = false;
            return this.startLocalWakeWord();
        }
    }

    startLocalWakeWord() {
        try {
            if (!('webkitSpeechRecognition' in window) && !('SpeechRecognition' in window)) {
                this.updateUI('❌ Navegador no compatible con voz', 'error');
                return false;
            }

            const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
            this.recognition = new SpeechRecognition();
            
            this.recognition.continuous = true;
            this.recognition.interimResults = true;
            this.recognition.lang = 'es-ES';
            this.recognition.maxAlternatives = 3;

            this.recognition.onstart = () => {
                this.isListening = true;
                this.updateUI('🎯 Escuchando... Di wake word + comando', 'listening');
                console.log("✅ WAKE WORD LOCAL ACTIVADO");
            };

            this.recognition.onresult = (event) => {
                for (let i = event.resultIndex; i < event.results.length; i++) {
                    if (event.results[i].isFinal) {
                        const transcript = event.results[i][0].transcript.toLowerCase();
                        const confidence = event.results[i][0].confidence;
                        
                        console.log(`🔊 Detectado: "${transcript}" (conf: ${confidence.toFixed(2)})`);
                        
                        // Procesar todas las alternativas
                        for (let j = 0; j < event.results[i].length; j++) {
                            const alternative = event.results[i][j].transcript.toLowerCase();
                            
                            if (this.detectWakeWordWithCommand(alternative)) {
                                console.log("🎯 ¡WAKE WORD + COMANDO DETECTADO!");
                                this.onWakeWordDetected();
                                break;
                            }
                        }
                    }
                }
            };

            this.recognition.onerror = (event) => {
                console.error('❌ Error reconocimiento:', event.error);
                
                if (event.error === 'not-allowed') {
                    this.updateUI('❌ Permiso de micrófono denegado', 'error');
                    this.isListening = false;
                } else {
                    setTimeout(() => {
                        if (this.isListening) {
                            this.recognition.start();
                        }
                    }, 1000);
                }
            };

            this.recognition.onend = () => {
                if (this.isListening && this.recognition) {
                    setTimeout(() => {
                        try {
                            this.recognition.start();
                        } catch (e) {
                            console.error('Error reiniciando:', e);
                        }
                    }, 500);
                }
            };

            this.recognition.start();
            return true;

        } catch (error) {
            console.error('❌ Error iniciando wake word local:', error);
            this.updateUI('❌ Error iniciando escucha', 'error');
            return false;
        }
    }

    detectWakeWordWithCommand(text) {
        // Verificar cooldown
        const now = Date.now();
        if (now - this.lastDetectionTime < this.detectionCooldown) {
            console.log('⏳ En cooldown, ignorando...');
            return false;
        }

        const textLower = text.toLowerCase().trim();
        const words = textLower.split(/\s+/);

        console.log(`🔍 Analizando: "${textLower}"`);

        // ⭐ CASO 1: Detectar comandos compuestos PRIMERO
        const firstWord = words[0];
        for (const [compound, action] of Object.entries(this.compoundCommands)) {
            if (firstWord === compound || this.calculateSimilarity(firstWord, compound) >= 0.80) {
                const rest = words.slice(1).join(' ');
                if (rest.length >= 2) {
                    console.log(`🎯 Comando compuesto: '${compound}' → '${action} ${rest}'`);
                    this.lastDetectionTime = now;
                    return true;
                } else {
                    console.log(`❌ Comando compuesto sin parámetros`);
                    return false;
                }
            }
        }

        // ⭐ CASO 2: Wake word normal + comando
        let wakeWordFound = false;
        let wakeWordPosition = -1;

        // Buscar wake word en las primeras 3 palabras
        for (let i = 0; i < Math.min(3, words.length); i++) {
            const word = words[i];
            
            // Coincidencia exacta
            if (this.wakeWords.has(word)) {
                wakeWordFound = true;
                wakeWordPosition = i;
                console.log(`🎯 Wake word exacta: '${word}' en posición ${i}`);
                break;
            }

            // Similitud >= 70%
            for (const wakeWord of this.wakeWords) {
                if (word.length >= 2) {
                    const similarity = this.calculateSimilarity(word, wakeWord);
                    if (similarity >= 0.70) {
                        wakeWordFound = true;
                        wakeWordPosition = i;
                        console.log(`🎯 Wake word similar: '${word}' ≈ '${wakeWord}' (${(similarity * 100).toFixed(0)}%)`);
                        break;
                    }
                }
            }

            if (wakeWordFound) break;
        }

        if (!wakeWordFound) {
            console.log('❌ No se encontró wake word');
            return false;
        }

        // ⭐ VALIDACIÓN CRÍTICA: Debe tener comando después
        const remainingWords = words.slice(wakeWordPosition + 1);
        const remainingText = remainingWords.join(' ');

        if (remainingText.length < 2) {
            console.log(`❌ Wake word sin comando: '${textLower}'`);
            return false;
        }

        // Verificar que tenga palabras de comando
        if (this.hasCommandWords(remainingText)) {
            console.log(`✅ Wake word + comando válido: '${remainingText}'`);
            this.lastDetectionTime = now;
            return true;
        } else {
            console.log(`❌ Wake word pero sin comando válido`);
            return false;
        }
    }

    hasCommandWords(text) {
        const textLower = text.toLowerCase();

        // Verificar números
        if (/\d/.test(textLower)) {
            console.log('   ✅ Contiene números');
            return true;
        }

        // Palabras clave de comandos
        const commandKeywords = [
            // Acciones
            'agrega', 'agregar', 'añade', 'añadir', 'pon', 'poner', 'mete', 'meter',
            'vendí', 'vendi', 'vender', 'vende', 'vendido', 'vendimos',
            'actualiza', 'actualizar', 'cambia', 'cambiar', 'modifica', 'modificar',
            'muestra', 'mostrar', 'ver', 'consultar', 'buscar', 'filtra', 'filtrar',
            'cuánto', 'cuanto', 'hay', 'stock', 'inventario',
            
            // Movimientos
            'venta', 'ventas', 'salida', 'salidas',
            'entrada', 'entradas', 'compra', 'compras',
            'movimiento', 'movimientos', 'historial',
            
            // Temporales
            'hoy', 'ayer', 'semana', 'mes',
            
            // Productos comunes
            'arroz', 'frijol', 'aceite', 'azucar', 'sal', 'leche', 'galleta',
            'jabon', 'atun', 'cafe', 'pan', 'huevo', 'pasta', 'tomate',
            'cebolla', 'papa', 'zanahoria', 'pollo', 'carne', 'refresco',
            'agua', 'yogurt', 'mantequilla', 'queso', 'shampoo',
            
            // Números escritos
            'uno', 'dos', 'tres', 'cuatro', 'cinco', 'seis', 'siete', 'ocho', 'nueve', 'diez',
            'once', 'doce', 'quince', 'veinte', 'treinta', 'docena',
            
            // Unidades
            'unidad', 'unidades', 'kilo', 'kilos', 'litro', 'litros',
            'paquete', 'paquetes', 'lata', 'latas', 'bolsa', 'bolsas'
        ];

        for (const keyword of commandKeywords) {
            if (textLower.includes(keyword)) {
                console.log(`   ✅ Contiene '${keyword}'`);
                return true;
            }
        }

        console.log('   ❌ No contiene palabras de comando');
        return false;
    }

    calculateSimilarity(word1, word2) {
        word1 = word1.toLowerCase();
        word2 = word2.toLowerCase();

        // Método 1: Letras comunes
        const set1 = new Set(word1);
        const set2 = new Set(word2);
        const intersection = new Set([...set1].filter(x => set2.has(x)));
        const union = new Set([...set1, ...set2]);
        const similarity1 = intersection.size / union.size;

        // Método 2: Prefijo común
        let similarity2 = 0;
        if (word1.startsWith(word2.substring(0, 2)) || word2.startsWith(word1.substring(0, 2))) {
            similarity2 = 0.7;
        }

        return Math.max(similarity1, similarity2);
    }

    startServerCheck() {
        console.log("🔄 Iniciando verificación del servidor...");
        this.checkInterval = setInterval(async () => {
            if (!this.isListening) return;
            
            try {
                const response = await fetch('/api/check-awake');
                if (response.ok) {
                    const data = await response.json();
                    if (data.awake) {
                        console.log("🎯 ¡WAKE WORD DETECTADO EN SERVIDOR!");
                        this.onWakeWordDetected();
                    }
                }
            } catch (error) {
                // Error silencioso
            }
        }, 800);
    }

    async stopListening() {
        console.log("🛑 DETENIENDO WAKE WORD...");
        this.isListening = false;

        if (this.recognition) {
            this.recognition.stop();
            this.recognition = null;
        }

        this.stopServerCheck();

        try {
            await fetch('/api/stop-wake-word', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });
        } catch (error) {
            // Ignorar errores
        }

        this.updateUI('🔇 Wake word desactivado', 'stopped');
        console.log("✅ WAKE WORD DETENIDO");
    }

    stopServerCheck() {
        if (this.checkInterval) {
            clearInterval(this.checkInterval);
            this.checkInterval = null;
        }
    }

    onWakeWordDetected() {
        console.log("🎯 ACTIVANDO GRABACIÓN AUTOMÁTICA...");
        this.updateUI('✅ ¡ACTIVADA! Iniciando grabación...', 'activated');

        setTimeout(() => {
            const startBtn = document.getElementById('startBtn');
            if (startBtn && !startBtn.disabled) {
                console.log("🎯 EJECUTANDO GRABACIÓN...");
                
                this.forceUserInteraction();
                startBtn.click();

                const statusElement = document.getElementById('status');
                if (statusElement) {
                    statusElement.textContent = "🎤 Activado por voz - Habla ahora";
                    statusElement.classList.add('auto-recording');
                }

                setTimeout(() => {
                    if (this.isListening) {
                        this.updateUI('🎯 Escuchando... Di wake word + comando', 'listening');
                        console.log("✅ WAKE WORD REACTIVADO");
                    }
                }, 10000);

            } else {
                console.log("⚠️ Botón de grabación no disponible");
                this.updateUI('⚠️ Error al activar grabación', 'warning');
                
                setTimeout(() => {
                    if (this.isListening) {
                        this.updateUI('🎯 Escuchando... Di wake word + comando', 'listening');
                    }
                }, 3000);
            }
        }, 1000);
    }

    forceUserInteraction() {
        try {
            const clicker = document.createElement('button');
            clicker.style.display = 'none';
            document.body.appendChild(clicker);
            clicker.click();
            document.body.removeChild(clicker);
            console.log("✅ Interacción forzada");
        } catch (e) {
            console.warn("⚠️ No se pudo forzar interacción:", e);
        }
    }

    updateUI(message, status) {
        const statusElement = document.getElementById('wakeWordStatus');
        const button = document.getElementById('wakeWordButton');
        
        if (statusElement) {
            statusElement.textContent = message;
            statusElement.className = `wake-word-status ${status}`;
        }
        
        if (button) {
            if (this.isListening) {
                button.textContent = '🛑 Detener Escucha';
                button.classList.add('active');
            } else {
                button.textContent = '🎯 Activar Escucha por Voz';
                button.classList.remove('active');
            }
        }
        
        console.log(`🟡 WAKE WORD UI [${status}]: ${message}`);
    }
}

// Inicialización
document.addEventListener('DOMContentLoaded', function() {
    console.log("🚀 INICIALIZANDO WAKE WORD MANAGER ACTUALIZADO...");
    window.wakeWordManager = new WakeWordManager();
    
    const wakeWordButton = document.getElementById('wakeWordButton');
    if (wakeWordButton) {
        wakeWordButton.addEventListener('click', function() {
            if (window.wakeWordManager.isListening) {
                window.wakeWordManager.stopListening();
            } else {
                window.wakeWordManager.startListening();
            }
        });
    }
});