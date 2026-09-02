"""HTML 报告生成器 — 生成独立 HTML 文件，复用 Web UI 暗色主题样式"""

from datetime import datetime
from html import escape


def _sim_class(similarity):
    pct = round(similarity * 100)
    if pct >= 90:
        return 'high'
    if pct >= 75:
        return 'medium'
    return 'low'


def _gauge_class(pct):
    if pct >= 30:
        return 'high'
    if pct >= 10:
        return 'medium'
    return 'low'


def _format_chars(chars):
    if not chars:
        return '0'
    if chars >= 10000:
        return f'{chars / 10000:.1f}万'
    if chars >= 1000:
        return f'{chars / 1000:.1f}k'
    return str(chars)


CSS = """:root{--bg-deep:#131418;--bg-default:#1a1b23;--bg-surface:#22232b;--bg-surface-hover:#2a2b35;--bg-elevated:#2c2d38;--text-primary:#e8e8ed;--text-secondary:#9a9aa3;--text-tertiary:#5c5c66;--accent-blue:#4a9eff;--accent-blue-hover:#3a8eef;--accent-amber:#f0c040;--accent-amber-bg:rgba(240,192,64,0.12);--green:#3dd68c;--green-bg:rgba(61,214,140,0.12);--red:#f04a4a;--red-bg:rgba(240,74,74,0.12);--amber:#f0c040;--amber-bg:rgba(240,192,64,0.12);--border:rgba(255,255,255,0.06);--border-strong:rgba(255,255,255,0.1);--radius-sm:6px;--radius-md:10px;--radius-lg:14px;--radius-xl:18px;--space-xs:4px;--space-sm:8px;--space-md:16px;--space-lg:24px;--space-xl:32px;--space-2xl:48px;--font-ui:-apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI",Roboto,"Helvetica Neue",sans-serif;--font-mono:"SF Mono","JetBrains Mono","Fira Code",monospace}
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--font-ui);background:var(--bg-deep);color:var(--text-primary);line-height:1.6;min-height:100vh;-webkit-font-smoothing:antialiased}
.header{background:var(--bg-default);border-bottom:1px solid var(--border);position:sticky;top:0;z-index:100;backdrop-filter:blur(12px)}
.header-inner{max-width:1200px;margin:0 auto;padding:var(--space-md) var(--space-lg);display:flex;align-items:center;justify-content:space-between}
.brand{display:flex;align-items:center;gap:var(--space-sm)}
.version-badge{font-size:10px;font-weight:700;color:var(--accent-blue);background:rgba(74,158,255,0.15);padding:2px 6px;border-radius:4px;letter-spacing:0.05em}
.brand-icon{width:22px;height:22px;color:var(--accent-blue)}
.brand-text{font-size:17px;font-weight:600}
.main{max-width:1200px;margin:0 auto;padding:var(--space-2xl) var(--space-lg)}
.section-title{text-align:center;margin-bottom:var(--space-xl)}
.section-title h2{font-size:24px;font-weight:700;letter-spacing:-0.02em;margin-bottom:var(--space-xs)}
.section-title p{font-size:14px;color:var(--text-secondary)}
.filter-summary{background:var(--bg-default);border:1px solid var(--border);border-radius:var(--radius-lg);padding:var(--space-lg);margin-bottom:var(--space-xl)}
.filter-summary h3{font-size:16px;font-weight:600;margin-bottom:var(--space-xs)}
.filter-subtitle{font-size:13px;color:var(--text-secondary);margin-bottom:var(--space-md)}
.filter-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:var(--space-md)}
.filter-item{background:var(--bg-surface);border-radius:var(--radius-md);padding:var(--space-md)}
.filter-cat-label{font-size:12px;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:var(--space-xs)}
.filter-count{font-size:20px;font-weight:700;color:var(--accent-amber)}
.filter-samples{margin-top:var(--space-sm);font-size:12px;color:var(--text-tertiary);line-height:1.5}
h3{font-size:18px;font-weight:600;margin-bottom:var(--space-md)}
.summary-cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:var(--space-md);margin-bottom:var(--space-xl)}
.result-card{background:var(--bg-default);border:1px solid var(--border);border-radius:var(--radius-lg);padding:var(--space-lg)}
.result-card.active{border-color:var(--accent-blue);box-shadow:0 0 0 1px var(--accent-blue)}
.card-header{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:var(--space-md);gap:var(--space-sm)}
.card-pair-name{font-size:14px;font-weight:600;line-height:1.3}
.card-severity{font-size:11px;font-weight:600;padding:3px 8px;border-radius:20px;flex-shrink:0}
.severity-high{background:var(--red-bg);color:var(--red)}
.severity-medium{background:var(--amber-bg);color:var(--amber)}
.severity-low{background:var(--green-bg);color:var(--green)}
.card-pct{font-size:48px;font-weight:700;letter-spacing:-0.03em;line-height:1;margin-bottom:var(--space-sm)}
.card-meta{font-size:12px;color:var(--text-tertiary)}
.gauge-bar{height:4px;background:var(--bg-surface);border-radius:2px;margin-top:var(--space-md);overflow:hidden}
.gauge-fill{height:100%;border-radius:2px}
.gauge-fill.high{background:var(--red)}
.gauge-fill.medium{background:var(--amber)}
.gauge-fill.low{background:var(--green)}
.detail-section{margin-bottom:var(--space-xl)}
.detail-tabs{display:flex;gap:var(--space-xs);margin-bottom:var(--space-md);overflow-x:auto}
.detail-tab{padding:8px 16px;font-size:13px;font-weight:500;background:var(--bg-default);border:1px solid var(--border);border-radius:var(--radius-sm);color:var(--text-secondary);white-space:nowrap}
.detail-tab.active{background:var(--bg-surface);color:var(--text-primary);border-color:var(--accent-blue)}
.detail-content{background:var(--bg-default);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden}
.segment-card{padding:var(--space-lg);border-bottom:1px solid var(--border)}
.segment-card:last-child{border-bottom:none}
.segment-header{display:flex;align-items:center;gap:var(--space-sm);margin-bottom:var(--space-md);flex-wrap:wrap}
.segment-id{font-size:11px;font-weight:600;color:var(--accent-blue);background:rgba(74,158,255,0.12);padding:2px 8px;border-radius:20px}
.segment-similarity{font-size:12px;font-weight:600;padding:2px 8px;border-radius:20px}
.similarity-high{background:var(--red-bg);color:var(--red)}
.similarity-medium{background:var(--amber-bg);color:var(--amber)}
.similarity-low{background:var(--green-bg);color:var(--green)}
.segment-compare{display:grid;grid-template-columns:1fr 1fr;gap:var(--space-md)}
@media(max-width:640px){.segment-compare{grid-template-columns:1fr}}
.segment-panel{background:var(--bg-surface);border-radius:var(--radius-md);padding:var(--space-md)}
.segment-panel-label{font-size:11px;font-weight:600;color:var(--text-tertiary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:var(--space-sm)}
.segment-panel-text{font-size:12px;line-height:1.7;color:var(--text-secondary);font-family:var(--font-mono);white-space:pre-wrap;word-break:break-all}
.segment-badge{display:inline-flex;align-items:center;padding:2px 10px;border-radius:4px;font-size:11px;font-weight:600;margin-left:var(--space-sm)}
.badge-compliance{background:var(--green-bg);color:var(--green);border:1px solid rgba(61,214,140,0.3)}
.badge-duplication{background:var(--red-bg);color:var(--red);border:1px solid rgba(240,74,74,0.3)}
.segment-compliance{border-left:3px solid var(--green)}
.segment-reason{padding:var(--space-xs) var(--space-sm);margin-bottom:var(--space-xs);background:var(--bg-surface);border-radius:var(--radius-sm);font-size:12px;color:var(--text-secondary)}
.footer{max-width:1200px;margin:0 auto;padding:var(--space-lg);text-align:center;display:flex;align-items:center;justify-content:center;gap:var(--space-sm);font-size:12px;color:var(--text-tertiary);border-top:1px solid var(--border)}
"""


def _render_summary_cards(results):
    parts = []
    for r in results:
        ai = r.get('ai_analysis')
        original_pct = r.get('duplicate_percentage', 0)
        adjusted_pct = ai['adjusted_percentage'] if ai else original_pct
        display_pct = adjusted_pct if ai else original_pct
        sev = r.get('severity', {})
        gauge_cls = _gauge_class(display_pct)

        if ai:
            pct_html = (
                f'<div class="card-pct">{adjusted_pct:.1f}%'
                f'<span style="font-size:14px;color:var(--text-tertiary);text-decoration:line-through;margin-left:4px">{original_pct:.1f}%</span>'
                f'</div>'
            )
        else:
            pct_html = f'<div class="card-pct">{original_pct:.1f}%</div>'

        matched = _format_chars(r.get('matched_chars', 0))
        total = _format_chars(r.get('total_tender_chars', 0))
        seg_count = len(r.get('segments', []))
        ai_note = ' · 合规应答已排除' if ai else ''

        parts.append(f'''
    <div class="result-card">
      <div class="card-header">
        <span class="card-pair-name">{escape(r.get('label_a',''))} ↔ {escape(r.get('label_b',''))}</span>
        <span class="card-severity severity-{sev.get('level','low')}">{escape(sev.get('label',''))}</span>
      </div>
      {pct_html}
      <div class="card-meta">匹配 {matched} / {total} 字 · {seg_count} 段{ai_note}</div>
      <div class="gauge-bar"><div class="gauge-fill {gauge_cls}" style="width:{min(display_pct,100):.1f}%"></div></div>
    </div>''')
    return '\n'.join(parts)


def _render_ai_summary(results):
    has_ai = any('ai_analysis' in r for r in results)
    has_warning = any('ai_warning' in r for r in results)

    if not has_ai and not has_warning:
        return ''

    items = []
    for r in results:
        ai = r.get('ai_analysis')
        if ai:
            reduction = ai['original_percentage'] - ai['adjusted_percentage']
            items.append(f'''
      <div class="filter-item">
        <div class="filter-cat-label">{escape(r.get('label_a',''))} ↔ {escape(r.get('label_b',''))}</div>
        <div class="filter-count">原始 {ai['original_percentage']:.1f}% → 调整后 {ai['adjusted_percentage']:.1f}%</div>
        <div class="filter-samples">
          <div style="margin-bottom:4px">合规应答：{ai['compliance_chars']} 字</div>
          <div style="margin-bottom:4px">实际重复：{ai['actual_duplication_chars']} 字</div>
          <div style="color:var(--green);margin-top:6px">{'排除合规应答后降低 ' + f'{reduction:.1f}%' if reduction > 0 else '未发现合规应答'}</div>
        </div>
        <div style="margin-top:6px;font-size:12px;color:var(--text-secondary)">{escape(ai.get('summary',''))}</div>
      </div>''')
        elif 'ai_warning' in r:
            items.append(f'''
      <div class="filter-item" style="border-color:var(--amber)">
        <div class="filter-cat-label" style="color:var(--accent-amber)">{escape(r.get('label_a',''))} ↔ {escape(r.get('label_b',''))} — AI 分析未完成</div>
        <div class="filter-samples">{escape(r['ai_warning'])}</div>
      </div>''')

    return f'''
    <div class="filter-summary">
      <h3>AI 分析摘要</h3>
      <p class="filter-subtitle">区分合规应答（必要重复）与实际重复（不必要照搬）</p>
      <div class="filter-grid">
        {''.join(items)}
      </div>
    </div>'''


def _render_detail_section(results):
    tabs = []
    for i, r in enumerate(results):
        active = 'active' if i == 0 else ''
        tabs.append(
            f'<button class="detail-tab {active}">{escape(r.get("label_a","A"))} ↔ {escape(r.get("label_b","B"))}</button>'
        )

    panels = []
    for i, r in enumerate(results):
        segments = r.get('segments', [])
        ai_analysis = r.get('ai_analysis')
        seg_cls_map = {}
        if ai_analysis:
            for sc in ai_analysis.get('segment_classifications', []):
                seg_cls_map[sc['segment_id']] = sc

        if not segments:
            panels.append(
                f'<div class="detail-panel" data-pair="{i}">'
                '<div class="segment-card" style="text-align:center;padding:var(--space-2xl);color:var(--text-tertiary)">未发现匹配的重复段落</div>'
                '</div>'
            )
            continue

        seg_cards = []
        for seg in segments:
            sim_pct = round(seg.get('similarity', 0) * 100)
            sim_cls = _sim_class(seg.get('similarity', 0))
            seg_id = seg.get('id', 0)

            sc = seg_cls_map.get(seg_id)
            is_compliance = sc and sc['classification'] == 'compliance_response'
            badge = ''
            if sc:
                if is_compliance:
                    badge = '<span class="segment-badge badge-compliance">合规应答</span>'
                else:
                    badge = '<span class="segment-badge badge-duplication">实际重复</span>'
            reason = f'<div class="segment-reason">{escape(sc["reason"])}</div>' if sc else ''
            compliance_cls = 'segment-compliance' if is_compliance else ''
            sim_display_cls = 'low' if is_compliance else sim_cls

            seg_cards.append(f'''
        <div class="segment-card {compliance_cls}">
          <div class="segment-header">
            <span class="segment-id">#{seg_id + 1}</span>
            {badge}
            <span class="segment-similarity similarity-{sim_display_cls}">相似度 {sim_pct}%</span>
          </div>
          {reason}
          <div class="segment-compare">
            <div class="segment-panel">
              <div class="segment-panel-label">{escape(r.get("label_a","文档 A"))}</div>
              <div class="segment-panel-text">{escape(seg.get("tender_text",""))}</div>
            </div>
            <div class="segment-panel">
              <div class="segment-panel-label">{escape(r.get("label_b","文档 B"))}</div>
              <div class="segment-panel-text">{escape(seg.get("bid_text",""))}</div>
            </div>
          </div>
        </div>''')

        panels.append(
            f'<div class="detail-panel" data-pair="{i}" style="display:{"block" if i==0 else "none"}">'
            f'{"".join(seg_cards)}'
            '</div>'
        )

    return f'''
    <div class="detail-section">
      <div class="detail-tabs">{''.join(tabs)}</div>
      <div class="detail-content">{''.join(panels)}</div>
    </div>
    <script>
    document.querySelectorAll('.detail-tab').forEach(function(tab){{
      tab.addEventListener('click',function(){{
        document.querySelectorAll('.detail-tab').forEach(function(t){{t.classList.remove('active')}});
        tab.classList.add('active');
        var idx=tab.dataset.pair;
        document.querySelectorAll('.detail-panel').forEach(function(p){{
          p.style.display=(p.dataset.pair===idx)?'block':'none';
        }});
      }});
    }});
    </script>'''


def generate_html_report(results, mode, output_path):
    """Generate a standalone HTML report file.

    Args:
        results: list of result dicts (same format as API response)
        mode: 'fast' or 'ai'
        output_path: file path to write the HTML report
    """
    mode_label = 'AI 辅助' if mode == 'ai' else '快速'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    ai_summary = _render_ai_summary(results) if mode == 'ai' else ''
    summary_cards = _render_summary_cards(results)
    detail_section = _render_detail_section(results)

    pair_count = len(results)
    avg_pct = sum(r.get('duplicate_percentage', 0) for r in results) / max(pair_count, 1)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>文档重复度比对报告 — {now}</title>
  <style>{CSS}</style>
</head>
<body>
  <header class="header">
    <div class="header-inner">
      <div class="brand">
        <svg class="brand-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
          <polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/>
          <line x1="16" y1="17" x2="8" y2="17"/>
          <polyline points="10 9 9 9 8 9"/>
        </svg>
        <span class="brand-text">文档重复度比对</span>
        <span class="version-badge">v1.2</span>
      </div>
      <span style="font-size:13px;color:var(--text-secondary)">模式: {mode_label}</span>
    </div>
  </header>

  <main class="main">
    <div class="section-title">
      <h2>比对结果报告</h2>
      <p>生成时间: {now} · 共 {pair_count} 对文档 · 平均重复率 {avg_pct:.1f}%</p>
    </div>

    {ai_summary}

    <h3>比对结果摘要</h3>
    <div class="summary-cards">
      {summary_cards}
    </div>

    {detail_section}
  </main>

  <footer class="footer">
    <span>DocDiff v1.2</span>
    <span>·</span>
    <span>文档重复度智能比对 · agent-compose 集成版</span>
    <span>·</span>
    <span>{now}</span>
  </footer>
</body>
</html>'''

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
