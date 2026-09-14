"""Overlap QA for the version-10 plates (run inside v10_figstyle.save).

Checks, in figure pixels at the figure dpi: text vs text (any two visible texts),
text vs foreground data marks of its own axes and twins (polylines, markers, scatter
points, bars, error bars), legend box vs data marks and vs other texts, and inset
axes vs the parent's data marks and texts. Background shading (gid 'shade'),
translucent bands (alpha < 0.5), axvline/axhline reference lines and white labels
drawn inside bars are ignored by design."""
import numpy as np
from matplotlib.text import Text
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle, Polygon
from matplotlib.collections import PathCollection, LineCollection, PolyCollection
from matplotlib.transforms import Bbox

TOL = 0.8   # px

def _all_axes(fig):
    out = []
    for ax in fig.axes:
        out.append(ax); out.extend(getattr(ax, 'child_axes', []))
    return out

def _siblings(ax):
    """The axes itself and its twins (same position), children excluded."""
    p = ax.get_position().bounds
    kids = getattr(ax, 'child_axes', [])
    return [a for a in _all_axes(ax.figure) if a is ax or (a.get_position().bounds == p and a not in kids)]

def _texts(fig, r):
    hidden, ticks, labels, legend_of = set(), {}, set(), {}
    for ax in _all_axes(fig):
        for axis, lim in ((ax.xaxis, ax.get_xlim()), (ax.yaxis, ax.get_ylim())):
            lo, hi = min(lim), max(lim); labels.add(id(axis.label))
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                for lab in (tick.label1, tick.label2):
                    ticks[id(lab)] = axis
                    if tick.get_loc() < lo or tick.get_loc() > hi: hidden.add(id(lab))
        lg = ax.get_legend()
        if lg is not None:
            for t in lg.get_texts(): legend_of[id(t)] = lg
    items = []
    for t in fig.findobj(Text):
        if id(t) in hidden or not t.get_visible() or not t.get_text().strip(): continue
        try: bb = t.get_window_extent(r)
        except Exception: continue
        if bb.width <= 0 or bb.height <= 0: continue
        if id(t) in legend_of: kind, grp = 'legend', legend_of[id(t)]
        elif id(t) in ticks: kind, grp = 'tick', ticks[id(t)]
        elif id(t) in labels: kind, grp = 'label', None
        else: kind, grp = 'text', None
        items.append(dict(t=t, bb=bb, kind=kind, grp=grp, ax=t.axes, s=t.get_text().replace('\n', ' / ')[:40]))
    return items

def _inter(a, b):
    return min(a.x1, b.x1) - max(a.x0, b.x0), min(a.y1, b.y1) - max(a.y0, b.y0)

def _overlap(a, b, tol=TOL):
    w, h = _inter(a, b); return w > tol and h > tol

def _sample(poly, step=1.5):
    """Sample points along a polyline given in pixels (NaN breaks the line)."""
    pts = []
    for k in range(len(poly) - 1):
        p0, p1 = poly[k], poly[k + 1]
        if not (np.all(np.isfinite(p0)) and np.all(np.isfinite(p1))): continue
        n = int(np.hypot(*(p1 - p0)) / step) + 2
        pts.append(np.linspace(p0, p1, n))
    return np.vstack(pts) if pts else np.empty((0, 2))

def _marks(ax):
    """Foreground data marks of an axes and its twins: (name, kind, payload)."""
    dpi = ax.figure.dpi; marks = []
    for a in _siblings(ax):
        xt, yt = a.get_xaxis_transform(), a.get_yaxis_transform()
        for ln in a.lines:
            if not ln.get_visible() or ln.get_transform() is xt or ln.get_transform() is yt: continue
            xy = np.column_stack([np.asarray(v, dtype=float) for v in ln.get_data()])
            if not len(xy): continue
            px = ln.get_transform().transform(xy); name = (ln.get_label() or 'line')[:30]
            if ln.get_linestyle() not in ('None', '', ' ', None): marks.append((name, 'line', _sample(px)))
            if ln.get_marker() not in (None, 'None', '', ' '):
                marks.append((name, 'marker', (px[np.all(np.isfinite(px), axis=1)], ln.get_markersize() / 2 * dpi / 72)))
        for c in a.collections:
            if not c.get_visible(): continue
            alpha = c.get_alpha()
            if isinstance(c, PathCollection):
                off = np.asarray(c.get_offsets(), dtype=float)
                if not len(off): continue
                px = c.get_offset_transform().transform(off); s = np.asarray(c.get_sizes(), dtype=float)
                rad = float(np.sqrt(s.max()) / 2 * dpi / 72) if len(s) else 2.0
                marks.append(((c.get_label() or 'points')[:30], 'marker', (px[np.all(np.isfinite(px), axis=1)], rad)))
            elif isinstance(c, LineCollection):
                tr = c.get_transform(); pts = [_sample(tr.transform(np.asarray(seg, dtype=float))) for seg in c.get_segments()]
                if pts: marks.append(('errorbar', 'line', np.vstack(pts)))
            elif isinstance(c, PolyCollection):
                if alpha is not None and alpha < 0.5: continue
                marks.append(((c.get_label() or 'area')[:30], 'rect', c.get_window_extent(ax.figure.canvas.get_renderer())))
        for p in a.patches:
            if not p.get_visible() or p.get_gid() in ('shade', 'bg'): continue
            if p.get_alpha() is not None and p.get_alpha() < 0.5: continue
            if isinstance(p, (Rectangle, Polygon)):
                bb = p.get_window_extent(ax.figure.canvas.get_renderer())
                if bb.width > 0.5 and bb.height > 0.5: marks.append(((p.get_label() or 'bar')[:30], 'rect', bb))
    return marks

def _hits(bb, marks, tol=TOL):
    out = []; sb = Bbox.from_extents(bb.x0 + tol, bb.y0 + tol, bb.x1 - tol, bb.y1 - tol)
    if sb.width <= 0 or sb.height <= 0: return out
    for name, kind, payload in marks:
        if kind == 'line':
            if len(payload) and np.any((payload[:, 0] >= sb.x0) & (payload[:, 0] <= sb.x1) & (payload[:, 1] >= sb.y0) & (payload[:, 1] <= sb.y1)): out.append(f'{kind} {name}')
        elif kind == 'marker':
            px, rad = payload
            if len(px) and np.any((px[:, 0] >= sb.x0 - rad) & (px[:, 0] <= sb.x1 + rad) & (px[:, 1] >= sb.y0 - rad) & (px[:, 1] <= sb.y1 + rad)): out.append(f'{kind} {name}')
        elif kind == 'rect':
            if _overlap(sb, payload, 0): out.append(f'{kind} {name}')
    return out

def overlaps(fig):
    fig.canvas.draw(); r = fig.canvas.get_renderer(); items = _texts(fig, r); found = []
    # 1. text vs text
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            a, b = items[i], items[j]
            if a['kind'] == 'legend' and b['kind'] == 'legend' and a['grp'] is b['grp']: continue
            if a['kind'] == 'tick' and b['kind'] == 'tick' and a['grp'] is b['grp'] and a['t'].get_rotation() % 180 not in (0,): continue
            if _overlap(a['bb'], b['bb']): found.append(f"text '{a['s']}' × text '{b['s']}'")
    # 2. text vs data marks of its own axes (and twins); white in-bar labels excluded
    cache = {}
    for it in items:
        if it['kind'] != 'text' or it['ax'] is None: continue
        col = it['t'].get_color()
        if col in ('white', 'w', '#ffffff', (1.0, 1.0, 1.0), (1.0, 1.0, 1.0, 1.0)) or it['t'].get_gid() == 'inbar': continue
        ax = it['ax']
        if id(ax) not in cache: cache[id(ax)] = _marks(ax)
        for h in _hits(it['bb'], cache[id(ax)]): found.append(f"text '{it['s']}' × {h}")
    # 3. legend box vs data marks and vs texts outside the legend
    for ax in _all_axes(fig):
        lg = ax.get_legend()
        if lg is None: continue
        if id(ax) not in cache: cache[id(ax)] = _marks(ax)
        handles = getattr(lg, 'legend_handles', None) or getattr(lg, 'legendHandles', [])
        parts = [(f"legend text '{t.get_text()[:24]}'", t.get_window_extent(r)) for t in lg.get_texts()]
        for h in handles:
            try: parts.append(('legend handle', h.get_window_extent(r)))
            except Exception: pass
        for name, bb in parts:
            if bb.width <= 0 or bb.height <= 0: continue
            for h in _hits(bb, cache[id(ax)]): found.append(f"{name} × {h}")
            if name == 'legend handle':
                for it in items:
                    if it['grp'] is lg or it['kind'] == 'tick': continue
                    if _overlap(bb, it['bb']): found.append(f"{name} × text '{it['s']}'")
    # 4. inset axes vs parent's marks and texts
    for ax in fig.axes:
        for ins in getattr(ax, 'child_axes', []):
            bb = ins.get_tightbbox(r)
            if bb is None: continue
            if id(ax) not in cache: cache[id(ax)] = _marks(ax)
            for h in _hits(bb, cache[id(ax)]): found.append(f"inset × {h}")
            for it in items:
                if it['ax'] is ins or it['kind'] == 'tick' or it['ax'] is None: continue
                if it['ax'] is ax and _overlap(bb, it['bb']): found.append(f"inset × text '{it['s']}'")
    seen = set(); uniq = []
    for f in found:
        if f not in seen: seen.add(f); uniq.append(f)
    return uniq
