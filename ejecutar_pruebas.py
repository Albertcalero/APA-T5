import estereo

# 1. Convertir de estéreo a mono (canal semisuma)
estereo.estereo2mono("wav/komm.wav", "wav/mono_semisuma.wav", canal=2)

# 2. Codificar la señal estéreo en un contenedor de 32 bits
estereo.codEstereo("wav/komm.wav", "wav/senal_codificada.wav")

# 3. Reconstruir la señal estéreo a partir del contenedor de 32 bits
estereo.decEstereo("wav/senal_codificada.wav", "wav/reconstruida.wav")

print("¡Procesamiento finalizado con éxito!")