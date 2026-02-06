import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# ==========================================
# CONFIGURACIÓN DEL ANÁLISIS
# ==========================================
file_path = 'captura_aulario_1hora.csv'  # Cambia al nombre de tu archivo
canales_lora = [868.1, 868.3, 868.5, 869.525]
ANCHO_CANAL_LORA_HZ = 125000
FRECUENCIA_MIN_INTERES = 862.0
FRECUENCIA_MAX_INTERES = 871.0
UMBRAL_DB = -55  # Umbral definido para detección de señal

def realizar_analisis_completo():
    print(f"--- Iniciando Procesamiento: {file_path} ---")
    
    # 1. CARGA DE DATOS
    if not os.path.exists(file_path):
        print(f"Error: El archivo '{file_path}' no existe en el directorio.")
        return

    try:
        df = pd.read_csv(file_path, header=None, encoding='utf-8')
    except:
        df = pd.read_csv(file_path, header=None, encoding='utf-16')
    df = df.dropna()

    # 2. RECONSTRUCCIÓN DE LA MATRIZ TIEMPO-FRECUENCIA
    print("Reconstruyendo matriz de datos...")
    freq_starts = df[2].unique()
    freq_starts.sort()
    bin_width_hz = df.iloc[0, 4]

    bloques = []
    for f_start in freq_starts:
        sub_df = df[df[2] == f_start].copy()
        potencias = sub_df.iloc[:, 6:].apply(pd.to_numeric, errors='coerce')
        freqs = f_start + np.arange(potencias.shape[1]) * bin_width_hz
        potencias.columns = freqs
        potencias['sweep_id'] = range(len(potencias))
        bloques.append(potencias)

    matriz_espectro = pd.concat([b.set_index('sweep_id') for b in bloques], axis=1).sort_index(axis=1)

    # Filtrado para el rango de visualización
    cols_mhz = matriz_espectro.columns / 1e6
    mask_freq = (cols_mhz >= FRECUENCIA_MIN_INTERES) & (cols_mhz <= FRECUENCIA_MAX_INTERES)
    matriz_filt = matriz_espectro.loc[:, mask_freq]
    freqs_mhz = matriz_filt.columns / 1e6
    tiempo_eje = matriz_filt.index

    # --- CÁLCULO DE OCUPACIÓN ---
    print("Calculando estadísticas de ocupación por canal...")
    ocupaciones = []
    labels_barras = [f"{c} MHz" for c in canales_lora]
    for canal in canales_lora:
        f_min = (canal * 1e6) - (ANCHO_CANAL_LORA_HZ / 2)
        f_max = (canal * 1e6) + (ANCHO_CANAL_LORA_HZ / 2)
        cols_canal = [c for c in matriz_espectro.columns if (c >= f_min) and (c <= f_max)]
        if cols_canal:
            datos_canal = matriz_espectro[cols_canal]
            # Ocupado si la potencia media del canal supera el umbral
            ocupado = datos_canal.mean(axis=1) > UMBRAL_DB
            pct = (ocupado.sum() / len(matriz_espectro)) * 100
            ocupaciones.append(pct)
        else:
            ocupaciones.append(0)

    # ==========================================
    # GRÁFICO 1: ANÁLISIS ESPECTRAL VERTICAL
    # ==========================================
    fig1 = plt.figure(figsize=(14, 12))
    gs = fig1.add_gridspec(2, 1, height_ratios=[1, 1])
    
    # Estimación de ruido para escala visual
    pico_ruido = np.percentile(matriz_filt.values.flatten()[~np.isnan(matriz_filt.values.flatten())], 50)

    # A) Waterfall
    ax1 = fig1.add_subplot(gs[0, 0])
    im = ax1.imshow(matriz_filt, aspect='auto', 
                    extent=[freqs_mhz.min(), freqs_mhz.max(), len(tiempo_eje), 0],
                    cmap='inferno', vmin=pico_ruido-5, vmax=UMBRAL_DB+20)
    ax1.set_title("Espectrograma (Waterfall)", fontsize=14, pad=15)
    ax1.set_ylabel("Tiempo (Índice de Barrido)", fontsize=12)
    plt.colorbar(im, ax=ax1, label='Potencia (dBfs)')
    for c in canales_lora:
        ax1.axvline(c, color='cyan', linestyle='--', alpha=0.6, linewidth=1)

    # B) Espectro Agregado
    ax2 = fig1.add_subplot(gs[1, 0])
    ax2.plot(freqs_mhz, matriz_filt.max(axis=0), color='red', alpha=0.4, label='Máximo (Max Hold)')
    ax2.plot(freqs_mhz, matriz_filt.mean(axis=0), color='navy', label='Promedio', linewidth=1.2)
    ax2.axhline(UMBRAL_DB, color='orange', linestyle='--', label=f'Umbral Detección ({UMBRAL_DB} dB)')
    for c in canales_lora:
        ax2.axvline(c, color='green', linestyle=':', alpha=0.7)
        ax2.text(c, ax2.get_ylim()[1], f"{c}", color='green', rotation=90, ha='right', fontsize=9)
    ax2.set_title("Estadísticas del Espectro", fontsize=14)
    ax2.set_xlabel("Frecuencia (MHz)", fontsize=12)
    ax2.set_ylabel("Potencia (dBfs)", fontsize=12)
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("analisis_lora_vertical.png", dpi=300)
    print("Imagen guardada: 'analisis_lora_vertical.png'")

    # ==========================================
    # GRÁFICO 2: HISTOGRAMA DE OCUPACIÓN
    # ==========================================
    plt.figure(figsize=(10, 6))
    # Color rojo si supera el límite del 1%
    colores = ['#e74c3c' if o > 1.0 else '#3498db' for o in ocupaciones]
    bars = plt.bar(labels_barras, ocupaciones, color=colores, edgecolor='black', alpha=0.8)
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.1, f'{yval:.2f}%', 
                 ha='center', va='bottom', fontweight='bold')
    
    plt.axhline(y=1.0, color='red', linestyle='-', label='Límite Duty Cycle (1%)')
    plt.title(f"Ocupación de Canales LoRa (Umbral: {UMBRAL_DB} dBfs)", fontsize=14)
    plt.ylabel("Ocupación Temporal (%)", fontsize=12)
    plt.ylim(0, max(max(ocupaciones) + 2, 3))
    plt.legend()
    plt.grid(axis='y', alpha=0.3)
    
    plt.tight_layout()
    plt.savefig("histograma_ocupacion_lora.png", dpi=300)
    print("Imagen guardada: 'histograma_ocupacion_lora.png'")

if __name__ == "__main__":
    realizar_analisis_completo()