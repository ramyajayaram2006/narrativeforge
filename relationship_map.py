"""
relationship_map.py
───────────────────
Renders an interactive D3.js force-directed character relationship graph
inside a Streamlit app via st.components.v1.html().

Usage (called from workspace.py sidebar):
    from relationship_map import render_relationship_map
    render_relationship_map(characters, scenes)
"""

import json
import streamlit.components.v1 as components


def _build_graph(characters, scenes):
    """
    Build nodes + edges from character and scene data.

    Nodes  — one per character, sized by mention count across scenes.
    Edges  — two characters share an edge if they appear in the same scene.
             edge weight = number of shared scenes.
    """
    if not characters:
        return {"nodes": [], "links": []}

    role_colors = {
        "protagonist": "#4ade80",
        "antagonist":  "#f87171",
        "mentor":      "#fbbf24",
        "ally":        "#60a5fa",
        "comic relief":"#c4b5fd",
        "love interest":"#f9a8d4",
        "sidekick":    "#67e8f9",
    }
    default_color = "#86efac"

    nodes = []
    for c in characters:
        role_key = (c.get("role") or "").lower().strip()
        color    = role_colors.get(role_key, default_color)

        scene_count = sum(
            1 for sc in (scenes or [])
            if c["name"] in (sc.get("characters") or [])
        )
        nodes.append({
            "id":          c["id"],
            "name":        c["name"],
            "role":        c.get("role") or "Unknown",
            "description": (c.get("description") or "")[:120],
            "voice":       c.get("speaking_style") or "",
            "color":       color,
            "scenes":      scene_count,
            "radius":      max(22, min(44, 22 + scene_count * 5)),
        })

    link_weight = {}
    for sc in (scenes or []):
        members = sc.get("characters") or []
        char_ids = {c["id"]: c["name"] for c in characters if c["name"] in members}
        ids = list(char_ids.keys())
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                key = (min(ids[i], ids[j]), max(ids[i], ids[j]))
                link_weight[key] = link_weight.get(key, 0) + 1

    links = [{"source": s, "target": t, "weight": w}
             for (s, t), w in link_weight.items()]

    return {"nodes": nodes, "links": links}


# BUG FIX 1: Template was written with {{ and }} (Python .format() escaping) but
# render_relationship_map() was calling .replace("{graph_json}", ...) instead of
# .format(graph_json=...). This caused the browser to receive literal {{ and }}
# in the JavaScript, which is a syntax error. ALL curly braces in JS/CSS use
# doubled {{ }} so .format() converts them correctly to single { }.
#
# BUG FIX 2: translate(${d.x},${d.y)} had the closing ) INSIDE the template
# expression: ${{d.y)}} → ${d.y)}  (wrong).
# Fixed to ${{d.y}}) → ${d.y})     (correct).

_D3_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8"/>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background: #080f08;
    font-family: 'Syne', system-ui, sans-serif;
    overflow: hidden;
  }}
  canvas {{ display: block; }}
  svg {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; }}
  #tooltip {{
    position: absolute; pointer-events: none;
    background: rgba(13,26,13,0.95);
    border: 1px solid rgba(74,222,128,0.3);
    border-radius: 10px;
    padding: 12px 16px;
    max-width: 220px;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    display: none;
    backdrop-filter: blur(12px);
  }}
  #tooltip .t-name  {{ font-size:0.9rem; font-weight:700; color:#f0fdf4; margin-bottom:4px; }}
  #tooltip .t-role  {{ font-size:0.65rem; font-weight:700; letter-spacing:0.1em; text-transform:uppercase; color:#4ade80; margin-bottom:7px; }}
  #tooltip .t-desc  {{ font-size:0.78rem; color:#86efac; line-height:1.5; font-style:italic; }}
  #tooltip .t-voice {{ font-size:0.7rem; color:rgba(134,239,172,0.5); margin-top:5px; }}
  #tooltip .t-scenes{{ font-size:0.68rem; color:rgba(134,239,172,0.4); margin-top:4px; font-family:'DM Mono',monospace; }}
  #legend {{
    position: absolute; bottom: 16px; left: 16px;
    background: rgba(13,26,13,0.85);
    border: 1px solid rgba(74,222,128,0.12);
    border-radius: 10px;
    padding: 10px 14px;
    backdrop-filter: blur(10px);
  }}
  #legend .l-title {{ font-size:0.6rem; font-weight:700; letter-spacing:0.14em; text-transform:uppercase; color:rgba(134,239,172,0.45); margin-bottom:8px; }}
  .l-item {{ display:flex; align-items:center; gap:7px; margin:4px 0; }}
  .l-dot  {{ width:10px; height:10px; border-radius:50%; flex-shrink:0; }}
  .l-lbl  {{ font-size:0.7rem; color:#86efac; }}
  #empty {{
    position:absolute; inset:0; display:flex; flex-direction:column;
    align-items:center; justify-content:center; gap:12px;
    color: rgba(134,239,172,0.3);
    font-size: 0.85rem; letter-spacing:0.06em; text-transform:uppercase;
  }}
  #empty .e-icon {{ font-size:2.5rem; opacity:0.4; }}
  #controls {{
    position: absolute; top:12px; right:12px;
    display:flex; gap:6px;
  }}
  .ctrl-btn {{
    background: rgba(13,26,13,0.85);
    border: 1px solid rgba(74,222,128,0.18);
    color: #4ade80; border-radius:7px;
    padding: 6px 12px; font-size:0.72rem; font-weight:600;
    cursor:pointer; transition:all 0.18s;
    letter-spacing:0.04em;
    font-family: system-ui, sans-serif;
  }}
  .ctrl-btn:hover {{ background:rgba(74,222,128,0.12); border-color:rgba(74,222,128,0.4); }}
</style>
</head>
<body>
<div id="tooltip">
  <div class="t-name" id="tt-name"></div>
  <div class="t-role" id="tt-role"></div>
  <div class="t-desc" id="tt-desc"></div>
  <div class="t-voice" id="tt-voice"></div>
  <div class="t-scenes" id="tt-scenes"></div>
</div>

<div id="controls">
  <button class="ctrl-btn" onclick="resetZoom()">&#8857; Reset</button>
  <button class="ctrl-btn" onclick="toggleLabels()">&#127991; Labels</button>
</div>
<div id="legend"></div>

<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const graphData = {graph_json};
const W = window.innerWidth;
const H = window.innerHeight;

const ROLE_COLORS = {{
  "protagonist": "#4ade80", "antagonist": "#f87171",
  "mentor": "#fbbf24",      "ally": "#60a5fa",
  "comic relief": "#c4b5fd","love interest": "#f9a8d4",
  "sidekick": "#67e8f9",    "other": "#86efac"
}};

if (graphData.nodes.length === 0) {{
  document.body.innerHTML += `<div id="empty"><div class="e-icon">&#128101;</div><div>Add characters to see the relationship map</div></div>`;
}} else {{
  const roles = [...new Set(graphData.nodes.map(n => n.role.toLowerCase()))];
  const legendEl = document.getElementById('legend');
  legendEl.innerHTML = '<div class="l-title">Character Roles</div>';
  roles.forEach(r => {{
    const color = ROLE_COLORS[r] || ROLE_COLORS["other"];
    legendEl.innerHTML += `<div class="l-item"><div class="l-dot" style="background:${{color}};box-shadow:0 0 6px ${{color}}44"></div><div class="l-lbl">${{r}}</div></div>`;
  }});
  buildGraph();
}}

let showLabels = true;
let labelSel;

function toggleLabels() {{
  showLabels = !showLabels;
  if (labelSel) labelSel.attr('opacity', showLabels ? 1 : 0);
}}

function resetZoom() {{
  svg.transition().duration(500).call(zoom.transform, d3.zoomIdentity);
}}

let svg, zoom;

function buildGraph() {{
  svg = d3.select('body').append('svg');
  const defs = svg.append('defs');

  const filter = defs.append('filter').attr('id','glow');
  filter.append('feGaussianBlur').attr('stdDeviation','3').attr('result','blur');
  const feMerge = filter.append('feMerge');
  feMerge.append('feMergeNode').attr('in','blur');
  feMerge.append('feMergeNode').attr('in','SourceGraphic');

  graphData.nodes.forEach(n => {{
    const grad = defs.append('radialGradient')
      .attr('id', `grad_${{n.id}}`)
      .attr('cx','35%').attr('cy','35%');
    grad.append('stop').attr('offset','0%')
      .attr('stop-color', n.color).attr('stop-opacity','0.9');
    grad.append('stop').attr('offset','100%')
      .attr('stop-color', n.color).attr('stop-opacity','0.35');
  }});

  const g = svg.append('g');

  zoom = d3.zoom()
    .scaleExtent([0.3, 3])
    .on('zoom', e => g.attr('transform', e.transform));
  svg.call(zoom);

  const simulation = d3.forceSimulation(graphData.nodes)
    .force('link', d3.forceLink(graphData.links)
      .id(d => d.id)
      .distance(d => 120 + (d.weight || 1) * 20)
      .strength(0.5))
    .force('charge', d3.forceManyBody().strength(-320))
    .force('center', d3.forceCenter(W / 2, H / 2))
    .force('collision', d3.forceCollide(d => d.radius + 14));

  const link = g.append('g').selectAll('line')
    .data(graphData.links).enter().append('line')
    .attr('stroke', 'rgba(74,222,128,0.22)')
    .attr('stroke-width', d => Math.min(5, 1 + (d.weight || 1)))
    .attr('stroke-linecap', 'round');

  const edgeLabel = g.append('g').selectAll('text')
    .data(graphData.links.filter(l => (l.weight || 1) > 1))
    .enter().append('text')
    .attr('fill', 'rgba(134,239,172,0.35)')
    .attr('font-size', '9px')
    .attr('text-anchor', 'middle')
    .attr('font-family', 'monospace')
    .text(d => `${{d.weight}} scenes`);

  const nodeG = g.append('g').selectAll('g')
    .data(graphData.nodes).enter().append('g')
    .style('cursor','pointer')
    .call(d3.drag()
      .on('start', (e, d) => {{ if (!e.active) simulation.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
      .on('drag',  (e, d) => {{ d.fx=e.x; d.fy=e.y; }})
      .on('end',   (e, d) => {{ if (!e.active) simulation.alphaTarget(0); d.fx=null; d.fy=null; }}));

  nodeG.append('circle')
    .attr('r', d => d.radius + 6)
    .attr('fill', 'none')
    .attr('stroke', d => d.color)
    .attr('stroke-width', 1)
    .attr('stroke-opacity', 0.18)
    .attr('filter', 'url(#glow)');

  nodeG.append('circle')
    .attr('r', d => d.radius)
    .attr('fill', d => `url(#grad_${{d.id}})`)
    .attr('stroke', d => d.color)
    .attr('stroke-width', 1.5)
    .attr('stroke-opacity', 0.6)
    .attr('filter', 'url(#glow)')
    .on('mouseover', function(e, d) {{
      d3.select(this).transition().duration(160)
        .attr('r', d.radius + 5)
        .attr('stroke-opacity', 1);
      const tt = document.getElementById('tooltip');
      document.getElementById('tt-name').textContent  = d.name;
      document.getElementById('tt-role').textContent  = d.role;
      document.getElementById('tt-desc').textContent  = d.description || '—';
      document.getElementById('tt-voice').textContent = d.voice ? `"${{d.voice}}"` : '';
      document.getElementById('tt-scenes').textContent = `Appears in ${{d.scenes}} scene${{d.scenes !== 1 ? 's' : ''}}`;
      tt.style.display = 'block';
      moveTip(e);
    }})
    .on('mousemove', moveTip)
    .on('mouseout', function(e, d) {{
      d3.select(this).transition().duration(160)
        .attr('r', d.radius)
        .attr('stroke-opacity', 0.6);
      document.getElementById('tooltip').style.display = 'none';
    }});

  nodeG.append('text')
    .attr('text-anchor','middle').attr('dominant-baseline','central')
    .attr('fill','rgba(6,12,6,0.85)').attr('font-weight','800')
    .attr('font-size', d => d.radius * 0.55)
    .attr('font-family','Syne,system-ui,sans-serif')
    .attr('pointer-events','none')
    .text(d => d.name.split(' ').map(w=>w[0]).join('').substring(0,2).toUpperCase());

  labelSel = nodeG.append('text')
    .attr('text-anchor','middle')
    .attr('dy', d => d.radius + 14)
    .attr('fill','#86efac')
    .attr('font-size','0.7rem')
    .attr('font-weight','600')
    .attr('font-family','Syne,system-ui,sans-serif')
    .attr('pointer-events','none')
    .text(d => d.name);

  // BUG FIX 2: translate() paren was inside the template expression — fixed.
  simulation.on('tick', () => {{
    link
      .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
      .attr('x2', d => d.target.x).attr('y2', d => d.target.y);
    edgeLabel
      .attr('x', d => (d.source.x + d.target.x) / 2)
      .attr('y', d => (d.source.y + d.target.y) / 2 - 4);
    nodeG.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
  }});

  setInterval(() => {{
    nodeG.selectAll('circle:first-child')
      .transition().duration(1200)
      .attr('stroke-opacity', 0.25)
      .transition().duration(1200)
      .attr('stroke-opacity', 0.1);
  }}, 2400);
}}

function moveTip(e) {{
  const tt = document.getElementById('tooltip');
  const x = e.clientX + 14;
  const y = e.clientY - 14;
  tt.style.left = (x + 230 > W ? x - 244 : x) + 'px';
  tt.style.top  = (y + 150 > H ? y - 150 : y) + 'px';
}}
</script>
</body>
</html>
"""


def render_relationship_map(characters: list, scenes: list, height: int = 480):
    """
    Renders the D3 force-directed character relationship graph in Streamlit.

    Parameters
    ----------
    characters : list  — from database.load_characters()
    scenes     : list  — from database.load_scenes()
    height     : int   — iframe height in pixels
    """
    graph = _build_graph(characters, scenes)
    # BUG FIX 1: Was .replace("{graph_json}", json.dumps(graph)) which left
    # all {{ and }} as literal double-braces in JavaScript — a syntax error.
    # .format() correctly converts {{ → { and }} → } throughout the template,
    # while substituting {graph_json} with the actual data.
    html = _D3_TEMPLATE.format(graph_json=json.dumps(graph))
    components.html(html, height=height, scrolling=False)
