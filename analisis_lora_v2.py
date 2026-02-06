import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Load the file
file_path = 'captura_aulario_1hora.csv'
print(f"Cargando datos desde: {file_path}")
# Read with error handling for encoding
try:
    df = pd.read_csv(file_path, header=None, encoding='utf-8')
except:
    df = pd.read_csv(file_path, header=None, encoding='utf-16')

df = df.dropna()
print(f"Datos cargados: {df.shape[0]} filas, {df.shape[1]} columnas")
# --- Reconstruct Waterfall Matrix ---
# Identify sweep blocks based on start frequency (Column 2)
freq_starts = df[2].unique()
freq_starts.sort()

# Get bin width from the first row
row0 = df[df[2] == freq_starts[0]].iloc[0]
bin_width_hz = row0[4]

bloques = []
print("Creando bloques de datos por frecuencia de inicio:")
for f_start in freq_starts:
    sub_df = df[df[2] == f_start].copy()
    
    # Power data starts at column 6
    potencias = sub_df.iloc[:, 6:].apply(pd.to_numeric, errors='coerce')
    
    # Calculate real frequencies for these columns
    n_cols = potencias.shape[1]
    freqs = f_start + np.arange(n_cols) * bin_width_hz
    
    # Assign frequencies as column names
    potencias.columns = freqs
    
    # Create a sweep ID based on order
    potencias['sweep_id'] = range(len(potencias))
    
    bloques.append(potencias)
print(f"Total bloques creados: {len(bloques)}")
# Merge blocks horizontally aligned by sweep_id
dfs_to_merge = [b.set_index('sweep_id') for b in bloques]
matriz_espectro = pd.concat(dfs_to_merge, axis=1).sort_index(axis=1)

# Filter range of interest (863 - 870 MHz)
FRECUENCIA_MIN_INTERES = 862.0
FRECUENCIA_MAX_INTERES = 871.0
cols_mhz = matriz_espectro.columns / 1e6
mask_freq = (cols_mhz >= FRECUENCIA_MIN_INTERES) & (cols_mhz <= FRECUENCIA_MAX_INTERES)
matriz_espectro_filt = matriz_espectro.loc[:, mask_freq]

freqs_mhz = matriz_espectro_filt.columns / 1e6
tiempo_sweeps = matriz_espectro_filt.index

# --- Calculate Noise Threshold ---
todos_los_valores = matriz_espectro_filt.values.flatten()
todos_los_valores = todos_los_valores[~np.isnan(todos_los_valores)]

# Histogram to find noise floor (mode)
hist_y, hist_x = np.histogram(todos_los_valores, bins=100)
pico_ruido = hist_x[np.argmax(hist_y)]
umbral_calculado = pico_ruido + 6.0
umbral_calculado = -55
print(f"Piso de ruido estimado: {pico_ruido:.2f} dB")
print(f"Umbral calculado (+6dB): {umbral_calculado:.2f} dB")

# --- Occupancy Analysis ---
canales_lora = [868.1, 868.3, 868.5, 869.525]
ANCHO_CANAL_LORA_HZ = 125000

print("\n--- Ocupación por Canal ---")
for canal in canales_lora:
    f_min_c = canal - (ANCHO_CANAL_LORA_HZ/1e6)/2
    f_max_c = canal + (ANCHO_CANAL_LORA_HZ/1e6)/2
    
    cols_canal = [c for c in matriz_espectro_filt.columns if (c/1e6 >= f_min_c) and (c/1e6 <= f_max_c)]
    
    if cols_canal:
        datos_canal = matriz_espectro_filt[cols_canal]
        # Integration logic: Average power in channel > Threshold
        potencia_inst_canal = datos_canal.mean(axis=1)
        muestras_ocupadas = np.sum(potencia_inst_canal > umbral_calculado)
        ocupacion_pct = (muestras_ocupadas / len(matriz_espectro_filt)) * 100
        print(f"Canal {canal} MHz: {ocupacion_pct:.2f}%")
    else:
        print(f"Canal {canal} MHz: Sin datos")

# --- Plotting ---
fig = plt.figure(figsize=(15, 10))
gs = fig.add_gridspec(2, 2, width_ratios=[3, 1], height_ratios=[1, 1])

# 1. Waterfall
ax1 = fig.add_subplot(gs[0, :])
im = ax1.imshow(matriz_espectro_filt, aspect='auto', 
                extent=[freqs_mhz.min(), freqs_mhz.max(), len(tiempo_sweeps), 0],
                cmap='inferno', vmin=pico_ruido-5, vmax=umbral_calculado+20)
ax1.set_title("Espectrograma (Waterfall)")
ax1.set_ylabel("Tiempo (Barridos)(1 hora total)")
ax1.set_xlabel("Frecuencia (MHz)")
plt.colorbar(im, ax=ax1, label='dBfs')

'''
# 2. Histogram
ax2 = fig.add_subplot(gs[0, 1])
ax2.hist(todos_los_valores, bins=100, color='gray', orientation='horizontal', density=True)
ax2.axhline(pico_ruido, color='blue', linestyle='--', label='Ruido')
ax2.axhline(umbral_calculado, color='red', linestyle='-', label='Umbral')
ax2.set_title("Distribución de Energía")
ax2.legend()
'''
# 3. Spectrum Summary
ax3 = fig.add_subplot(gs[1, :])
avg_spectrum = matriz_espectro_filt.mean(axis=0)
max_spectrum = matriz_espectro_filt.max(axis=0)
ax3.plot(freqs_mhz, max_spectrum, color='red', alpha=0.5, label='Máximo observado')
ax3.plot(freqs_mhz, avg_spectrum, color='navy', label='Promedio')
ax3.axhline(umbral_calculado, color='orange', linestyle='--', label='Umbral Ruido')
ax3.set_title("Espectro Agregado")
ax3.set_xlabel("Frecuencia (MHz)")
ax3.legend()

plt.tight_layout()
plt.savefig("analisis_lora_v2.png", dpi=600)
plt.show()