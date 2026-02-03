import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ==========================================
# CONFIGURACIÓN
# ==========================================
ARCHIVO_CSV = "captura_universidad.csv"
UMBRAL_OCUPACION_DB = -60.0  # Ajusta según tu ruido (aprox 10dB por encima del suelo azul)
ANCHO_CANAL_LORA = 0.125     # MHz

def analizar_espectro():
    print(f"--- INICIANDO PROCESADO INTELIGENTE DE {ARCHIVO_CSV} ---")
    
    # 1. CARGA DE DATOS ROBUSTA
    if not os.path.exists(ARCHIVO_CSV):
        print(f"ERROR: No encuentro el archivo '{ARCHIVO_CSV}'.")
        return

    try:
        # Probamos primero UTF-8 que suele ser el estándar tras pasar por herramientas modernas
        df = pd.read_csv(ARCHIVO_CSV, header=None, encoding='utf-8')
    except:
        print("UTF-8 falló. Probando UTF-16 (formato PowerShell)...")
        try:
            df = pd.read_csv(ARCHIVO_CSV, header=None, encoding='utf-16')
        except Exception as e:
            print(f"ERROR FATAL: {e}")
            return

    df = df.dropna()
    print(f"Filas cargadas: {len(df)}")

    # 2. PROCESADO POR BLOQUES DE FRECUENCIA (LA CLAVE DEL ARREGLO)
    # hackrf_sweep guarda trozos de 5 MHz mezclados. Hay que separarlos.
    # Agrupamos por la columna 2 (Frecuencia de Inicio en Hz)
    grupos_freq = df.groupby(2)
    
    resultados_bloques = []

    print("Reconstruyendo el espectro completo...")
    
    for start_freq_hz, bloque in grupos_freq:
        # Metadatos del bloque
        bin_width_hz = bloque.iloc[0, 4]
        
        # Datos de potencia (desde columna 6)
        potencias = bloque.iloc[:, 6:].apply(pd.to_numeric, errors='coerce')
        
        # Estadísticas de este trozo de espectro
        avg_bloque = potencias.mean(axis=0)
        max_bloque = potencias.max(axis=0)
        ocup_bloque = (potencias > UMBRAL_OCUPACION_DB).mean(axis=0) * 100
        
        # Generar eje X (Frecuencias) para este trozo
        num_puntos = len(avg_bloque)
        freqs_bloque = start_freq_hz + (np.arange(num_puntos) * bin_width_hz)
        
        # Guardamos en un DataFrame temporal
        temp_df = pd.DataFrame({
            'Frecuencia_Hz': freqs_bloque,
            'Avg_dB': avg_bloque.values,
            'Max_dB': max_bloque.values,
            'Ocupacion_Pct': ocup_bloque.values
        })
        resultados_bloques.append(temp_df)

    # 3. UNIFICACIÓN
    if not resultados_bloques:
        print("Error: No se pudieron extraer datos.")
        return

    # Unimos todos los trozos y ordenamos por frecuencia
    df_final = pd.concat(resultados_bloques).sort_values('Frecuencia_Hz').reset_index(drop=True)
    
    # Convertimos a MHz para facilitar la lectura
    frecuencias_mhz = df_final['Frecuencia_Hz'] / 1e6
    avg_potencia = df_final['Avg_dB']
    max_potencia = df_final['Max_dB']
    ocupacion_pct = df_final['Ocupacion_Pct']

    print(f"Rango reconstruido: {frecuencias_mhz.min():.2f} MHz - {frecuencias_mhz.max():.2f} MHz")

    # 4. INFORME DE TEXTO
    print("\n" + "="*45)
    print(f" INFORME VIABILIDAD (Umbral: {UMBRAL_OCUPACION_DB} dBm)")
    print("="*45)
    
    canales_lora = [868.1, 868.3, 868.5, 869.525, 869.8]
    
    for canal in canales_lora:
        # Buscamos el bin más cercano a la frecuencia deseada
        # (Usamos argmin para encontrar el índice del valor más próximo)
        idx = (np.abs(frecuencias_mhz - canal)).argmin()
        freq_real = frecuencias_mhz[idx]
        
        # Verificamos que esté "cerca" (dentro de 100 kHz)
        if abs(freq_real - canal) < 0.1:
            ocu = ocupacion_pct[idx]
            max_p = max_potencia[idx]
            
            estado = "✅ LIBRE"
            if ocu > 1.0: estado = "⚠️ TRÁFICO"
            if ocu > 10.0: estado = "⛔ SATURADO"
            
            print(f"Canal {canal:>7} MHz (Real {freq_real:.3f}) | Ocup: {ocu:>5.1f}% | Max: {max_p:>3.0f} dB | {estado}")
        else:
            print(f"Canal {canal} MHz: Fuera del rango capturado.")

    # 5. GRÁFICAS
    plt.figure(figsize=(12, 10))
    
    # --- SUBPLOT 1: ESPECTRO ---
    plt.subplot(2, 1, 1)
    plt.title("Espectro de Potencia (Rango Completo Reconstruido)")
    plt.fill_between(frecuencias_mhz, avg_potencia, -130, color='skyblue', alpha=0.4, label='Ruido')
    plt.plot(frecuencias_mhz, avg_potencia, color='blue', linewidth=1, label='Promedio')
    plt.plot(frecuencias_mhz, max_potencia, color='red', linewidth=0.8, alpha=0.6, label='Picos Máx.')
    plt.axhline(UMBRAL_OCUPACION_DB, color='orange', linestyle='--', label='Umbral')
    
    plt.ylabel("Potencia (dBm)")
    # Ajustamos límites visuales al rango interesante (ej: 863-871)
    plt.xlim(863, 871) 
    plt.ylim(min(avg_potencia)-5, max(max_potencia)+5)
    plt.grid(True, alpha=0.3)
    plt.legend()

    # --- SUBPLOT 2: OCUPACIÓN ---
    plt.subplot(2, 1, 2)
    plt.title("Duty Cycle (%)")
    plt.plot(frecuencias_mhz, ocupacion_pct, color='darkgreen')
    plt.fill_between(frecuencias_mhz, ocupacion_pct, 0, color='lightgreen', alpha=0.5)
    
    for c in canales_lora:
        plt.axvline(c, color='black', linestyle=':', alpha=0.3)
        plt.text(c, max(ocupacion_pct)*0.9, str(c), rotation=90, fontsize=8)

    plt.xlabel("Frecuencia (MHz)")
    plt.ylabel("Ocupación (%)")
    plt.xlim(863, 871) # Zoom en la zona de interés
    plt.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("analisis_final_tfg.png", dpi=300)
    print("\nGráfica guardada: analisis_final_tfg.png")
    plt.show()

if __name__ == "__main__":
    analizar_espectro()