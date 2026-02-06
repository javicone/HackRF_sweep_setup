import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os

# --- CONFIGURACIÓN ---
file_path = 'captura_aulario_1hora.csv'
canales_lora = [868.1, 868.3, 868.5, 869.525]
ANCHO_CANAL_LORA_HZ = 125000
FRECUENCIA_MIN_INTERES = 862.0
FRECUENCIA_MAX_INTERES = 871.0

print(f"Cargando datos desde: {file_path}")

# 1. CARGA DE DATOS
try:
    df = pd.read_csv(file_path, header=None, encoding='utf-8')
except:
    df = pd.read_csv(file_path, header=None, encoding='utf-16')

df = df.dropna()

# 2. RECONSTRUCCIÓN DE MATRIZ
freq_starts = df[2].unique()
freq_starts.sort()
row0 = df[df[2] == freq_starts[0]].iloc[0]
bin_width_hz = row0[4]

bloques = []
for f_start in freq_starts:
    sub_df = df[df[2] == f_start].copy()
    potencias = sub_df.iloc[:, 6:].apply(pd.to_numeric, errors='coerce')
    n_cols = potencias.shape[1]
    freqs = f_start + np.arange(n_cols) * bin_width_hz
    potencias.columns = freqs
    potencias['sweep_id'] = range(len(potencias))
    bloques.append(potencias)

dfs_to_merge = [b.set_index('sweep_id') for b in bloques]
matriz_espectro = pd.concat(dfs_to_merge, axis=1).sort_index(axis=1)

# Filtro de rango
cols_mhz = matriz_espectro.columns / 1e6
mask_freq = (cols_mhz >= FRECUENCIA_MIN_INTERES) & (cols_mhz <= FRECUENCIA_MAX_INTERES)
matriz_espectro_filt = matriz_espectro.loc[:, mask_freq]

freqs_mhz = matriz_espectro_filt.columns / 1e6
tiempo_sweeps = matriz_espectro_filt.index

# 3. UMBRAL Y OCUPACIÓN
todos_los_valores = matriz_espectro_filt.values.flatten()
todos_los_valores = todos_los_valores[~np.isnan(todos_los_valores)]
hist_y, hist_x = np.histogram(todos_los_valores, bins=100)
pico_ruido = hist_x[np.argmax(hist_y)]
umbral_calculado = -55 # Tu valor manual

# --- GRÁFICOS ---
fig = plt.figure(figsize=(14, 12))
# Definimos 2 filas y 1 sola columna
gs = fig.add_gridspec(2, 1, height_ratios=[1, 1])

# SUBPLOT 1: WATERFALL
ax1 = fig.add_subplot(gs[0, 0])
im = ax1.imshow(matriz_espectro_filt, aspect='auto', 
                extent=[freqs_mhz.min(), freqs_mhz.max(), len(tiempo_sweeps), 0],
                cmap='inferno', vmin=pico_ruido-5, vmax=umbral_calculado+20)
ax1.set_title("Espectrograma (Waterfall) - 1 Hora de Captura", fontsize=14, pad=15)
ax1.set_ylabel("Tiempo (Barridos Temporales)", fontsize=12)
plt.colorbar(im, ax=ax1, label='Potencia (dBfs)')

# Marcado de canales en Waterfall
for canal in canales_lora:
    ax1.axvline(canal, color='cyan', linestyle='--', alpha=0.6, linewidth=1)
    ax1.text(canal, len(tiempo_sweeps)*0.05, f" {canal}", color='cyan', rotation=90, verticalalignment='top', fontsize=9)

# SUBPLOT 2: ESPECTRO AGREGADO
ax3 = fig.add_subplot(gs[1, 0])
avg_spectrum = matriz_espectro_filt.mean(axis=0)
max_spectrum = matriz_espectro_filt.max(axis=0)

ax3.plot(freqs_mhz, max_spectrum, color='red', alpha=0.5, label='Máximo observado (Max Hold)')
ax3.plot(freqs_mhz, avg_spectrum, color='navy', label='Nivel Promedio', linewidth=1.5)
ax3.axhline(umbral_calculado, color='orange', linestyle='--', label=f'Umbral de Ruido ({umbral_calculado} dBfs)')

# Marcado de canales en Espectro Agregado
for canal in canales_lora:
    ax3.axvline(canal, color='green', linestyle=':', alpha=0.7, linewidth=1.5)
    # Colocamos el texto en la parte superior del gráfico
    ax3.text(canal, max(max_spectrum)+2, f"{canal} MHz", color='green', rotation=90, ha='right', fontsize=9)

ax3.set_title("Estadísticas del Espectro (Promedio vs Máximos)", fontsize=14)
ax3.set_xlabel("Frecuencia (MHz)", fontsize=12)
ax3.set_ylabel("Potencia (dBfs)", fontsize=12)
ax3.set_xlim(FRECUENCIA_MIN_INTERES, FRECUENCIA_MAX_INTERES)
ax3.grid(True, which='both', linestyle='--', alpha=0.3)
ax3.legend(loc='upper right')

plt.tight_layout()
plt.savefig("analisis_lora_banda.png", dpi=600)
print("Análisis finalizado. Gráfica guardada como 'analisis_lora_banda.png'")
plt.show()