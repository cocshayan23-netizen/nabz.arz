# -*- coding: utf-8 -*-
"""NABZ | نبض بازار  -  pure Python (Kivy) version. Prices: tgju.org (unofficial)."""
import os, json, time, threading, datetime, urllib.request
from kivy.app import App
from kivy.clock import Clock
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.lang import Builder
from kivy.metrics import dp, sp
from kivy.properties import ListProperty
from kivy.graphics import Color, RoundedRectangle, Line, Mesh, Ellipse
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.uix.behaviors import ButtonBehavior
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.image import AsyncImage
from kivy.utils import get_color_from_hex, platform
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
except Exception:
    arabic_reshaper = None
from data import CATALOG, STR

HERE = os.path.dirname(os.path.abspath(__file__))
LabelBase.register('UI', HERE + '/fonts/DejaVuSans.ttf', fn_bold=HERE + '/fonts/DejaVuSans-Bold.ttf')
Builder.load_string('<Label>:\n    font_name: "UI"\n<TextInput>:\n    font_name: "UI"\n')

AJAX = "https://call3.tgju.org/ajax.json"
HIST = "https://api.tgju.org/v1/market/indicator/summary-table-data/"
BY = {i[0]: i for i in CATALOG}
DARK = dict(bg='#111620', card='#1E2430', card2='#2A303C', sel='#3A4050', text='#FFFFFF', sub='#8E96A5',
            up='#3DDC84', down='#FF6B6B', accent='#8C9EFF', menu='#434956', banner='#3949AB')
LIGHT = dict(bg='#F3F5F9', card='#FFFFFF', card2='#E3E7EF', sel='#FFFFFF', text='#111620', sub='#6B7280',
             up='#1E9E5A', down='#D93636', accent='#3949AB', menu='#FFFFFF', banner='#3949AB')
S = dict(unit='toman', lang='en', cal='gregorian', view='list', dark=True, alerts=[], raw={}, time=0, irr=0.1,
         favs=['price_dollar_rl', 'crypto-bitcoin', 'crypto-tether-irr', 'geram18', 'geram24', 'price_dkk'])
HC = {}
EXTRA = {
    'hint': ('۳ مورد اول در ویجت نمایش داده می‌شود. با فلش‌ها ترتیب را عوض کنید.',
             'Top 3 favorites will be shown in the widget. Use the arrows to reorder.',
             "İlk 3 favori widget'ta gösterilir. Sıralamak için okları kullanın."),
    'widgets': ('ویجت‌ها', 'Widgets', "Widget'lar"),
    'offline': ('اتصال برقرار نشد', 'Connection failed', 'Bağlantı hatası'),
    'unit': ('واحد قیمت', 'Price unit', 'Fiyat birimi'),
    'rial': ('ریال', 'Rial', 'Riyal'),
    'alert_title': ('هشدار قیمت', 'Price alerts', 'Fiyat uyarıları'),
}
WEEK = [('دوشنبه', 'سه‌شنبه', 'چهارشنبه', 'پنجشنبه', 'جمعه', 'شنبه', 'یکشنبه'),
        ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'),
        ('Pazartesi', 'Salı', 'Çarşamba', 'Perşembe', 'Cuma', 'Cumartesi', 'Pazar')]
GMON = [('ژانویه', 'فوریه', 'مارس', 'آوریل', 'مه', 'ژوئن', 'ژوئیه', 'اوت', 'سپتامبر', 'اکتبر', 'نوامبر', 'دسامبر'),
        ('January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'),
        ('Ocak', 'Şubat', 'Mart', 'Nisan', 'Mayıs', 'Haziran', 'Temmuz', 'Ağustos', 'Eylül', 'Ekim', 'Kasım', 'Aralık')]
PMON = ('فروردین', 'اردیبهشت', 'خرداد', 'تیر', 'مرداد', 'شهریور', 'مهر', 'آبان', 'آذر', 'دی', 'بهمن', 'اسفند')
PMON_EN = ('Farvardin', 'Ordibehesht', 'Khordad', 'Tir', 'Mordad', 'Shahrivar', 'Mehr', 'Aban', 'Azar', 'Dey', 'Bahman', 'Esfand')
FA_D = str.maketrans('0123456789', '۰۱۲۳۴۵۶۷۸۹')


# ---------------------------------------------------------------- helpers
def LI(): return {'fa': 0, 'en': 1, 'tr': 2}[S['lang']]
def C(k): return get_color_from_hex((DARK if S['dark'] else LIGHT)[k])
def T(k): return (STR.get(k) or EXTRA[k])[LI()]
def NAME(ins): return ins[5 + LI()]
def dg(s): return s.translate(FA_D) if S['lang'] == 'fa' else s

def sh(s, base=None):
    if arabic_reshaper and any('\u0600' <= c <= '\u06ff' for c in s):
        r = arabic_reshaper.reshape(s)
        return get_display(r, base_dir=base) if base else get_display(r)
    return s

def argb(n): return ((n >> 16) & 255) / 255., ((n >> 8) & 255) / 255., (n & 255) / 255., 1

def fmt(v):
    a = abs(v)
    if a >= 1000: s = "{:,.0f}".format(v)
    elif a >= 1: s = "{:,.2f}".format(v).rstrip('0').rstrip('.')
    else: s = "{:.4f}".format(v).rstrip('0').rstrip('.')
    return s or '0'

def jalali(gy, gm, gd):
    gdm = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    gy2 = gy + 1 if gm > 2 else gy
    days = 355666 + 365 * gy + (gy2 + 3) // 4 - (gy2 + 99) // 100 + (gy2 + 399) // 400 + gd + gdm[gm - 1]
    jy = -1595 + 33 * (days // 12053); days %= 12053
    jy += 4 * (days // 1461); days %= 1461
    if days > 365:
        jy += (days - 1) // 365; days = (days - 1) % 365
    jm = 1 + days // 31 if days < 186 else 7 + (days - 186) // 30
    jd = 1 + days % 31 if days < 186 else 1 + (days - 186) % 30
    return jy, jm, jd

def header_date():
    n = datetime.datetime.now(); i = LI()
    if S['cal'] == 'persian':
        _, jm, jd = jalali(n.year, n.month, n.day)
        d, m = jd, (PMON if i == 0 else PMON_EN)[jm - 1]
    else:
        d, m = n.day, GMON[i][n.month - 1]
    return dg("%s %d %s  •  %02d:%02d" % (WEEK[i][n.weekday()], d, m, n.hour, n.minute))

def chart_date(p, year_only):
    y, m, d = jalali(*p[:3]) if S['cal'] == 'persian' else p[:3]
    return dg(str(y) if year_only else "%d/%d" % (m, d))

def um(ins): return 10 if (S['unit'] == 'rial' and ins[8] != 'U') else 1
def factor(ins): return (0.1 if ins[8] == 'R' else 1.0 if ins[8] == 'U' else S['irr']) * um(ins)
def unit_name(ins): return 'USD' if ins[8] == 'U' else T('rial') if S['unit'] == 'rial' else T('toman')

def quote(key):
    r = S['raw'].get(key); ins = BY.get(key)
    if not r or not ins: return None
    f = factor(ins)
    return dict(ins=ins, price=r[0] * f, chg=r[3] * r[1] * f, pct=r[3] * r[2])

def http(url):
    rq = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
    return urllib.request.urlopen(rq, timeout=25).read().decode('utf8')

def num(s):
    try: return float(str(s).replace(',', '').replace('٬', '').strip())
    except Exception: return None

def fetch_raw():
    cur = json.loads(http(AJAX))['current']; out = {}
    for ins in CATALOG:
        o = cur.get(ins[0])
        if not isinstance(o, dict): continue
        p = num(o.get('p'))
        if p is None: continue
        dr = {'low': -1, 'high': 1}.get(o.get('dt'), 0)
        out[ins[0]] = [p, abs(num(o.get('d')) or 0), abs(num(o.get('dp')) or 0), dr]
    if not out: raise ValueError('empty')
    t, u = out.get('crypto-tether-irr'), out.get('price_dollar_rl')
    irr = 1.0 if (t and u and u[0] > 0 and t[0] < u[0] * 0.5) else 0.1
    return out, irr

def fetch_hist(key):
    if key in HC: return HC[key]
    rows = json.loads(http(HIST + key))['data']; out = []
    for r in rows:
        try:
            c = num(r[3]); y, m, d = [int(x) for x in str(r[6]).split('/')[:3]]
            if c is not None: out.append((y, m, d, c))
        except Exception: pass
    out.sort()
    if len(out) < 2: raise ValueError('no history')
    HC[key] = out
    return out


# ---------------------------------------------------------------- widgets
def bg(w, color, r=16, rad=None):
    with w.canvas.before:
        Color(*color)
        rr = RoundedRectangle(pos=w.pos, size=w.size, radius=rad or [dp(r)])
    w.bind(pos=lambda *a: setattr(rr, 'pos', w.pos), size=lambda *a: setattr(rr, 'size', w.size))
    return rr

class L(Label):
    def __init__(s, text='', size=16, color='text', bold=False, align='left', h=None, base=None, **kw):
        col = C(color) if isinstance(color, str) else color
        super().__init__(text=sh(dg(text), base), font_size=sp(size), color=col, bold=bold,
                         halign=align, valign='middle', **kw)
        s.bind(size=lambda *a: setattr(s, 'text_size', s.size))
        if h: s.size_hint_y = None; s.height = dp(h)

class Tap(ButtonBehavior, BoxLayout): pass

class Solid(BoxLayout):
    def on_touch_down(self, t):
        r = super().on_touch_down(t)
        return True if self.collide_point(*t.pos) else r

class Full(FloatLayout):
    def on_touch_down(self, t):
        super().on_touch_down(t); return True

class PullSV(ScrollView):
    on_pull = None
    def on_touch_down(self, t):
        self._y0 = t.y if self.collide_point(*t.pos) else None
        return super().on_touch_down(t)
    def on_touch_up(self, t):
        y0 = getattr(self, '_y0', None)
        if y0 is not None and self.scroll_y >= 0.98 and y0 - t.y > dp(110) and self.on_pull:
            self.on_pull()
        self._y0 = None
        return super().on_touch_up(t)

class Seg(BoxLayout):
    def __init__(s, labels, sel, cb):
        super().__init__(size_hint_y=None, height=dp(52), padding=dp(5), spacing=dp(4))
        bg(s, C('card2'), 20); s.bs = []; s.cb = cb
        for i, t in enumerate(labels):
            b = Tap(); b.add_widget(L(t, 15, align='center'))
            with b.canvas.before:
                b.cc = Color(0, 0, 0, 0); b.rr = RoundedRectangle(pos=b.pos, size=b.size, radius=[dp(15)])
            b.bind(pos=lambda w, v: setattr(w.rr, 'pos', v), size=lambda w, v: setattr(w.rr, 'size', v))
            b.bind(on_release=lambda w, i=i: s.pick(i)); s.bs.append(b); s.add_widget(b)
        s.mark(sel)
    def mark(s, i):
        for k, b in enumerate(s.bs): b.cc.rgba = C('sel') if k == i else (0, 0, 0, 0)
    def pick(s, i): s.mark(i); s.cb(i)

def circle(w, rgba):
    with w.canvas.before:
        Color(*rgba); e = Ellipse(pos=w.pos, size=w.size)
    w.bind(pos=lambda *a: setattr(e, 'pos', w.pos), size=lambda *a: setattr(e, 'size', w.size))

def icon(ins, d=50):
    f = FloatLayout(size_hint=(None, None), size=(dp(d), dp(d)))
    if ins[1] == 2:
        cc = ''.join(chr(ord(c) - 0x1F1E6 + 97) for c in ins[3] if 0x1F1E6 <= ord(c) <= 0x1F1FF)
        f.add_widget(L(ins[2], 11, 'sub', align='center'))
        f.add_widget(AsyncImage(source='https://flagcdn.com/w80/%s.png' % cc, size_hint=(1, .75),
                                pos_hint={'center_x': .5, 'center_y': .5}))
    else:
        circle(f, argb(ins[4]))
        fg = (0.23, 0.18, 0, 1) if ins[1] == 1 else (1, 1, 1, 1)
        f.add_widget(L(ins[3], 11 if len(ins[3]) > 2 else 18, fg, bold=True, align='center'))
    return f

def field(hint, **kw):
    b = BoxLayout(size_hint_y=None, height=dp(54), padding=[dp(14), 0]); bg(b, C('card2') if not kw.pop('alt', 0) else C('bg'), 16)
    ti = TextInput(hint_text=hint, multiline=False, background_color=(0, 0, 0, 0), background_normal='',
                   background_active='', foreground_color=C('text'), hint_text_color=C('sub'), cursor_color=C('text'),
                   font_size=sp(17), padding=[0, dp(15)], **kw)
    b.add_widget(ti); b.ti = ti
    return b

class Chart(Widget):
    pts = ListProperty([])
    def __init__(s, **kw):
        super().__init__(**kw); s.bind(pos=s.draw, size=s.draw, pts=s.draw)
    def draw(s, *a):
        s.canvas.clear(); p = s.pts
        if len(p) < 2 or s.width < 4: return
        step = max(1, len(p) // 160); p = p[::step] + ([p[-1]] if (len(p) - 1) % step else [])
        n = len(p); lo, hi = min(p), max(p); rg = (hi - lo) or 1
        xs = [s.x + s.width * i / (n - 1) for i in range(n)]
        ys = [s.y + dp(8) + (s.height - dp(30)) * (v - lo) / rg for v in p]
        col = C('up') if p[-1] >= p[0] else C('down'); B = 8
        with s.canvas:
            for k in range(B):
                bb, bt = s.y + s.height * k / B, s.y + s.height * (k + 1) / B
                if max(ys) <= bb: break
                vs = []
                for x, y in zip(xs, ys):
                    vs += [x, min(y, bt) if y > bb else bb, 0, 0, x, bb, 0, 0]
                Color(col[0], col[1], col[2], 0.05 + 0.25 * k / (B - 1))
                Mesh(vertices=vs, indices=list(range(2 * n)), mode='triangle_strip')
            Color(*col)
            Line(points=[c for xy in zip(xs, ys) for c in xy], width=dp(2.2), joint='round', cap='round')


# ---------------------------------------------------------------- app
class NabzApp(App):
    def build(self):
        self.path = os.path.join(self.user_data_dir, 'nabz.json'); self.load()
        if platform not in ('android', 'ios'): Window.size = (410, 840)
        self.busy = False; self.stack = []
        self.root = FloatLayout(); self.render()
        Window.bind(on_keyboard=self.on_key)
        Clock.schedule_once(self.refresh, 0.3); Clock.schedule_interval(self.refresh, 90)
        return self.root

    def load(self):
        try:
            d = json.load(open(self.path, encoding='utf8'))
            S.update({k: d[k] for k in S if k in d})
        except Exception: pass
    def save(self):
        try: json.dump({k: S[k] for k in S}, open(self.path, 'w', encoding='utf8'))
        except Exception: pass

    def on_key(self, w, key, *a):
        if key == 27 and self.stack: self.pop(); return True
    def push(self, w): self.root.add_widget(w); self.stack.append(w)
    def pop(self):
        if self.stack: self.root.remove_widget(self.stack.pop())
    def modal(self, content):
        lay = FloatLayout(); d = Tap(); bg(d, (0, 0, 0, .55), 0)
        d.bind(on_release=lambda *a: self.pop()); lay.add_widget(d); lay.add_widget(content); self.push(lay)
    def screen(self):
        f = Full(); bg(f, C('bg'), 0); self.push(f); return f
    def toast(self, msg):
        t = L(msg, 15, 'text', align='center', size_hint=(.9, None), height=dp(54), pos_hint={'center_x': .5, 'y': .14})
        bg(t, C('menu'), 18); self.root.add_widget(t)
        Clock.schedule_once(lambda dt: self.root.remove_widget(t), 3.2)

    # ------------------------------------------------ home
    def render(self):
        self.root.clear_widgets(); self.stack = []
        Window.clearcolor = C('bg')
        col = BoxLayout(orientation='vertical', padding=[dp(16), dp(36), dp(16), 0], spacing=dp(2))
        col.add_widget(L('NABZ | نبض بازار', 30, bold=True, h=50, base='L'))
        self.dt = L(header_date(), 15, 'sub', h=24); col.add_widget(self.dt)
        self.st = L('', 13, 'sub', h=24); col.add_widget(self.st)
        sv = PullSV(do_scroll_x=False, bar_width=0); sv.on_pull = self.refresh
        self.grid = GridLayout(cols=2 if S['view'] == 'grid' else 1, spacing=dp(10), size_hint_y=None,
                               padding=[0, dp(8), 0, dp(110)])
        self.grid.bind(minimum_height=self.grid.setter('height'))
        sv.add_widget(self.grid); col.add_widget(sv); self.root.add_widget(col)
        r = Tap(size_hint=(None, None), size=(dp(72), dp(72)), pos=(dp(16), dp(24))); circle(r, (0, 0, 0, 1))
        r.add_widget(L('↻', 30, (1, 1, 1, 1), align='center')); r.bind(on_release=self.refresh)
        pill = BoxLayout(size_hint=(None, None), size=(dp(150), dp(72)), pos=(Window.width - dp(166), dp(24)))
        bg(pill, C('card'), 36)
        for sym, fn in (('+', self.sheet), ('⋮', self.menu)):
            b = Tap(); b.add_widget(L(sym, 30, align='center')); b.bind(on_release=lambda w, fn=fn: fn()); pill.add_widget(b)
        pill.pos_hint = {'right': .96}; pill.pos = (0, dp(24))
        fl = FloatLayout(); fl.add_widget(r); r.pos_hint = {'x': .04, 'y': .0}
        self.root.add_widget(r); r.pos = (dp(16), dp(24))
        pill.size_hint = (None, None); self.root.add_widget(pill)
        pill.pos = (Window.width - dp(166), dp(24)); Window.bind(width=lambda w, v: setattr(pill, 'x', v - dp(166)))
        self.fill()

    def fill(self):
        self.grid.clear_widgets()
        if S['time']:
            self.st.text = sh(dg("%s: %s" % (T('updated'), time.strftime('%H:%M', time.localtime(S['time'])))))
        else: self.st.text = sh(T('loading'))
        self.dt.text = sh(header_date())
        for k in S['favs']:
            q = quote(k)
            if q: self.grid.add_widget(self.card(q))

    def card(self, q):
        ins = q['ins']; up = q['chg'] >= 0
        chg = L(("↑ " if up else "↓ ") + fmt(abs(q['chg'])), 14, 'up' if up else 'down', align='right')
        if S['view'] == 'grid':
            c = Tap(orientation='vertical', size_hint_y=None, height=dp(185), padding=dp(14), spacing=dp(2))
            c.add_widget(icon(ins, 46)); c.add_widget(L(NAME(ins), 15, bold=True, h=26))
            c.add_widget(L(ins[2], 12, 'sub', h=18)); c.add_widget(L(fmt(q['price']), 19, bold=True, h=30))
            chg.halign = 'left'; chg.size_hint_y = None; chg.height = dp(22); c.add_widget(chg)
        else:
            c = Tap(size_hint_y=None, height=dp(90), padding=dp(16), spacing=dp(14))
            c.add_widget(icon(ins, 52))
            mid = BoxLayout(orientation='vertical'); mid.add_widget(L(NAME(ins), 18, bold=True)); mid.add_widget(L(ins[2], 14, 'sub'))
            rt = BoxLayout(orientation='vertical', size_hint_x=None, width=dp(135))
            rt.add_widget(L(fmt(q['price']), 20, bold=True, align='right')); rt.add_widget(chg)
            c.add_widget(mid); c.add_widget(rt)
        bg(c, C('card'), 22); c.bind(on_release=lambda *a: self.detail(ins[0]))
        return c

    def refresh(self, *a):
        if self.busy: return
        self.busy = True; self.st.text = sh(T('loading'))
        def work():
            try: r, irr, e = *fetch_raw(), None
            except Exception as ex: r = irr = None; e = ex
            Clock.schedule_once(lambda dt: self.refreshed(r, irr, e))
        threading.Thread(target=work, daemon=True).start()

    def refreshed(self, raw, irr, err):
        self.busy = False
        if raw:
            S['raw'], S['irr'], S['time'] = raw, irr, time.time(); self.save(); self.check_alerts()
        else: self.toast(T('offline'))
        self.fill()

    def check_alerts(self):
        keep = []
        for a in S['alerts']:
            q = quote(a['key'])
            if q and ((a['above'] and q['price'] >= a['price'] * um(q['ins'])) or (not a['above'] and q['price'] <= a['price'] * um(q['ins']))):
                msg = "%s %s" % (NAME(q['ins']), T('alert_hit') % fmt(a['price'] * um(q['ins'])))
                self.toast(msg)
                try:
                    from plyer import notification
                    notification.notify(title='NABZ', message=msg)
                except Exception: pass
            else: keep.append(a)
        if len(keep) != len(S['alerts']): S['alerts'] = keep; self.save()

    # ------------------------------------------------ menu (⋮)
    def menu(self, op=None):
        if self.stack and op is not None: self.pop()
        i = LI()
        groups = [('view', 'menu_view', '▦', [('grid', T('grid')), ('list', T('list'))], S['view']),
                  ('cal', 'calendar', '▣', [('persian', T('persian')), ('gregorian', T('gregorian'))], S['cal']),
                  ('lang', 'language', '◎', [('en', 'English'), ('tr', 'Türkçe'), ('fa', 'فارسی')], S['lang']),
                  ('unit', 'unit', '¤', [('toman', T('toman')), ('rial', T('rial'))], S['unit']),
                  ('dark', 'theme', '◐', [(True, T('dark')), (False, T('light'))], S['dark'])]
        box = Solid(orientation='vertical', size_hint=(.78, None), padding=[dp(14), dp(10)], pos_hint={'center_x': .5, 'y': .12})
        box.bind(minimum_height=box.setter('height')); bg(box, C('menu'), 30)
        box.size_hint_y = None
        def row(txt, sym, cb, col='text', last=False):
            r = Tap(size_hint_y=None, height=dp(70), padding=[dp(14), 0])
            r.add_widget(L(('› ' if sym else '') + txt, 19, col)); 
            if sym: r.add_widget(L(sym, 20, 'sub', align='right', size_hint_x=None, width=dp(40)))
            r.bind(on_release=lambda *a: cb()); box.add_widget(r)
        for key, sk, sym, opts, cur in groups:
            row(T(sk), sym, lambda key=key: (self.pop(), self.menu(None if op == key else key)))
            if op == key:
                for val, lab in opts:
                    r = Tap(size_hint_y=None, height=dp(56), padding=[dp(34), 0])
                    r.add_widget(L(lab, 18, 'accent' if val == cur else 'text'))
                    r.add_widget(L('✓' if val == cur else '', 24, 'accent', align='right', size_hint_x=None, width=dp(40)))
                    r.bind(on_release=lambda w, key=key, val=val: self.setting(key, val)); box.add_widget(r)
        row(T('manage'), '♡', lambda: (self.pop(), self.manage()))
        row(T('widgets'), '▤', lambda: (self.pop(), self.widgets()))
        self.modal(box)

    def setting(self, key, val):
        S[key] = val; self.save(); self.render()

    # ------------------------------------------------ add sheet (+)
    def sheet(self):
        st = dict(tab=0, q='')
        box = Solid(orientation='vertical', size_hint=(1, .8), pos_hint={'x': 0, 'y': 0}, padding=[dp(16), dp(18), dp(16), 0], spacing=dp(12))
        bg(box, C('bg'), 0, [dp(34), dp(34), 0, 0])
        def setq(w, v): st['q'] = v.lower(); fillrows()
        def settab(i): st['tab'] = i; fillrows()
        box.add_widget(Seg([T('tab_crypto'), T('tab_gold'), T('tab_currency')], 0, settab))
        sf = field(T('search')); sf.ti.bind(text=setq); box.add_widget(sf)
        sv = ScrollView(bar_width=dp(3)); g = GridLayout(cols=1, size_hint_y=None); g.bind(minimum_height=g.setter('height'))
        sv.add_widget(g); box.add_widget(sv)
        def fillrows():
            g.clear_widgets()
            for ins in CATALOG:
                if ins[1] != (0, 1, 2)[st['tab']]: continue
                if st['q'] and st['q'] not in (' '.join((ins[2], ins[5], ins[6], ins[7]))).lower(): continue
                r = Tap(size_hint_y=None, height=dp(78), padding=[dp(6), dp(8)], spacing=dp(14))
                r.add_widget(icon(ins, 50)); r.add_widget(L(NAME(ins), 18))
                mk = L('', 26, size_hint_x=None, width=dp(44), align='center'); r.add_widget(mk)
                def paint(mk=mk, k=ins[0]):
                    on = k in S['favs']; mk.text = '✓' if on else '+'; mk.color = C('up') if on else C('sub')
                paint()
                def tog(w, k=ins[0], paint=paint):
                    S['favs'].remove(k) if k in S['favs'] else S['favs'].append(k)
                    self.save(); paint(); self.fill()
                r.bind(on_release=tog); g.add_widget(r)
        fillrows(); self.modal(box)

    # ------------------------------------------------ manage favorites
    def manage(self):
        f = self.screen()
        col = BoxLayout(orientation='vertical', padding=[dp(16), dp(36), dp(16), dp(16)], spacing=dp(12))
        hd = BoxLayout(size_hint_y=None, height=dp(70)); hd.add_widget(L(T('manage'), 28, bold=True))
        x = Tap(size_hint_x=None, width=dp(60)); x.add_widget(L('✕', 28, align='center')); x.bind(on_release=lambda *a: (self.pop(), self.fill()))
        hd.add_widget(x); col.add_widget(hd)
        ban = L(T('hint'), 16, (1, 1, 1, 1), h=82, padding=[dp(20), 0]); bg(ban, C('banner'), 24); col.add_widget(ban)
        sv = ScrollView(bar_width=0); g = GridLayout(cols=1, spacing=dp(10), size_hint_y=None); g.bind(minimum_height=g.setter('height'))
        sv.add_widget(g); col.add_widget(sv); f.add_widget(col)
        def build():
            g.clear_widgets(); n = len(S['favs'])
            for i, k in enumerate(S['favs']):
                ins = BY[k]; r = BoxLayout(size_hint_y=None, height=dp(86), padding=[dp(10), 0], spacing=dp(4)); bg(r, C('card'), 22)
                r.add_widget(L('⋮⋮', 18, 'sub', align='center', size_hint_x=None, width=dp(36)))
                m = FloatLayout(size_hint_x=None, width=dp(44))
                if i < 3:
                    mm = Widget(size_hint=(None, None), size=(dp(30), dp(30)), pos_hint={'center_x': .5, 'center_y': .5})
                    circle(mm, get_color_from_hex(('#F5B301', '#B0B7C3', '#CD7F32')[i])); m.add_widget(mm)
                    m.add_widget(L(str(i + 1), 14, (0, 0, 0, 1), bold=True, align='center'))
                r.add_widget(m)
                mid = BoxLayout(orientation='vertical'); mid.add_widget(L(NAME(ins), 18, bold=True)); mid.add_widget(L(ins[2], 14, 'sub')); r.add_widget(mid)
                def btn(sym, col, cb):
                    b = Tap(size_hint_x=None, width=dp(52)); b.add_widget(L(sym, 24, col, align='center'))
                    if cb: b.bind(on_release=lambda *a: cb())
                    r.add_widget(b)
                btn('▲', 'text' if i > 0 else 'card2', (lambda i=i: mv(i, -1)) if i > 0 else None)
                btn('▼', 'text' if i < n - 1 else 'card2', (lambda i=i: mv(i, 1)) if i < n - 1 else None)
                btn('✕', 'down', lambda k=k: rm(k)); g.add_widget(r)
        def mv(i, d):
            S['favs'][i], S['favs'][i + d] = S['favs'][i + d], S['favs'][i]; self.save(); build()
        def rm(k): S['favs'].remove(k); self.save(); build()
        build()

    # ------------------------------------------------ widgets gallery
    def widgets(self):
        f = self.screen(); qs = [q for q in (quote(k) for k in S['favs']) if q][:3]
        col = BoxLayout(orientation='vertical', padding=[dp(16), dp(36), dp(16), dp(16)], spacing=dp(12))
        hd = BoxLayout(size_hint_y=None, height=dp(70)); hd.add_widget(L(T('widgets'), 28, bold=True))
        x = Tap(size_hint_x=None, width=dp(60)); x.add_widget(L('✕', 28, align='center')); x.bind(on_release=lambda *a: self.pop()); hd.add_widget(x)
        col.add_widget(hd)
        sv = ScrollView(bar_width=0); g = GridLayout(cols=1, spacing=dp(12), size_hint_y=None); g.bind(minimum_height=g.setter('height')); sv.add_widget(g)
        if qs:
            def single(q, big):
                b = BoxLayout(orientation='vertical', padding=dp(20)); bg(b, C('card'), 30)
                top = BoxLayout(size_hint_y=None, height=dp(56)); top.add_widget(icon(q['ins'], 48))
                nm = BoxLayout(orientation='vertical'); nm.add_widget(L(NAME(q['ins']), 17, align='right')); nm.add_widget(L(q['ins'][2], 14, 'sub', align='right')); top.add_widget(nm)
                b.add_widget(top); b.add_widget(Widget())
                up = q['chg'] >= 0
                b.add_widget(L(('↑ ' if up else '↓ ') + fmt(abs(q['chg'])), 15, 'up' if up else 'down', h=26))
                b.add_widget(L(fmt(q['price']), 34 if big else 28, bold=True, h=54)); return b
            def lst(rows, tall):
                b = BoxLayout(orientation='vertical', padding=dp(18), spacing=dp(4)); bg(b, C('card'), 30)
                for q in rows:
                    r = BoxLayout(); lf = BoxLayout(orientation='vertical', size_hint_x=.4)
                    lf.add_widget(icon(q['ins'], 28 if not tall else 34)); lf.add_widget(L(q['ins'][2], 14))
                    rt = BoxLayout(orientation='vertical'); up = q['chg'] >= 0
                    rt.add_widget(L(('↑ ' if up else '↓ ') + fmt(abs(q['chg'])), 14, 'up' if up else 'down', align='right'))
                    rt.add_widget(L(fmt(q['price']), 20, bold=True, align='right')); r.add_widget(lf); r.add_widget(rt); b.add_widget(r)
                return b
            w = single(qs[0], True); w.size_hint_y = None; w.height = dp(210); g.add_widget(w)
            row = BoxLayout(size_hint_y=None, height=dp(210), spacing=dp(12)); row.add_widget(single(qs[0], False)); row.add_widget(lst(qs, False)); g.add_widget(row)
            w = lst(qs, True); w.size_hint_y = None; w.height = dp(300); g.add_widget(w)
        col.add_widget(sv); f.add_widget(col)

    # ------------------------------------------------ detail page
    def detail(self, key):
        q = quote(key)
        if not q: return
        ins = q['ins']; up = q['chg'] >= 0; f = self.screen(); st = dict(r=0, data=None)
        sv = ScrollView(bar_width=0); box = BoxLayout(orientation='vertical', size_hint_y=None, padding=[dp(20), dp(36), dp(20), dp(30)], spacing=dp(4))
        box.bind(minimum_height=box.setter('height')); sv.add_widget(box); f.add_widget(sv)
        hd = BoxLayout(size_hint_y=None, height=dp(72), spacing=dp(14)); hd.add_widget(icon(ins, 54))
        nm = BoxLayout(orientation='vertical'); nm.add_widget(L(NAME(ins), 24, bold=True)); nm.add_widget(L(ins[2], 16, 'sub')); hd.add_widget(nm)
        x = Tap(size_hint_x=None, width=dp(60)); x.add_widget(L('✕', 28, align='center')); x.bind(on_release=lambda *a: self.pop()); hd.add_widget(x); box.add_widget(hd)
        box.add_widget(Widget(size_hint_y=None, height=dp(16)))
        box.add_widget(L(('↑ ' if up else '↓ ') + fmt(abs(q['chg'])), 20, 'up' if up else 'down', h=32))
        box.add_widget(L(fmt(q['price'] - q['chg']), 20, 'sub', h=32))
        box.add_widget(L(fmt(q['price']), 58, bold=True, h=80))
        box.add_widget(L("%s  ·  %s%%" % (unit_name(ins), ("%.2f" % abs(q['pct']))), 16, 'sub', h=32))
        if ins[8] != 'U':
            ro = S['unit'] == 'rial'
            box.add_widget(L("≈ %s %s" % (fmt(q['price'] / 10 if ro else q['price'] * 10), T('toman') if ro else T('rial')), 16, 'sub', h=30))
        hl = BoxLayout(size_hint_y=None, height=dp(40)); hi = L('', 16, 'up', bold=True); lo = L('', 16, 'down', bold=True, align='right')
        hl.add_widget(hi); hl.add_widget(lo); box.add_widget(hl)
        ch = Chart(size_hint_y=None, height=dp(300)); box.add_widget(ch)
        ph = L(T('chart_loading'), 15, 'sub', align='center', h=24); box.add_widget(ph)
        dl = BoxLayout(size_hint_y=None, height=dp(30)); dls = [L('', 14, 'sub', align=a) for a in ('left', 'center', 'center', 'right')]
        for d in dls: dl.add_widget(d)
        box.add_widget(dl); box.add_widget(Widget(size_hint_y=None, height=dp(8)))
        def show(i=None):
            if i is not None: st['r'] = i
            d = st['data']
            if not d: return
            d = d[-(31, 366, 10 ** 9)[st['r']]:]; fc = factor(ins); vals = [p[3] * fc for p in d]
            ch.pts = vals; hi.text = sh(dg("%s: %s" % (T('high'), fmt(max(vals))))); lo.text = sh(dg("%s: %s" % (T('low'), fmt(min(vals)))))
            n = len(d)
            for k, lb in enumerate(dls): lb.text = sh(chart_date(d[round((n - 1) * k / 3)], st['r'] == 2))
        box.add_widget(Seg([T('r1m'), T('r1y'), T('rall')], 0, show))
        def got(d, e):
            if not f.parent: return
            if d: st['data'] = d; ph.text = ''; ph.height = 0; show()
            else: ph.text = sh(T('nodata'))
        def work():
            try: d, e = fetch_hist(key), None
            except Exception as ex: d, e = None, ex
            Clock.schedule_once(lambda dt: got(d, e))
        threading.Thread(target=work, daemon=True).start()
        # converter
        cv = BoxLayout(orientation='vertical', size_hint_y=None, height=dp(250), padding=dp(22), spacing=dp(12)); bg(cv, C('card'), 30)
        cv.add_widget(L(T('converter'), 22, bold=True, h=34))
        a = field(T('amount'), input_filter='float'); v = field(T('value'), input_filter='float'); lock = [False]
        for fld, un in ((a, ins[2] if ins[8] != 'U' or ins[1] != 1 else 'USD'), (v, unit_name(ins))):
            r = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(12)); r.add_widget(fld); r.add_widget(L(un, 17, 'sub', size_hint_x=None, width=dp(80))); cv.add_widget(r)
        def conv(src, dst, mul):
            def cb(w, t):
                if lock[0]: return
                lock[0] = True
                try: dst.ti.text = ("%.4f" % (float(t) * mul)).rstrip('0').rstrip('.') if t else ''
                except Exception: dst.ti.text = ''
                lock[0] = False
            src.ti.bind(text=cb)
        conv(a, v, q['price']); conv(v, a, 1.0 / q['price'] if q['price'] else 0)
        box.add_widget(cv); box.add_widget(Widget(size_hint_y=None, height=dp(10)))
        # alerts
        ac = BoxLayout(orientation='vertical', size_hint_y=None, padding=dp(22), spacing=dp(8)); ac.bind(minimum_height=ac.setter('height')); bg(ac, C('card'), 30)
        box.add_widget(ac)
        def alerts():
            ac.clear_widgets(); ac.add_widget(L(T('alert_title'), 22, bold=True, h=34)); mine = [x for x in S['alerts'] if x['key'] == key]
            if not mine: ac.add_widget(L(T('no_alerts'), 16, 'sub', h=30))
            for x in mine:
                r = BoxLayout(size_hint_y=None, height=dp(44)); r.add_widget(L("%s %s" % (T('above') if x['above'] else T('below'), fmt(x['price'] * um(ins))), 17))
                d = Tap(size_hint_x=None, width=dp(50)); d.add_widget(L('✕', 20, 'down', align='center'))
                d.bind(on_release=lambda w, x=x: (S['alerts'].remove(x), self.save(), alerts())); r.add_widget(d); ac.add_widget(r)
            b = Tap(size_hint_y=None, height=dp(44)); b.add_widget(L(T('add_alert'), 18, 'accent', bold=True)); b.bind(on_release=lambda *z: add()); ac.add_widget(b)
        def add():
            sd = dict(above=True); dlg = Solid(orientation='vertical', size_hint=(.9, None), height=dp(300), padding=dp(20), spacing=dp(12), pos_hint={'center_x': .5, 'center_y': .5}); bg(dlg, C('card'), 28)
            dlg.add_widget(L(NAME(ins), 20, bold=True, h=34)); dlg.add_widget(Seg([T('above'), T('below')], 0, lambda i: sd.update(above=(i == 0))))
            pf = field(T('price'), input_filter='float'); pf.ti.text = fmt(q['price']).replace(',', ''); dlg.add_widget(pf)
            br = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(12))
            for lab, ok in ((T('cancel'), False), (T('save'), True)):
                b = Tap(); b.add_widget(L(lab, 18, 'accent' if ok else 'sub', bold=ok, align='center')); br.add_widget(b)
                def go(w, ok=ok):
                    if ok:
                        p = num(pf.ti.text)
                        if p: S['alerts'].append(dict(key=key, above=sd['above'], price=p / um(ins))); self.save()
                    self.pop(); alerts()
                b.bind(on_release=go)
            dlg.add_widget(br); self.modal(dlg)
        alerts()


if __name__ == '__main__':
    NabzApp().run()
