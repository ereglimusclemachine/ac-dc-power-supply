"""
AC-DC Güç Kaynağı - Tasarım Hesapları
=====================================
230 V / 50 Hz şebeke -> 12 V trafo -> köprü doğrultucu (4x 1N4001)
-> filtre kondansatörü -> 7805 regülatör -> 5 V çıkış

Bu dosya, LTspice simülasyonundan ÖNCE elle yapılan hesapları içerir.
Simülasyon sonuçları bu değerlerle karşılaştırılacaktır.

Çalıştırmak için:  python tasarim_hesaplari.py
"""

import math
import os

import matplotlib.pyplot as plt
import numpy as np

# ---------------------------------------------------------------
# 1) Tasarım hedefleri (giriş parametreleri)
# ---------------------------------------------------------------
V_TRAFO_RMS = 12.0      # Trafo sekonder gerilimi (V rms)
F_SEBEKE = 50.0         # Şebeke frekansı (Hz)
V_DIYOT = 0.9           # 1N4001 iletim gerilimi (~0.7-1.0 V, akıma bağlı)
I_YUK = 0.100           # Yük akımı (A)  -> 100 mA
V_CIKIS = 5.0           # Regülatör çıkışı (V)
V_DROPOUT = 2.0         # 7805 için gereken minimum (Vin - Vout)
RIPPLE_HEDEF = 2.0      # İzin verilen maksimum dalgalanma (V tepe-tepe)

STANDART_KONDANSATORLER_uF = [100, 220, 470, 1000, 2200, 4700]

# ---------------------------------------------------------------
# 2) Hesaplar
# ---------------------------------------------------------------
v_tepe_trafo = V_TRAFO_RMS * math.sqrt(2)          # Trafo çıkışının tepe değeri
v_tepe_dc = v_tepe_trafo - 2 * V_DIYOT              # Köprüde her an 2 diyot iletimde
f_ripple = 2 * F_SEBEKE                             # Tam dalga doğrultma -> 100 Hz

# Dalgalanma formülü:  dV = I / (f_ripple * C)   ->   C = I / (f_ripple * dV)
c_min = I_YUK / (f_ripple * RIPPLE_HEDEF)
c_secilen_uF = next(c for c in STANDART_KONDANSATORLER_uF if c * 1e-6 >= c_min)
c_secilen = c_secilen_uF * 1e-6
ripple_gercek = I_YUK / (f_ripple * c_secilen)

v_min_kondansator = v_tepe_dc - ripple_gercek       # Kondansatördeki en düşük gerilim
v_min_gereken = V_CIKIS + V_DROPOUT                 # 7805'in çalışması için gereken
v_ort_kondansator = v_tepe_dc - ripple_gercek / 2
p_regulator = (v_ort_kondansator - V_CIKIS) * I_YUK  # Regülatörde ısıya dönüşen güç
verim = (V_CIKIS * I_YUK) / (v_ort_kondansator * I_YUK) * 100

diyot_ters_gerilim = v_tepe_trafo                   # Köprüde her diyotun gördüğü PIV

print("=" * 55)
print(" AC-DC GÜÇ KAYNAĞI TASARIM HESAPLARI")
print("=" * 55)
print(f"Trafo tepe gerilimi        : {v_tepe_trafo:6.2f} V")
print(f"Doğrultucu çıkışı (tepe)   : {v_tepe_dc:6.2f} V")
print(f"Dalgalanma frekansı        : {f_ripple:6.0f} Hz")
print(f"Gereken min. kondansatör   : {c_min*1e6:6.0f} uF")
print(f"Seçilen standart değer     : {c_secilen_uF:6d} uF")
print(f"Beklenen dalgalanma (p-p)  : {ripple_gercek:6.2f} V")
print(f"Kondansatör min. gerilimi  : {v_min_kondansator:6.2f} V")
print(f"7805 için gereken minimum  : {v_min_gereken:6.2f} V")
durum = "UYGUN" if v_min_kondansator >= v_min_gereken else "YETERSİZ!"
print(f"  -> Regülasyon durumu     : {durum}")
print(f"7805'te harcanan güç       : {p_regulator:6.2f} W")
print(f"Yaklaşık verim (reg. katı) : {verim:6.1f} %")
print(f"Diyot ters gerilimi (PIV)  : {diyot_ters_gerilim:6.2f} V  (1N4001: 50 V -> uygun)")
print("=" * 55)

# ---------------------------------------------------------------
# 3) Basit zaman-domeni modeli ve grafik
# ---------------------------------------------------------------
dt = 1e-5
t = np.arange(0, 0.06, dt)                           # 3 periyot (60 ms)
v_dogrultulmus = np.abs(v_tepe_trafo * np.sin(2 * np.pi * F_SEBEKE * t)) - 2 * V_DIYOT
v_dogrultulmus = np.clip(v_dogrultulmus, 0, None)

v_kond = np.zeros_like(t)
for i in range(1, len(t)):
    desarj = v_kond[i - 1] - (I_YUK / c_secilen) * dt   # Sabit akımla deşarj
    v_kond[i] = max(v_dogrultulmus[i], desarj)            # Diyot iletimdeyse şarj olur

v_cikis = np.where(v_kond >= v_min_gereken, V_CIKIS, np.clip(v_kond - V_DROPOUT, 0, None))

fig, ax = plt.subplots(figsize=(10, 5))
ax.plot(t * 1000, v_dogrultulmus, "--", color="gray", label="Doğrultulmuş (filtresiz)")
ax.plot(t * 1000, v_kond, color="tab:blue", label=f"Kondansatör çıkışı ({c_secilen_uF} uF)")
ax.plot(t * 1000, v_cikis, color="tab:green", linewidth=2, label="7805 çıkışı")
ax.axhline(v_min_gereken, color="tab:red", linestyle=":", label=f"7805 min. giriş ({v_min_gereken:.0f} V)")
ax.set_xlabel("Zaman (ms)")
ax.set_ylabel("Gerilim (V)")
ax.set_title(f"Teorik dalga şekilleri - Yük: {I_YUK*1000:.0f} mA")
ax.grid(alpha=0.3)
ax.legend(loc="lower right")
fig.tight_layout()

klasor = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "gorseller")
os.makedirs(klasor, exist_ok=True)
yol = os.path.join(klasor, "teorik_dalga_sekilleri.png")
fig.savefig(yol, dpi=150)
print(f"Grafik kaydedildi: {os.path.normpath(yol)}")
