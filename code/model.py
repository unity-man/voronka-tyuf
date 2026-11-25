# Простая модель воронки из основного расчёта: равновесие, жёсткость водяной пружины, период,
# метацентрическая высота, высота ободка над водой по мере заполнения.
# Запуск: python model.py  (с аргументом full носик считается заполненным водой)

import math, sys
import numpy as np

RHO, G, NU, SIGMA = 1000.0, 9.81, 1e-6, 0.072
RI, T, LS, RTOP = 0.004, 0.004, 0.050, 0.050
TA = math.tan(math.radians(30)); TC = T / math.cos(math.radians(30))
RO = RI + T; HC = (RTOP - RI) / TA
zj = LS; zjo = zj + (RO - RI - TC) / TA; ztop = zj + HC

zz = np.linspace(0, ztop, 20001); dz = zz[1] - zz[0]
ri = np.where(zz < zj, RI, RI + (zz - zj) * TA)
ro = np.where(zz < zjo, RO, np.minimum(RI + (zz - zj) * TA + TC, RTOP + TC))
wall = math.pi * (ro ** 2 - ri ** 2)
M = 2500.0 * (wall * dz).sum()
zG = (wall * zz * dz).sum() / (wall * dz).sum()

outer = math.pi * ro ** 2
FULL = len(sys.argv) > 1 and sys.argv[1] == "full"
inner_dry = np.where(zz < zj, 0.0 if FULL else math.pi * ri ** 2, math.pi * ri ** 2)
disp = np.cumsum((outer - math.pi * ri ** 2 + inner_dry) * dz)
i = np.searchsorted(disp, M / RHO); h = zz[i]
Rwl = ro[i]; A = math.pi * Rwl ** 2
k = RHO * G * A
zB = (np.cumsum((outer - math.pi * ri ** 2 + inner_dry) * zz * dz)[i]) / disp[i]
m_add_max = RHO * (2 / 3) * math.pi * Rwl ** 3 / 2
T0 = 2 * math.pi * math.sqrt(M / k); T1 = 2 * math.pi * math.sqrt((M + m_add_max) / k)
I_out = math.pi * Rwl ** 4 / 4
GM = zB + I_out / (M / RHO) - zG
mu, s = 0.62, math.pi * RI ** 2
rate = mu * s * math.sqrt(2 * G * M / RHO) * A ** -1.5
omega = 2 * math.pi / 0.391
print(f"масса {M*1e3:.0f} г, центр масс {zG*1e3:.1f} мм над концом носика")
print(f"осадка в равновесии {h*1e3:.1f} мм, радиус ватерлинии {Rwl*1e3:.1f} мм, k = {k:.1f} Н/м")
print(f"период без присоединённой массы {T0:.3f} с, с наибольшей ({m_add_max*1e3:.0f} г) {T1:.3f} с")
print(f"присоединённая масса по периоду 0,391 с: {(k*(0.391/2/math.pi)**2 - M)*1e3:.0f} г")
print(f"метацентрическая высота GM = {GM*1e3:.0f} мм")
print(f"скорость оседания {rate*1e3:.2f} мм/с")
print(f"число Бонда: горло {RHO*G*RTOP**2/SIGMA:.0f}, носик {RHO*G*RI**2/SIGMA:.1f}")
print(f"ω²R/g = {omega**2*Rwl/G:.2f}, пограничный слой √(ν/ω) = {math.sqrt(NU/omega)*1e3:.2f} мм")
S_wet = 2 * math.pi * Rwl * (h - zj) / math.sin(math.radians(30)) / 2 + 2 * math.pi * RO * LS
loss = RHO * math.sqrt(NU * omega / 2) * S_wet * 0.391 / (M + 0.016)
print(f"вязкие потери за период (смоченная площадь {S_wet*1e4:.0f} см²): {loss*100:.0f} %")
print(f"подъём уровня в баке 180 x 180 мм: {M/RHO/0.18**2*1e3:.1f} мм")

outer_full = np.cumsum(outer * dz)
inner_full = np.cumsum(math.pi * ri ** 2 * dz)
inner_mom = np.cumsum(math.pi * ri ** 2 * zz * dz)
outer_mom = np.cumsum(outer * zz * dz)
print("заполнение: уровень внутри, мм | вода, г | осадка, мм | ободок над водой, мм | GM, мм | угол захлёста, °")
for zeta in np.arange(0.0, 0.125, 0.005):
    j = np.searchsorted(zz, zeta); mw = RHO * inner_full[j]
    i = np.searchsorted(outer_full, (M + mw) / RHO)
    if i >= len(zz) - 1:
        print(f"{zeta*1e3:6.0f}  тонет"); break
    hd = zz[i]; Vd = outer_full[i]
    zB = outer_mom[i] / Vd
    zGs = (M * zG + RHO * inner_mom[j]) / (M + mw)
    Iout = math.pi * ro[i] ** 4 / 4; Iin = math.pi * ri[j] ** 4 / 4 if zeta > 0 else 0.0
    GMf = zB + (Iout - Iin) / Vd - zGs
    fb = ztop - hd; phi = math.degrees(math.atan(fb / (RTOP + TC)))
    print(f"{zeta*1e3:6.0f} {mw*1e3:8.0f} {hd*1e3:9.1f} {fb*1e3:11.1f} {GMf*1e3:9.1f} {phi:8.1f}")
