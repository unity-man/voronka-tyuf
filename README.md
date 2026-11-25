Тонущая воронка

Материалы к задаче 6 областного турнира юных физиков 2026 года. Текст работы лежит в paper.pdf, здесь собраны программы и данные, по которым он написан.

Воронка в расчётах стеклянная: горло 100 мм, конус 60 градусов, носик 8 x 50 мм, стенка 4 мм, масса 188 г. Бак 180 x 180 мм, вода глубиной 150 мм.

Состав

- paper.pdf - работа.
- code - шесть скриптов, описание и команды запуска в начале каждого файла.
- data - таблицы из расчётов.
- media - видео расчётов.
- SHA256SUMS - контрольные суммы всех файлов.

Скрипты

- code/dualsphysics.py - трёхмерные расчёты: файлы расчёта, серия с разным наклоном, обработка, видео основного и проверочного расчёта.
- code/openfoam.py - осесимметричные расчёты: заполнение закреплённой воронки и колебания воронки с закрытым и открытым носиком, обработка, видео.
- code/render.py - трёхмерный кадр в Blender (рис. 4).
- code/model.py - простая модель: равновесие, период, устойчивость, высота ободка над водой при заполнении.
- code/figures.py - графики из папки data.
- code/paper/build.py - сборка paper.pdf.

Как получены видео

- media/funnel_3d.mp4: python code/dualsphysics.py video папка_основного_расчёта
- media/validation_cylinder.mp4: python code/dualsphysics.py check DualSPHysics_v5.4/examples/main/11_Floating
- media/openfoam_closed_spout.mp4 и media/openfoam_open_spout.mp4: python code/openfoam.py heave-video папка видео.mp4 заголовок
- media/openfoam_fill.mp4 и media/openfoam_fill_slow.mp4: python code/openfoam.py fill-video папка

Как получены таблицы

- data/motion_main.csv: python code/dualsphysics.py case run 0.002 10 0.04 2, затем run/run.sh и python code/dualsphysics.py post run (файл run/out/fi/FloatingInfo_mk61.csv).
- data/gauges_main_a.csv ... gauges_main_d.csv: там же, папка run/out/gauges.
- data/motion_angle_0.csv ... motion_angle_20.csv: python code/dualsphysics.py series.
- data/fill_sharp.csv, data/fill_round.csv: python code/openfoam.py fill папка 1.5 0.01 0 (и 0.0014 для скруглённой кромки), затем папка/Allrun и python code/openfoam.py fill-level папка таблица.csv.
- data/heave_openfoam.csv: python code/openfoam.py heave папка 1.08 0.02 0.015 0.001 8 0; высота воронки берётся из строк Centre of rotation в log.interFoam (функция funnel_height в openfoam.py), равновесие - среднее за 0,19-0,95 с.
- data/sinking_openfoam.csv: python code/openfoam.py heave папка 2.5 0.02 0.015 0.001 8 1, затем python code/openfoam.py levels папка таблица.csv.
- data/validation_cylinder.csv: пример 11_Floating из DualSPHysics (CaseFloatingSphereVal2D), файл floatinginfo/FloatingInfo_mk61.csv. data/reference_fekken2004.txt - опубликованное решение из того же примера.

В файлах motion_*.csv вывод программы FloatingInfo: время, скорость, положение центра масс, углы roll, pitch, yaw. Углы отсчитаны от начального положения, поэтому наклон оси равен -(начальный наклон + roll).

Программы

- DualSPHysics 5.4 (вместе с Project Chrono): https://dual.sphysics.org, код https://github.com/DualSPHysics/DualSPHysics. Версии программ из вывода: DualSPHysics5 v5.4.355 (08-04-2025), GenCase v5.4.354.01 (07-04-2025), MeasureTool v5.4.266.02 (07-05-2025).
- OpenFOAM v2412 (ESI-OpenCFD): https://www.openfoam.com, образ docker opencfd/openfoam-default:2412, https://hub.docker.com/r/opencfd/openfoam-default. Сборка _45e7c4a0-20241224.
- Blender 4.2.23 LTS: https://www.blender.org, архив blender-4.2.23-linux-x64.tar.xz.
- Python 3 с numpy 2.5.5, scipy 1.18.1, matplotlib 3.11.2, imageio-ffmpeg, reportlab.
- Расчёты шли на Linux с видеокартой NVIDIA GeForce GTX 1070.

Контрольные суммы

Контрольная сумма SHA-256 - это отпечаток файла из 64 символов. Если в файле изменится хотя бы один байт, отпечаток станет другим. По отпечатку можно убедиться, что файл тот же, что использовался в работе.

Файл SHA256SUMS содержит отпечатки всех файлов репозитория. Проверка в Linux или macOS из папки репозитория:

    shasum -a 256 -c SHA256SUMS

Для каждого файла должно быть написано OK. В Windows отпечаток одного файла показывает команда PowerShell:

    Get-FileHash paper.pdf -Algorithm SHA256

Отпечатки программ, которыми сделаны расчёты:

    1ba02114b1c025c370f2e269a07677c16c9bea8d990fcd75ac8378aff9d41b50  образ opencfd/openfoam-default:2412 (docker image inspect)
    0415b10e5e32af8b8b7ad2a703f9043dca67dfcf7626eb98f1c05a50856fde29  DualSPHysics_v5.4/bin/linux/DualSPHysics5.4_linux64
    a1b6414e0f716669363d1a80a05e133085c04995e15716e3c1f0406e0d023226  DualSPHysics_v5.4/bin/linux/GenCase_linux64
    62630430902484f4aede017108313673fe6414f40fb59b6ae7f14ac23219db00  DualSPHysics_v5.4/bin/linux/FloatingInfo_linux64, MeasureTool_linux64, PartVTK_linux64 (один и тот же файл)
    bea0eb3146be13eae6225409a117b215184f41b7f79e799f97cb3abb8f6dc404  blender-4.2.23-linux-x64.tar.xz

Свой образ OpenFOAM можно сравнить командой:

    docker image inspect opencfd/openfoam-default:2412 --format "{{index .RepoDigests 0}}"
