"""
LogiFast CR — Optimizador Cross Docking
Streamlit App  |  UCR Ingeniería Industrial  |  I Semestre 2026
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import math, io, json
from itertools import permutations

from solver import (
    parse_ts_file, solve, build_transfer_table,
    storage_analysis, T_LOAD, T_TRANSFER, T_CHANGE,
    compute_makespan, solve_product_flow
)

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LogiFast CR — Cross Docking Optimizer",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
  h1,h2,h3 { font-family: 'Space Mono', monospace; }
  .metric-card {
    background: linear-gradient(135deg, #0f2027, #203a43, #2c5364);
    border-radius: 12px; padding: 1.2rem 1.5rem;
    color: white; margin-bottom: 0.5rem;
    border-left: 4px solid #00e5ff;
  }
  .metric-card .label { font-size: 0.75rem; opacity: 0.7; text-transform: uppercase; letter-spacing: 1px; }
  .metric-card .value { font-size: 2rem; font-family: 'Space Mono', monospace; font-weight: 700; color: #00e5ff; }
  .metric-card .sub   { font-size: 0.8rem; opacity: 0.6; margin-top: 2px; }
  .section-header {
    border-bottom: 2px solid #00e5ff; padding-bottom: 6px;
    margin: 1.5rem 0 1rem; font-size: 1.05rem; font-family: 'Space Mono', monospace;
    color: #203a43;
  }
  .stAlert { border-radius: 8px; }
  .truck-badge {
    display:inline-block; padding:2px 10px; border-radius:20px;
    font-family:'Space Mono',monospace; font-size:0.8rem; font-weight:700;
    margin:2px;
  }
  .badge-in  { background:#003566; color:#00b4d8; }
  .badge-out { background:#370617; color:#f48c06; }
</style>
""", unsafe_allow_html=True)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/1/1e/University_of_Costa_Rica_seal.svg/240px-University_of_Costa_Rica_seal.svg.png", width=80)
    st.markdown("## 🚛 LogiFast CR\n**Cross Docking Optimizer**")
    st.markdown("---")
    st.markdown("**UCR — Ing. Industrial**\nOptimización • I Sem 2026")
    st.markdown("---")

    input_method = st.radio("Fuente de datos", ["📂 Archivo TS (upload)", "✏️ Pegar texto TS", "🔧 Datos de ejemplo (TS5)"])

    if input_method == "📂 Archivo TS (upload)":
        uploaded = st.file_uploader("Subir archivo .txt", type=["txt"])
        raw_text = uploaded.read().decode() if uploaded else None
    elif input_method == "✏️ Pegar texto TS":
        raw_text = st.text_area("Pegar contenido del archivo TS", height=200)
        raw_text = raw_text if raw_text.strip() else None
    else:
        raw_text = "i\t5\t\to\t3\t\tn\t8\t\tr\t1\t1\t170r\t2\t1\t6r\t2\t2\t6r\t2\t3\t19r\t2\t4\t50r\t2\t5\t38r\t2\t6\t6r\t2\t7\t19r\t2\t8\t56r\t3\t1\t49r\t3\t2\t31r\t3\t3\t60r\t3\t6\t12r\t3\t7\t37r\t3\t8\t31r\t4\t5\t143r\t4\t7\t47r\t5\t4\t58r\t5\t5\t36r\t5\t7\t72r\t5\t8\t14s\t1\t1\t75s\t1\t2\t12s\t1\t3\t59s\t1\t6\t9s\t1\t7\t98s\t1\t8\t40s\t2\t1\t150s\t2\t5\t217s\t3\t2\t25s\t3\t3\t20s\t3\t4\t108s\t3\t6\t9s\t3\t7\t77s\t3\t8\t61"

    st.markdown("---")
    st.markdown("**Parámetros operativos**")
    t_load     = st.number_input("⏱ Carga/descarga (min/unidad)", value=T_LOAD, min_value=1)
    t_transfer = st.number_input("🔄 Traslado interno (min/lote)", value=T_TRANSFER, min_value=1)
    t_change   = st.number_input("🔁 Cambio de camión (min)", value=T_CHANGE, min_value=0)

    run_btn = st.button("🚀 Optimizar", use_container_width=True, type="primary")


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 🚛 LogiFast CR — Optimización Cross Docking")
st.caption("Programación Entera Mixta (MIP) | Universidad de Costa Rica — I Semestre 2026")

tab_main, tab_model, tab_analysis, tab_code = st.tabs([
    "📊 Resultados", "📐 Modelo MIP", "📈 Análisis", "💻 Código Python"
])

# ─── Run solver ───────────────────────────────────────────────────────────────
result = None
data   = None
sa     = None

if raw_text and run_btn:
    with st.spinner("Resolviendo..."):
        try:
            data   = parse_ts_file(raw_text)
            result = solve(data)
            sa     = storage_analysis(result)
            st.session_state['result'] = result
            st.session_state['data']   = data
            st.session_state['sa']     = sa
        except Exception as e:
            st.error(f"Error al procesar datos: {e}")

elif 'result' in st.session_state:
    result = st.session_state['result']
    data   = st.session_state['data']
    sa     = st.session_state['sa']


# ─── TAB 1: Results ───────────────────────────────────────────────────────────
with tab_main:
    if result is None:
        st.info("👈 Selecciona una fuente de datos y presiona **Optimizar**.")
        # Show example data description
        with st.expander("ℹ️ Formato del archivo TS"):
            st.code("""i  5        ← número de camiones de entrada
o  3        ← número de camiones de salida
n  8        ← número de tipos de producto
r  1  1  170  ← camión entrada 1, producto 1, 170 unidades
r  2  1  6
...
s  1  1  75   ← camión salida 1, producto 1, 75 unidades
s  1  2  12
...
""")
    else:
        # ── KPI Cards ────────────────────────────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        ms_h = result['makespan'] // 60
        ms_m = result['makespan'] % 60

        with c1:
            st.markdown(f"""<div class="metric-card">
              <div class="label">⏱ Makespan Óptimo</div>
              <div class="value">{result['makespan']}</div>
              <div class="sub">minutos ({ms_h}h {ms_m}m)</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            n_combos = result['n_combos']
            st.markdown(f"""<div class="metric-card">
              <div class="label">🔍 Combinaciones evaluadas</div>
              <div class="value">{n_combos:,}</div>
              <div class="sub">{data['I']}! × {data['O']}! secuencias</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            st.markdown(f"""<div class="metric-card">
              <div class="label">✅ Transferencia directa</div>
              <div class="value">{sa['pct_direct']}%</div>
              <div class="sub">{sa['direct']} unidades directas</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            total_units = sum(result['U'].values())
            st.markdown(f"""<div class="metric-card">
              <div class="label">📦 Total unidades</div>
              <div class="value">{total_units:,}</div>
              <div class="sub">{data['I']} entrada | {data['O']} salida</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("")

        # ── Optimal Sequence ─────────────────────────────────────────────────
        col_seq, col_trucks = st.columns([1, 1])
        with col_seq:
            st.markdown('<div class="section-header">🏆 Secuencia Óptima</div>', unsafe_allow_html=True)
            in_seq  = " → ".join([f"R{i}" for i in result['inbound_order']])
            out_seq = " → ".join([f"S{j}" for j in result['outbound_order']])
            st.markdown(f"**Camiones Entrada:** `{in_seq}`")
            st.markdown(f"**Camiones Salida:** `{out_seq}`")

        with col_trucks:
            st.markdown('<div class="section-header">🚚 Tiempos por Camión</div>', unsafe_allow_html=True)
            truck_rows = []
            for i in result['inbound_order']:
                truck_rows.append({
                    'Camión': f"Entrada R{i}", 'Tipo': '↓ Descarga',
                    'Inicio': result['a'][i],
                    'Fin': result['a'][i] + result['U'][i],
                    'Unidades': result['U'][i]
                })
            for j in result['outbound_order']:
                truck_rows.append({
                    'Camión': f"Salida S{j}", 'Tipo': '↑ Carga',
                    'Inicio': sa['start_load'][j],
                    'Fin': result['d'][j],
                    'Unidades': result['D'][j]
                })
            st.dataframe(pd.DataFrame(truck_rows), use_container_width=True, hide_index=True)

        # ── Gantt Chart ───────────────────────────────────────────────────────
        st.markdown('<div class="section-header">📅 Diagrama de Gantt</div>', unsafe_allow_html=True)

        fig = go.Figure()
        colors_in  = px.colors.sequential.Blues[3:]
        colors_out = px.colors.sequential.Oranges[3:]

        for idx, i in enumerate(result['inbound_order']):
            start = result['a'][i]
            end   = result['a'][i] + result['U'][i]
            fig.add_trace(go.Bar(
                x=[end - start], y=[f"Muelle Entrada"],
                base=[start], orientation='h',
                name=f"R{i} ({result['U'][i]} u)",
                marker_color=colors_in[idx % len(colors_in)],
                text=f" R{i} ({result['U'][i]})",
                textposition='inside',
                insidetextanchor='middle',
                hovertemplate=f"Camión Entrada {i}<br>Inicio: {start} min<br>Fin: {end} min<br>Unidades: {result['U'][i]}<extra></extra>"
            ))

        for idx, j in enumerate(result['outbound_order']):
            start = sa['start_load'][j]
            end   = result['d'][j]
            fig.add_trace(go.Bar(
                x=[end - start], y=[f"Muelle Salida"],
                base=[start], orientation='h',
                name=f"S{j} ({result['D'][j]} u)",
                marker_color=colors_out[idx % len(colors_out)],
                text=f" S{j} ({result['D'][j]})",
                textposition='inside',
                insidetextanchor='middle',
                hovertemplate=f"Camión Salida {j}<br>Inicio: {start} min<br>Fin: {end} min<br>Unidades: {result['D'][j]}<extra></extra>"
            ))

        # Makespan line
        fig.add_vline(x=result['makespan'], line_dash="dash", line_color="#ef233c",
                      annotation_text=f"Makespan: {result['makespan']} min",
                      annotation_position="top right")

        fig.update_layout(
            barmode='stack', height=280, showlegend=True,
            plot_bgcolor='#f8f9fa', paper_bgcolor='white',
            xaxis=dict(title='Tiempo (minutos)', gridcolor='#dee2e6'),
            yaxis=dict(title='', categoryorder='array', categoryarray=['Muelle Salida', 'Muelle Entrada']),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            margin=dict(l=10, r=10, t=30, b=10),
            font=dict(family='DM Sans'),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ── Transfer Matrix ────────────────────────────────────────────────────
        st.markdown('<div class="section-header">🔀 Matriz de Transferencia</div>', unsafe_allow_html=True)

        col_mat, col_tbl = st.columns([1, 1])
        with col_mat:
            # Heatmap
            I_list = result['I_list']
            J_list = result['J_list']
            x = result['x']
            K_list = result['K_list']
            mat = [[sum(x.get((i, j, k), 0) for k in K_list) for j in J_list] for i in I_list]
            fig2 = go.Figure(go.Heatmap(
                z=mat,
                x=[f"S{j}" for j in J_list],
                y=[f"R{i}" for i in I_list],
                colorscale='Blues',
                text=[[f"{v}" for v in row] for row in mat],
                texttemplate="%{text}",
                hovertemplate="R%{y} → S%{x}: %{z} unidades<extra></extra>",
            ))
            fig2.update_layout(
                title="Unidades transferidas (entrada → salida)",
                height=300, margin=dict(l=10, r=10, t=40, b=10),
                font=dict(family='DM Sans'),
                yaxis=dict(autorange='reversed')
            )
            st.plotly_chart(fig2, use_container_width=True)

        with col_tbl:
            rows = build_transfer_table(result)
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


# ─── TAB 2: Model ─────────────────────────────────────────────────────────────
with tab_model:
    st.markdown("## 📐 Formulación del Modelo MIP")

    st.markdown("### 1. Decisiones del sistema")
    st.markdown("""
| Tipo de decisión | Descripción |
|---|---|
| Secuencia | ¿En qué orden entran los camiones al muelle de entrada? |
| Secuencia | ¿En qué orden se cargan los camiones de salida? |
| Flujo | ¿Cuántas unidades del producto *k* van del camión de entrada *i* al de salida *j*? |
| Binaria | ¿Hay alguna transferencia entre el camión *i* y el *j*? |
| Ruta | ¿Los productos van directo o pasan por almacenamiento temporal? |
""")

    st.markdown("### 2. Objetivo")
    st.latex(r"\min \; C")
    st.latex(r"C = \text{Makespan} = \max_{j \in J} \; d_j")
    st.info("Se minimiza el tiempo total de operación del almacén (makespan): el momento en que el último camión de salida abandona el muelle.")

    st.markdown("### 3. Variables de Decisión")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Variables Continuas**")
        st.markdown("""
| Variable | Dominio | Descripción |
|---|---|---|
| $C$ | $\\mathbb{R}^+$ | Makespan (objetivo) |
| $a_i$ | $\\mathbb{R}^+$ | Tiempo de llegada al muelle del camión de entrada $i$ |
| $d_j$ | $\\mathbb{R}^+$ | Tiempo de salida del camión $j$ de salida |
| $x_{ijk}$ | $\\mathbb{Z}^+$ | Unidades del producto $k$ de entrada $i$ a salida $j$ |
""")
    with col2:
        st.markdown("**Variables Binarias / Enteras**")
        st.markdown("""
| Variable | Dominio | Descripción |
|---|---|---|
| $\\sigma^r_{ii'}$ | $\\{0,1\\}$ | 1 si camión entrada $i$ precede a $i'$ |
| $\\sigma^s_{jj'}$ | $\\{0,1\\}$ | 1 si camión salida $j$ precede a $j'$ |
| $v_{ij}$ | $\\{0,1\\}$ | 1 si existe alguna transferencia de $i$ a $j$ |
""")

    st.markdown("### 4. Parámetros")
    st.markdown("""
| Parámetro | Valor | Descripción |
|---|---|---|
| $t_{load}$ | 1 min/unidad | Tiempo de carga o descarga por unidad |
| $t_{transfer}$ | 5 min/lote | Tiempo de traslado interno por lote |
| $t_{change}$ | 10 min | Tiempo de cambio entre camiones en muelle |
| $r_{ik}$ | dado | Unidades del producto $k$ en camión de entrada $i$ |
| $s_{jk}$ | dado | Unidades del producto $k$ requeridas por camión de salida $j$ |
""")

    st.markdown("### 5. Restricciones")

    constraints = [
        ("(C1) Makespan",
         r"C \geq d_j \quad \forall j \in J",
         "El makespan es mayor o igual al tiempo de salida de cada camión de salida."),
        ("(C2) Conservación de flujo — entrada",
         r"\sum_{j \in J} x_{ijk} = r_{ik} \quad \forall i \in I, k \in K",
         "Todo lo que llega en el camión de entrada debe ser transferido."),
        ("(C3) Conservación de flujo — salida",
         r"\sum_{i \in I} x_{ijk} = s_{jk} \quad \forall j \in J, k \in K",
         "El camión de salida debe recibir exactamente lo que necesita."),
        ("(C4) Activación de variable $v_{ij}$",
         r"\sum_k x_{ijk} \leq M \cdot v_{ij} \quad \forall i,j",
         "Si hay transferencia de i a j, entonces v_ij = 1."),
        ("(C5-C7) Secuencia de entrada (3 restricciones)",
         r"a_{i'} \geq a_i + U_i \cdot t_{load} + t_{change} - M(1-\sigma^r_{ii'}) \quad \forall i \neq i'",
         "Si el camión i precede a i', el camión i' no puede empezar hasta que i termine y pase el tiempo de cambio."),
        ("(C8) Anti-reflexividad entrada",
         r"\sigma^r_{ii} = 0 \quad \forall i",
         "Ningún camión puede precederse a sí mismo."),
        ("(C9-C11) Secuencia de salida (3 restricciones)",
         r"d_{j'} \geq d_j + t_{change} - M(1-\sigma^s_{jj'}) \quad \forall j \neq j'",
         "Restricción anáfora para el muelle de salida."),
        ("(C12) Anti-reflexividad salida",
         r"\sigma^s_{jj} = 0 \quad \forall j",
         "Ningún camión de salida puede precederse a sí mismo."),
        ("(C13) Sincronización entrada-salida",
         r"d_j \geq a_i + U_i \cdot t_{load} + t_{transfer} - M(1-v_{ij}) \quad \forall i,j",
         "El camión de salida j no puede salir hasta que el camión de entrada i haya terminado de descargar y se realice el traslado interno, si hay transferencia entre ellos."),
    ]

    for name, formula, explanation in constraints:
        with st.expander(f"**{name}**"):
            st.latex(formula)
            st.markdown(f"*{explanation}*")


# ─── TAB 3: Analysis ──────────────────────────────────────────────────────────
with tab_analysis:
    if result is None:
        st.info("Ejecuta la optimización primero.")
    else:
        st.markdown("## 📈 Análisis de la Solución")

        # ── Ranking of all permutations ────────────────────────────────────────
        if 'all_results' in result and len(result['all_results']) > 1:
            st.markdown("### Top 20 Secuencias por Makespan")
            top_df = pd.DataFrame([
                {'Rank': i+1,
                 'Makespan (min)': ms,
                 'Orden Entrada': ' → '.join(f'R{t}' for t in pi),
                 'Orden Salida':  ' → '.join(f'S{t}' for t in pj)}
                for i, (ms, pi, pj) in enumerate(result['all_results'])
            ])
            # Highlight best
            def highlight_best(row):
                if row['Rank'] == 1:
                    return ['background-color: #d4edda'] * len(row)
                return [''] * len(row)
            st.dataframe(top_df.style.apply(highlight_best, axis=1),
                         use_container_width=True, hide_index=True)

        # ── Storage analysis ───────────────────────────────────────────────────
        st.markdown("### Almacenamiento Temporal")
        col_s1, col_s2 = st.columns([1, 2])
        with col_s1:
            fig_pie = go.Figure(go.Pie(
                labels=['Transferencia Directa', 'Via Almacenamiento'],
                values=[sa['direct'], sa['storage']],
                hole=0.5,
                marker_colors=['#2ec4b6', '#e76f51'],
                textinfo='label+percent',
            ))
            fig_pie.update_layout(
                title="Distribución de flujo de unidades",
                height=300, margin=dict(l=10, r=10, t=40, b=10),
                showlegend=False, font=dict(family='DM Sans'),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        with col_s2:
            if sa['storage_lots']:
                st.markdown("**Lotes que pasan por almacenamiento temporal:**")
                st.dataframe(pd.DataFrame(sa['storage_lots']),
                             use_container_width=True, hide_index=True)
            else:
                st.success("✅ ¡Todos los lotes se transfieren directamente! Sin almacenamiento temporal.")

        # ── Product breakdown ──────────────────────────────────────────────────
        st.markdown("### Inventario por Producto")
        prod_rows = []
        for k in result['K_list']:
            s_tot = sum(result['supply'].get((i, k), 0) for i in result['I_list'])
            d_tot = sum(result['demand'].get((j, k), 0) for j in result['J_list'])
            sources = [f"R{i}" for i in result['I_list'] if result['supply'].get((i,k),0)>0]
            dests   = [f"S{j}" for j in result['J_list'] if result['demand'].get((j,k),0)>0]
            prod_rows.append({
                'Producto': f"P{k}",
                'Total entrada': s_tot,
                'Total salida': d_tot,
                'Camiones origen': ', '.join(sources),
                'Camiones destino': ', '.join(dests),
                '✅ Balance': '✓' if s_tot == d_tot else '✗'
            })
        st.dataframe(pd.DataFrame(prod_rows), use_container_width=True, hide_index=True)


# ─── TAB 4: Code ──────────────────────────────────────────────────────────────
with tab_code:
    st.markdown("## 💻 Código Python del Solver")
    st.markdown("El modelo completo se implementa en `solver.py`. Aquí se muestra la lógica central:")

    st.code("""
# ── Variables de decisión (conceptual MIP) ────────────────────────────────────
# x[i,j,k]      entero ≥ 0  : unidades del producto k de entrada i a salida j
# v[i,j]        binaria     : si existe transferencia entre i y j
# sigma_r[i,i'] binaria     : camión i precede a i' en muelle de entrada
# sigma_s[j,j'] binaria     : camión j precede a j' en muelle de salida
# a[i]          continua ≥ 0: tiempo de llegada de camión de entrada i al muelle
# d[j]          continua ≥ 0: tiempo de salida del camión j
# C             continua ≥ 0: makespan (objetivo)

# ── Objetivo ──────────────────────────────────────────────────────────────────
# min C

# ── Restricciones (13) ────────────────────────────────────────────────────────
# (C1)  C >= d[j]                         ∀j
# (C2)  Σ_j x[i,j,k] = r[i,k]            ∀i,k   (conservación entrada)
# (C3)  Σ_i x[i,j,k] = s[j,k]            ∀j,k   (conservación salida)
# (C4)  Σ_k x[i,j,k] <= M * v[i,j]       ∀i,j   (activación v)
# (C5-C7) Secuencia camiones entrada (3 restricciones por par i,i')
# (C8)  sigma_r[i,i] = 0                  ∀i
# (C9-C11) Secuencia camiones salida (3 restricciones por par j,j')
# (C12) sigma_s[j,j] = 0                  ∀j
# (C13) d[j] >= a[i] + U_i + t_transfer - M*(1-v[i,j])  ∀i,j

# ── Solución por enumeración (factible para I≤8, O≤5) ────────────────────────
from itertools import permutations

best_makespan = float('inf')
for pi in permutations(inbound_trucks):
    for pj in permutations(outbound_trucks):
        ms, a, d = compute_makespan(pi, pj, ...)
        if ms < best_makespan:
            best_makespan = ms
            best_pi, best_pj = pi, pj

# ── Cálculo de makespan dado un orden ─────────────────────────────────────────
def compute_makespan(perm_i, perm_j, U, D, x, ...):
    # Programar muelle de entrada secuencialmente
    a = {}; t = 0
    for i in perm_i:
        a[i] = t
        t += U[i] + T_CHANGE          # U[i] = Σ_k r[i,k]

    # Programar muelle de salida
    d = {}; out_dock_free = 0
    for j in perm_j:
        # j debe esperar a que todos sus productos estén disponibles
        earliest = max(
            a[i] + U[i] + T_TRANSFER
            for i in I if Σ_k x[i,j,k] > 0
        )
        start = max(earliest, out_dock_free)
        d[j] = start + D[j]           # D[j] = Σ_k s[j,k]
        out_dock_free = d[j] + T_CHANGE

    return max(d.values()), a, d
""", language="python")

    if result:
        st.markdown("### 📋 Resultados JSON (exportable)")
        export = {
            'makespan_minutos': result['makespan'],
            'orden_entrada': list(result['inbound_order']),
            'orden_salida': list(result['outbound_order']),
            'tiempos_entrada': {str(k): v for k, v in result['a'].items()},
            'tiempos_salida': {str(k): v for k, v in result['d'].items()},
        }
        st.json(export)

        json_str = json.dumps(export, indent=2)
        st.download_button("⬇️ Descargar resultados JSON", json_str,
                           file_name="logiFast_resultado.json", mime="application/json")

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("---")
st.caption("LogiFast CR Optimizer · UCR Ingeniería Industrial · I Semestre 2026 · Programación Entera Mixta (MIP)")
