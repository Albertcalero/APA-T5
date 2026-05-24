"""
Albert Calero
"""

import struct

def leer_cabecera_y_datos(fichero):
    """
    Función auxiliar para leer y desempaquetar la cabecera de un fichero WAVE.
    Valida que el archivo cumpla con el formato estructurado RIFF/WAVE PCM.
    
    Devuelve un diccionario con los metadatos y los datos brutos del subcacho 'data'.
    """
    with open(fichero, 'rb') as f:
        # Leer el contenedor principal RIFF (12 bytes iniciales)
        riff_header = f.read(12)
        if len(riff_header) < 12:
            raise ValueError(f"El fichero '{fichero}' está incompleto o corrupto.")
        
        riff, size, wave = struct.unpack('<4sI4s', riff_header)
        if riff != b'RIFF' or wave != b'WAVE':
            raise ValueError(f"El fichero '{fichero}' no es un archivo WAVE válido.")
        
        fmt_data = None
        data_bytes = b''
        
        # Recorrer secuencialmente los subcachos del archivo
        while True:
            chunk_header = f.read(8)
            if len(chunk_header) < 8:
                break
            chunk_id, chunk_size = struct.unpack('<4sI', chunk_header)
            
            if chunk_id == b'fmt ':
                fmt_data = f.read(chunk_size)
                # Alineación a palabra par en formato RIFF
                if chunk_size % 2 != 0:
                    f.read(1)
            elif chunk_id == b'data':
                data_bytes = f.read(chunk_size)
                if chunk_size % 2 != 0:
                    f.read(1)
            else:
                # Saltar cachos adicionales (como JUNK o LIST) de forma segura
                f.seek(chunk_size + (chunk_size % 2), 1)
        
        if not fmt_data:
            raise ValueError("No se ha localizado el subcacho obligatorio 'fmt '.")
        if not data_bytes:
            raise ValueError("No se ha localizado el subcacho obligatorio 'data'.")
        
        # Extraer metadatos del formato de audio (primeros 16 bytes de 'fmt ')
        audio_format, num_channels, sample_rate, byte_rate, block_align, bits_per_sample = struct.unpack(
            '<HHIIHH', fmt_data[:16]
        )
        
        if audio_format != 1:
            raise ValueError("Formato no soportado. Solo se admite PCM lineal sin compresión.")
            
        return {
            'num_channels': num_channels,
            'sample_rate': sample_rate,
            'bits_per_sample': bits_per_sample,
            'data': data_bytes
        }


def escribir_fichero_wave(fichero, num_channels, sample_rate, bits_per_sample, datos_brutos):
    """
    Función auxiliar para empaquetar y escribir las cabeceras RIFF/WAVE 
    estructuradas junto a los datos de audio binarios correspondientes.
    """
    subchunk1_size = 16
    audio_format = 1  # PCM Lineal
    block_align = num_channels * (bits_per_sample // 8)
    byte_rate = sample_rate * block_align
    subchunk2_size = len(datos_brutos)
    riff_size = 4 + (8 + subchunk1_size) + (8 + subchunk2_size)
    
    cabecera = struct.pack(
        '<4sI4s4sIHHIIHH4sI',
        b'RIFF', riff_size, b'WAVE',
        b'fmt ', subchunk1_size, audio_format, num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
        b'data', subchunk2_size
    )
    
    with open(fichero, 'wb') as f:
        f.write(cabecera)
        f.write(datos_brutos)


def estereo2mono(ficEste, ficMono, canal=2):
    """
    Lee el fichero estéreo 'ficEste' (16 bits) y genera el fichero monofónico 'ficMono'.
    
    Opciones de 'canal':
        0: Canal izquierdo (L)
        1: Canal derecho (R)
        2: Semisuma (L + R) / 2  [Opción por defecto]
        3: Semidiferencia (L - R) / 2
    """
    info = leer_cabecera_y_datos(ficEste)
    if info['num_channels'] != 2:
        raise ValueError(f"El archivo '{ficEste}' no es una señal estéreo.")
    if info['bits_per_sample'] != 16:
        raise ValueError("Resolución no soportada. Se requiere audio estéreo de 16 bits.")
        
    num_muestras = len(info['data']) // 2
    muestras = struct.unpack(f'<{num_muestras}h', info['data'])
    
    # Separar canales usando técnicas de rebanado (slicing)
    L = muestras[0::2]
    R = muestras[1::2]
    
    if canal == 0:
        mono_muestras = L
    elif canal == 1:
        mono_muestras = R
    elif canal == 2:
        mono_muestras = [(l + r) // 2 for l, r in zip(L, R)]
    elif canal == 3:
        mono_muestras = [(l - r) // 2 for l, r in zip(L, R)]
    else:
        raise ValueError("El parámetro canal debe ser un valor entero entre 0 y 3.")
        
    datos_mono = struct.pack(f'<{len(mono_muestras)}h', *mono_muestras)
    escribir_fichero_wave(ficMono, 1, info['sample_rate'], 16, datos_mono)


def mono2estereo(ficIzq, ficDer, ficEste):
    """
    Lee dos archivos monofónicos ('ficIzq' y 'ficDer') de 16 bits y genera
    un archivo estéreo combinado 'ficEste'.
    """
    info_izq = leer_cabecera_y_datos(ficIzq)
    info_der = leer_cabecera_y_datos(ficDer)
    
    if info_izq['num_channels'] != 1 or info_der['num_channels'] != 1:
        raise ValueError("Ambas señales de origen deben ser monofónicas.")
    if info_izq['bits_per_sample'] != 16 or info_der['bits_per_sample'] != 16:
        raise ValueError("Ambos ficheros deben poseer una codificación de 16 bits.")
    if info_izq['sample_rate'] != info_der['sample_rate']:
        raise ValueError("Las frecuencias de muestreo de los archivos no coinciden.")
        
    num_m_izq = len(info_izq['data']) // 2
    num_m_der = len(info_der['data']) // 2
    if num_m_izq != num_m_der:
        raise ValueError("La duración de ambos canales monoaurales debe ser idéntica.")
        
    izq = struct.unpack(f'<{num_m_izq}h', info_izq['data'])
    der = struct.unpack(f'<{num_m_der}h', info_der['data'])
    
    # Entrelazar los canales utilizando una comprensión de lista anidada (sin bucles)
    muestras_estereo = [muestra for par in zip(izq, der) for muestra in par]
    datos_estereo = struct.pack(f'<{len(muestras_estereo)}h', *muestras_estereo)
    
    escribir_fichero_wave(ficEste, 2, info_izq['sample_rate'], 16, datos_estereo)


def codEstereo(ficEste, ficCod):
    """
    Codifica un fichero estéreo de 16 bits en una señal monofónica de 32 bits.
    Los 16 bits más significativos almacenan la semisuma de canales, mientras que
    los 16 bits menos significativos contienen la semidiferencia.
    """
    info = leer_cabecera_y_datos(ficEste)
    if info['num_channels'] != 2:
        raise ValueError("La señal de entrada debe ser estéreo.")
    if info['bits_per_sample'] != 16:
        raise ValueError("La señal estéreo de entrada debe ser de 16 bits.")
        
    num_muestras = len(info['data']) // 2
    muestras = struct.unpack(f'<{num_muestras}h', info['data'])
    
    L = muestras[0::2]
    R = muestras[1::2]
    
    # Empaquetado binario mediante desplazamiento de bits y máscaras lógicas
    muestras_32 = [
        (((l + r) // 2) << 16) | (((l - r) // 2) & 0xFFFF)
        for l, r in zip(L, R)
    ]
    
    datos_32 = struct.pack(f'<{len(muestras_32)}i', *muestras_32)
    escribir_fichero_wave(ficCod, 1, info['sample_rate'], 32, datos_32)


def decEstereo(ficCod, ficEste):
    """
    Decodifica una señal monofónica de 32 bits y reconstruye los canales
    izquierdo y derecho independientes en un archivo estéreo de 16 bits.
    """
    info = leer_cabecera_y_datos(ficCod)
    if info['num_channels'] != 1:
        raise ValueError("El archivo codificado de entrada debe ser monofónico.")
    if info['bits_per_sample'] != 32:
        raise ValueError("El archivo codificado debe poseer un tamaño de muestra de 32 bits.")
        
    num_muestras = len(info['data']) // 4
    muestras_32 = struct.unpack(f'<{num_muestras}i', info['data'])
    
    # Función de conversión interna para procesar las muestras eficientemente mediante mapeo
    def _desentrelazar(val):
        s = val >> 16
        d_u = val & 0xFFFF
        d = d_u - 65536 if d_u >= 32768 else d_u
        l = max(-32768, min(32767, s + d))
        r = max(-32768, min(32767, s - d))
        return l, r
        
    pares = [_desentrelazar(v) for v in muestras_32]
    muestras_estereo = [m for par in pares for m in par]
    
    datos_estereo = struct.pack(f'<{len(muestras_estereo)}h', *muestras_estereo)
    escribir_fichero_wave(ficEste, 2, info['sample_rate'], 16, datos_estereo)