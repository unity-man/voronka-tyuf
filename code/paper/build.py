# Сборка paper.pdf: Times New Roman 14 пт, одинарный интервал, поля 6 мм.
# Нужен reportlab, картинки в img, числа в results.json.
# Запуск: python build.py paper.pdf

import json, os, re, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER, TA_LEFT
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
from reportlab.platypus import BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from reportlab.platypus.tableofcontents import TableOfContents

HERE = os.path.dirname(os.path.abspath(__file__)); IMG = os.path.join(HERE, "img")
F = "/System/Library/Fonts/Supplemental/"
for n, f in (("TNR", "Times New Roman.ttf"), ("TNR-B", "Times New Roman Bold.ttf"), ("TNR-I", "Times New Roman Italic.ttf"), ("TNR-BI", "Times New Roman Bold Italic.ttf")):
    pdfmetrics.registerFont(TTFont(n, F + f))
for b, i, n in ((0, 0, "TNR"), (1, 0, "TNR-B"), (0, 1, "TNR-I"), (1, 1, "TNR-BI")):
    addMapping("TNR", b, i, n)

FS, LD, M = 14, 16.1, 6 * mm
ACC = colors.HexColor("#1f4e79")
body = ParagraphStyle("body", fontName="TNR", fontSize=FS, leading=LD, alignment=TA_JUSTIFY, firstLineIndent=7 * mm)
bodyni = ParagraphStyle("bodyni", parent=body, firstLineIndent=0)
item = ParagraphStyle("item", parent=body, firstLineIndent=-5 * mm, leftIndent=5 * mm)
h1 = ParagraphStyle("h1", fontName="TNR-B", fontSize=FS, leading=LD, spaceBefore=3, spaceAfter=1, textColor=ACC, keepWithNext=1)
h2 = ParagraphStyle("h2", fontName="TNR-BI", fontSize=FS, leading=LD, spaceBefore=1, keepWithNext=1)
title = ParagraphStyle("title", fontName="TNR-B", fontSize=18.5, leading=22, alignment=TA_CENTER, textColor=ACC)
sub = ParagraphStyle("sub", fontName="TNR-I", fontSize=15, leading=18, alignment=TA_CENTER)
cap = ParagraphStyle("cap", fontName="TNR-I", fontSize=FS, leading=LD, alignment=TA_CENTER)
formula = ParagraphStyle("formula", fontName="TNR", fontSize=FS, leading=LD + 1, alignment=TA_CENTER)
cell = ParagraphStyle("cell", fontName="TNR", fontSize=FS, leading=LD, alignment=TA_CENTER)
ref = ParagraphStyle("ref", fontName="TNR", fontSize=FS, leading=LD, alignment=TA_LEFT, firstLineIndent=-6 * mm, leftIndent=6 * mm, splitLongWords=1)

class HPara(Paragraph):
    def draw(self):
        super().draw()
        c = self.canv; c.saveState(); c.setStrokeColor(ACC); c.setLineWidth(2.4)
        c.line(-2.6 * mm, -2, -2.6 * mm, self.height - 1); c.restoreState()

class TOC(TableOfContents):
    def wrap(self, aw, ah):
        w, h = super().wrap(aw, ah); self._h = h; return w, h
    def drawOn(self, canv, x, y, _sW=0):
        super().drawOn(canv, x, y, _sW)
        canv.saveState(); canv.setStrokeColor(ACC); canv.setLineWidth(1.2)
        canv.line(x - 2.6 * mm, y, x - 2.6 * mm, y + getattr(self, "_h", 0)); canv.restoreState()

class Doc(BaseDocTemplate):
    def __init__(self, fn):
        super().__init__(fn, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=M,
                         title="Задача № 6. Тонущая воронка", author="ОТЮФ 2026")
        fr = Frame(M, M, A4[0] - 2 * M, A4[1] - 2 * M, id="f", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        self.addPageTemplates([PageTemplate("p", [fr], onPage=self.page_no)])
    def beforeDocument(self):
        self.n_h = 0
    def page_no(self, c, d):
        if d.page == 1:
            return
        c.saveState()
        w = 9 * mm; x = A4[0] - M - w; y = 0.6 * mm
        c.setFillColor(ACC); c.roundRect(x, y, w, 5.0 * mm, 1.2 * mm, stroke=0, fill=1)
        c.setFillColor(colors.white); c.setFont("TNR-B", 13); c.drawCentredString(x + w / 2, y + 1.3 * mm, str(d.page))
        c.restoreState()
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("h1", "h2"):
            lvl = 0 if f.style.name == "h1" else 1
            self.n_h += 1; key = f"h{self.n_h}"
            self.canv.bookmarkPage(key); self.canv.addOutlineEntry(f.getPlainText(), key, level=lvl)
            self.notify("TOCEntry", (lvl, f.getPlainText(), self.page, key))

def P(t, s=body):
    t = re.sub(r"<sub>(.*?)</sub>", r'<sub size="10" rise="3">\1</sub>', t)
    t = re.sub(r"<super>(.*?)</super>", r'<super size="10" rise="5">\1</super>', t)
    return (HPara if s is h1 else Paragraph)(t, s)

def figs(pairs, height=46 * mm, width=95 * mm):
    ri, rc = [], []
    for fn, caption in pairs:
        iw, ih = ImageReader(os.path.join(IMG, fn)).getSize()
        h = height; w = h * iw / ih
        if w > width: w = width; h = w * ih / iw
        ri.append(Image(os.path.join(IMG, fn), width=w, height=h)); rc.append(P(caption, cap))
    t = Table([ri, rc], colWidths=[(A4[0] - 2 * M) / len(pairs)] * len(pairs))
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                           ("LINEAFTER", (0, 0), (0, -1), 0.6, colors.HexColor("#9fb6cc"))]))
    return KeepTogether([t])

toc = TOC(); toc.dotsMinLevel = 0
R = json.load(open(os.path.join(HERE, "results.json")))
toc.levelStyles = [ParagraphStyle("t0", fontName="TNR-B", fontSize=FS, leading=LD, leftIndent=0, firstLineIndent=0),
                   ParagraphStyle("t1", fontName="TNR", fontSize=FS, leading=LD, leftIndent=7 * mm, firstLineIndent=0)]
left = ParagraphStyle("left", fontName="TNR", fontSize=FS, leading=LD + 4, alignment=TA_LEFT)
center = ParagraphStyle("center", fontName="TNR", fontSize=FS, leading=LD + 2, alignment=TA_CENTER)
tcell = ParagraphStyle("tcell", fontName="TNR", fontSize=FS, leading=LD, alignment=TA_LEFT)
tcellb = ParagraphStyle("tcellb", fontName="TNR-B", fontSize=FS, leading=LD, alignment=TA_LEFT)
W = A4[0] - 2 * M
def grid(rows, cw, head=True):
    t = Table(rows, colWidths=cw)
    st = [("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#9fb6cc")), ("TOPPADDING", (0, 0), (-1, -1), 0),
          ("BOTTOMPADDING", (0, 0), (-1, -1), 1), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if head: st.append(("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")))
    t.setStyle(TableStyle(st)); return t

def figrow(pairs, height):
    ims, ws = [], []
    for fn, _ in pairs:
        iw, ih = ImageReader(os.path.join(IMG, fn)).getSize(); ws.append(height * iw / ih)
        ims.append(Image(os.path.join(IMG, fn), width=ws[-1], height=height))
    k = W / sum(ws)
    if k < 1:
        ims = [Image(os.path.join(IMG, fn), width=w * k, height=height * k) for (fn, _), w in zip(pairs, ws)]
    cw = [w * min(k, 1) + (W - sum(ws) * min(k, 1)) / len(ws) for w in ws]
    t = Table([ims, [P(c, cap) for _, c in pairs]], colWidths=cw)
    t.setStyle(TableStyle([("ALIGN", (0, 0), (-1, -1), "CENTER"), ("VALIGN", (0, 0), (-1, 0), "BOTTOM"),
                           ("VALIGN", (0, 1), (-1, 1), "TOP"),
                           ("LEFTPADDING", (0, 0), (-1, -1), 1), ("RIGHTPADDING", (0, 0), (-1, -1), 1),
                           ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                           ("LINEAFTER", (0, 0), (-2, -1), 0.6, colors.HexColor("#9fb6cc"))]))
    return KeepTogether([t])

S = [P("Учреждение образования", center),
     P("«Средняя школа № 12 г. Мозыря»", center), Spacer(1, 30 * mm),
     P("Задача № 6", ParagraphStyle("tn", parent=title, fontSize=16, leading=20)),
     P("«Тонущая воронка»", ParagraphStyle("tt2", parent=title, fontSize=24, leading=30)), Spacer(1, 3 * mm),
     P("Исследовательская работа к областному турниру юных физиков, 2026 год", sub), Spacer(1, 20 * mm),
     P("Автор: ______________________________________________________", left), Spacer(1, 2 * mm),
     P("Руководитель: ________________________________________________", left), Spacer(1, 14 * mm),
     P("Содержание", ParagraphStyle("ct", parent=h2, alignment=TA_CENTER, textColor=ACC, fontName="TNR-B")), toc,
     Spacer(1, 10 * mm), P("Мозырь, 2026", center), PageBreak()]

S += [P("1. Постановка задачи", h1),
      P("Тяжёлую воронку с длинным носиком отпускают в воду носиком вниз. По условию она делает несколько затухающих "
        "вертикальных колебаний и постепенно погружается. Нужно исследовать её движение и устойчивость и найти условия, "
        "при которых она опрокидывается."),
      P("Воронка похожа на судно с пробоиной в днище. Когда в воду входит конус, выталкивающая сила быстро растёт, и около "
        "секунды воронка качается около равновесия. Одновременно вода затекает через носик, воронка оседает, и в конце "
        "вода переливается через ободок. Мы построили простую модель и проверили её численным экспериментом в двух независимых "
        "открытых программах. Сжимаемостью воды, вязкостью для корпуса (Re ≈ 2,5·10<super>4</super>), реактивной силой струи "
        "(0,04 Н при весе 1,8 Н) и натяжением для корпуса (число Бонда около 340) пренебрегаем; в носике число Бонда около 2, "
        "и там натяжение учтено.")]

found = [f"Воронка делает затухающие вертикальные колебания с периодом 0,391 ± 0,007 с по DualSPHysics и {R['of_T']} с по "
         "OpenFOAM. Модель «водяной пружины» даёт от 0,34 до 0,42 с.",
         "Декремент 0,42: за период теряется 57 % энергии, в основном с волнами.",
         "Малый начальный наклон раскачивается примерно до 20° и затем гаснет. Период качания наклона около 0,87 с, близок "
         "к удвоенному периоду вертикальных колебаний, это параметрический резонанс.",
         "Опрокидывание начинается с захлёста, когда наклон больше arctg(h/R), где h обозначает высоту ободка над водой, "
         "а R его радиус. При начальном наклоне 20° воронка зачерпнула краем 11 см<super>3</super> воды.",
         "С открытым носиком вода натекает в конус со скоростью 26 см<super>3</super>/с, и воронка, продолжая колебаться, "
         "оседает на 3,4 мм/с, как предсказывает модель. Вихрь на острой входной кромке носика уменьшает расход примерно на 25 %."]
S += [P("2. Основные результаты", h1)] + [P(f"{i}) {t}", item) for i, t in enumerate(found, 1)]

S += [P("3. Применимость и объём работы", h1),
      P("Выводы относятся к воронкам с открытым горлом, у которых стенки тяжелее воды, а течение в носике инерционное "
        "(Re в носике около 6·10<super>3</super>). Расчёты сделаны для стеклянной воронки с горлом Ø100 мм, углом конуса 60°, "
        "носиком Ø8 × 50 мм, стенкой 4 мм и массой 188 г в баке 180 × 180 мм с водой глубиной 150 мм. Основной трёхмерный "
        "расчёт содержит 673 тыс. частиц и 10 с движения. Реальный опыт не проводился: чтобы измерить наклон, "
        "нужна синхронная съёмка с нескольких камер и определение положения воронки по шести координатам (6DoF). Поэтому "
        "основным методом стал численный эксперимент, проверенный на эталонной задаче и вторым независимым решателем. Для "
        "проверки вертикальных колебаний опытом достаточно съёмки 240 кадров/с и Tracker [5].", bodyni)]
S += [figs([("fig1_scheme.png", "Рис. 1. Обозначения: z, ζ, «сухой» слой"),
            ("f_valid.png", "Рис. 2. Падение цилиндра: расчёт и эталон")], height=34 * mm)]

S += [P("4. Основная часть", h1),
      P("4.1. Модель", h2),
      P("Воду вытесняют стенки и «сухой» слой между уровнем снаружи z и уровнем внутри ζ (рис. 1), поэтому выталкивающая "
        "сила F = ρg[V(z) − V(ζ) + V<sub>ст</sub>]. В равновесии F = Mg. При сдвиге воронки на Δz погружённый объём "
        "меняется на A<sub>wl</sub>Δz, где A<sub>wl</sub> обозначает площадь ватерлинии. Вода действует как пружина "
        "жёсткостью k = ρgA<sub>wl</sub>, и период колебаний", body),
      P("T = 2π·√((M + m<sub>в</sub> + m<sub>пр</sub>) / (ρgA<sub>wl</sub>)),", formula),
      P("где m<sub>в</sub> обозначает массу воды внутри воронки, m<sub>пр</sub> присоединённую массу. У нашей воронки радиус "
        "ватерлинии 46 мм и k ≈ 66 Н/м. Без присоединённой массы T = 0,34 с; если взять её равной половине массы воды в полушарии "
        "радиусом ватерлинии, T = 0,42 с.", bodyni),
      P("Вода входит через носик сечением s по формуле Торричелли Q = μs√(2g(z − ζ)), где μ около 0,6 для острой кромки. "
        "Отсюда скорость оседания dz/dt ≈ μs√(2gM/ρ)·A<sub>wl</sub><super>−3/2</super>: чем шире ватерлиния, тем медленнее "
        "воронка тонет. Для нашей воронки в начале это 3,4 мм/с."),
      P("Воронка возвращается к вертикали, если метацентрическая высота положительна:", body),
      P("GM = z<sub>B</sub> + (I<sub>нар</sub> − I<sub>вн</sub>)/V − z<sub>G</sub> &gt; 0,     I = πR<super>4</super>/4.", formula),
      P("Момент I<sub>нар</sub> считается по внешней ватерлинии, I<sub>вн</sub> по поверхности воды внутри. У пустой воронки "
        "GM ≈ 18 мм, при заполнении конуса он растёт до 27 мм: вода лежит низко и опускает общий центр масс. "
        "Зато воронка садится глубже, и высота ободка над водой h уменьшается с 14,5 мм до нуля. Ободок уходит под воду при наклоне φ* = arctg(h/R): у пустой воронки при 15°, дальше при всё "
        "меньших углах. Тогда вода заливается с одной стороны, и воронка заваливается.", bodyni),
      P("При колебаниях радиус ватерлинии меняется от 20 до 54 мм, и момент I, пропорциональный R<super>4</super>, меняется "
        "в десятки раз дважды за период наклона. Уравнение наклона принимает вид θ'' + ω<sub>θ</sub><super>2</super>(1 + "
        "ε·cos ω<sub>z</sub>t)θ = 0, и при ω<sub>z</sub> ≈ 2ω<sub>θ</sub> малый наклон растёт (параметрический резонанс [1])."),
      P("4.2. Численный эксперимент", h2),
      P("Трёхмерный расчёт выполнен в DualSPHysics [2], методе частиц на видеокарте, вместе с движком Project Chrono [3], "
        "который считает движение воронки как твёрдого тела. Вода здесь слабосжимаемая: скорость звука 12 м/с, число Маха "
        "0,09, шаг по времени около 5·10<super>−5</super> с, размер частицы 2 мм (в серии с наклоном 2,5 мм). В носик "
        "диаметром 8 мм помещается четыре частицы, вода через него почти не проходит, и конус остаётся сухим. Записывались "
        "положение и углы воронки и уровень воды в четырёх точках бака."),
      P("В OpenFOAM [4] вода и воздух считаются методом объёма жидкости с натяжением 0,072 Н/м и краевым углом 30°. "
        "Свободные колебания посчитаны в осесимметричной постановке для той же воронки с сухим конусом: сетка 1 мм "
        "деформируется вслед за воронкой, которая движется по вертикали и отпускается на 15 мм выше равновесия. Второй такой "
        "расчёт с открытым носиком показывает заполнение и оседание. Влияние кромки носика посчитано на малой закреплённой "
        "воронке с сеткой 0,5 мм."),
      P("4.3. Проверка расчёта", h2),
      P("В эталонной задаче тяжёлый цилиндр с плотностью 1,2 от плотности воды падает в воду. Траектория из DualSPHysics "
        "отличается от опубликованного решения в среднем на 0,1 радиуса (рис. 2). При частицах 2 и 2,5 мм "
        "первые амплитуды воронки различаются не больше чем на 5 % при одинаковом периоде (рис. 3), значит, численная "
        "вязкость затухание почти не меняет. Уровень в баке поднялся на 5,8 мм: вытеснено 188 см<super>3</super> при массе "
        "воронки 188 г. Частицы воды держатся примерно в одной частице от стенки, поэтому в DualSPHysics воронка сидит "
        "на 8 мм выше, чем по модели. Независимая проверка выполнена в OpenFOAM (раздел 4.4).")]

S += [P("4.4. Вертикальные колебания", h2),
      P("Воронка входит в воду, проскакивает равновесие на 35 мм и колеблется около него (рис. 3). Верхние отклонения "
        "центра масс 44,8; 28,8; 17,0; 10,0 мм и дальше до 1,1 мм на десятом колебании. Период держится в пределах 2 %: "
        "T = 0,391 ± 0,007 с, внутри интервала модели. Каждое отклонение примерно в 1,5 раза меньше предыдущего, декремент "
        "δ = 0,42, добротность около 7,5. Энергия пропорциональна квадрату амплитуды, и за период теряется "
        f"1 − e<super>−2δ</super> ≈ 57 % энергии. {R['of_text']}"),
      figs([("f_heave.png", "Рис. 3. Высота центра масс воронки"),
            ("render_t144.png", "Рис. 4. 3D-расчёт, t = 1,44 с, наклон 21°")], height=36 * mm)]

S += [P("4.5. Наклон и опрокидывание", h2),
      P("Без начального наклона воронка остаётся вертикальной (меньше 1°), а 2° раскачиваются до 21° "
        "на 1,44 с (рис. 4, 5). Период наклона около 0,87 с, близок к удвоенному "
        "периоду вертикальных колебаний, как и требует параметрический резонанс. Чем "
        "сильнее раскачка, тем быстрее гаснут вертикальные колебания: энергия переходит в наклон (табл. 1). Когда вертикальные колебания затухают, раскачка прекращается и наклон уменьшается до нескольких градусов."),
      P("При начальном наклоне 20° удар о воду наклоняет воронку до 31°. Ободок в этом расчёте стоит на 23 мм над водой, "
        "захлёст начинается при arctg(23/55) ≈ 23°, и воронка зачерпывает краем около 11 см<super>3</super> воды. В остальных "
        "расчётах наклон не превышал 21°, вода внутрь не попала, и ни одна воронка не перевернулась. У реальной воронки "
        "ободок ниже, 14,5 мм, захлёст начинается с 15°, и раскачки до 20° для него достаточно."),
      P("Таблица 1. Серия с разным начальным наклоном", cap)]
ang = [("0°", "0,0°", "0,6°", "0,64", "нет"), ("2°", "3,7°", "21,2°", "0,64", "нет"), ("5°", "9,6°", "19,2°", "0,53", "нет"),
       ("10°", "17,2°", "19,1°", "0,48", "нет"), ("20°", "31,2°", "23,9°", "0,44", "11 см<super>3</super>")]
S += [grid([[P(h, tcellb) for h in ("Начальный", "При входе", "Наибольший", "Размах 2/1", "Вода внутри")]] +
           [[P(c, tcell) for c in r] for r in ang], [W / 5] * 5),
      figs([("f_tilt.png", "Рис. 5. Наклон оси воронки во времени"),
            ("f_waves.png", "Рис. 6. Уровень воды в двух точках бака")], height=36 * mm),
      P("4.6. Волны", h2),
      P("Каждое колебание выталкивает воду в стороны, и по поверхности расходятся кольцевые волны (рис. 4). Датчики у стенки "
        "бака показывают колебания уровня с периодом 0,40 с, как у самой воронки, и размахом в несколько миллиметров (рис. 6). "
        "Вязкое трение в пограничном слое толщиной "
        "√(ν/ω) ≈ 0,25 мм по оценке забирает около 12 % энергии за период, остальное уносят волны. Отражённая от стенок бака "
        "волна возвращается через 0,3 с и немного влияет на поздние колебания."),
      P("4.7. Вихри в носике", h2),
      P("Заполнение малой закреплённой воронки сравнивалось при острой и скруглённой входной кромке носика (рис. 7). На острой "
        "кромке поток отрывается и образует кольцевой вихрь, который сужает струю (рис. 8). При скруглении радиусом 1,4 мм "
        "начальный расход больше в 1,3 раза, 90 % уровня набирается за 0,41 с вместо 0,61 с. В формуле Торричелли это рост "
        "μ примерно с 0,6 до 0,8, и погружение с острой кромкой идёт медленнее. Уровень внутри по инерции ненадолго поднимается "
        "выше внешнего."),
      P("4.8. Заполнение и оседание", h2),
      P("В расчёте с открытым носиком вода бьёт из носика фонтаном высотой до 65 мм над дном конуса, вокруг струи "
        "закручиваются кольцевые вихри (рис. 10). Средний расход 26 см<super>3</super>/с: за 2,5 с в конус натекает "
        "67 см<super>3</super>, и уровень внутри поднимается на 51 мм. Воронка колеблется с прежним периодом 0,38 с и "
        "оседает в среднем на 3,4 мм/с (рис. 9), что совпадает с оценкой по формуле Торричелли (раздел 4.1)."),
      figrow([("f_vortex.png", "Рис. 7. Заполнение при двух кромках"), ("of_zoom.png", "Рис. 8. Вихрь"),
              ("f_open.png", "Рис. 9. Высота воронки и вода внутри"), ("of_open.png", "Рис. 10. Фонтан в конусе, t = 2 с")],
             height=37 * mm),
      P("4.9. Механизм по шагам", h2),
      P("Конус входит в воду, проскакивает равновесие и колеблется, излучая волны. Асимметрия при входе даёт наклон, "
        "колебания раскачивают его, а по мере заполнения ободок опускается к воде и захлёст становится возможен при всё меньшем наклоне.")]

S += [P("5. Выводы", h1),
      P("1) Воронка совершает затухающие колебания с периодом T = 2π√((M + m<sub>в</sub> + m<sub>пр</sub>)/(ρgA<sub>wl</sub>)); "
        "для исследованной воронки T = 0,39 с, декремент 0,42. Затухание в основном вызвано излучением волн.", item),
      P("2) Одновременно с колебаниями воронка оседает со скоростью, которую задаёт расход через носик, для нашей "
        "воронки 3,4 мм/с. Вихри на острой кромке уменьшают расход примерно на 25 %.", item),
      P("3) Пустая воронка устойчива (GM ≈ 18 мм), и вода внутри устойчивость не уменьшает. Малый наклон раскачивается "
        "вертикальными колебаниями до 20° за счёт параметрического резонанса и гаснет вместе с ними. Опасна не потеря устойчивости, а уменьшение "
        "высоты ободка над водой.", item),
      P("4) Опрокидывание начинается с захлёста: вода заливается через ободок, когда наклон превышает arctg(h/R). В расчётах "
        "захлёст был только при начальном наклоне 20°, полного переворота не было. Угол захлёста уменьшается при заполнении, "
        "поэтому риск растёт к концу погружения, особенно при низком ободке и раскачке.", item),
      P("5) Простая модель согласуется с двумя независимыми расчётами: периоды 0,391 с (DualSPHysics) и 0,38 с (OpenFOAM) "
        "различаются меньше чем на 3 % и лежат внутри оценки модели.", item)]

S += [P("6. Открытые материалы", h1),
      P("Геометрия воронки, настройки расчётов, скрипты обработки, таблицы движения, видео и контрольные суммы файлов "
        "лежат в открытом репозитории " + R["repo"] + ".", ParagraphStyle("lnk", parent=bodyni, alignment=TA_LEFT))]

SRC = [("Ландау Л. Д., Лифшиц Е. М. Механика. § 27. Параметрический резонанс.", None),
       ("DualSPHysics. Открытая программа для расчёта жидкости методом частиц.", "https://dual.sphysics.org"),
       ("Project Chrono. Открытый движок динамики твёрдых тел.", "https://projectchrono.org"),
       ("OpenFOAM. Открытый пакет вычислительной гидродинамики.", "https://www.openfoam.com"),
       ("Tracker. Бесплатная программа видеоанализа движения.", "https://physlets.org/tracker")]
S += [P("7. Источники", h1)]
for i, (t, u) in enumerate(SRC, 1):
    link = f' <link href="{u}" color="#1f4e79">{u.replace("https://", "").replace("www.", "")}</link>' if u else ""
    S.append(P(f"{i}. {t}{link}", ref))

Doc(sys.argv[1]).multiBuild(S)
