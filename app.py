"""
Cross-Docking Optimizer — Streamlit App
"""

import streamlit as st
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import io, time

from solver import parse_data, validate_data, solve_crossdock

# ─────────────────────────────────────────────
#  PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Cross-Docking Optimizer",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
#  CUSTOM CSS
# ─────────────────────────────────────────────

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;700;800&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'Syne', sans-serif; }

    .stApp { background: #0d0f14; color: #e8e6e0; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: #13161e !important;
        border-right: 1px solid #2a2d38;
    }

    /* Cards */
    .kpi-card {
        background: linear-gradient(135deg, #1a1d26 0%, #1f2330 100%);
        border: 1px solid #2e3245;
        border-radius: 12px;
        padding: 20px 24px;
        text-align: center;
    }
    .kpi-label { font-size: 11px; letter-spacing: 2px; color: #6b7280; text-transform: uppercase; margin-bottom: 6px; }
    .kpi-value { font-size: 36px; font-weight: 800; color: #f0a832; font-family: 'DM Mono', monospace; }
    .kpi-sub   { font-size: 12px; color: #4ade80; margin-top: 4px; }

    /* Section headers */
    .section-title {
        font-size: 13px; letter-spacing: 3px; color: #f0a832;
        text-transform: uppercase; margin: 28px 0 12px;
        border-bottom: 1px solid #2a2d38; padding-bottom: 8px;
    }

    /* Status badge */
    .badge-ok   { background:#14532d; color:#4ade80; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:700; }
    .badge-warn { background:#713f12; color:#fbbf24; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:700; }
    .badge-err  { background:#7f1d1d; color:#f87171; padding:4px 12px; border-radius:20px; font-size:12px; font-weight:700; }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background: #1a1d26; border: 1px solid #2e3245; border-radius: 8px;
        color: #9ca3af; font-family: 'Syne', sans-serif;
    }
    .stTabs [aria-selected="true"] {
        background: #f0a832 !important; color: #0d0f14 !important; font-weight: 700;
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(135deg, #f0a832, #e88c10);
        color: #0d0f14; font-weight: 800; border: none; border-radius: 8px;
        font-family: 'Syne', sans-serif; letter-spacing: 1px;
        padding: 12px 28px; width: 100%; font-size: 14px;
    }
    .stButton > button:hover { transform: translateY(-1px); box-shadow: 0 8px 20px rgba(240,168,50,0.3); }

    /* Plotly charts dark bg */
    .js-plotly-plot { background: transparent !important; }

    /* Hide streamlit branding */
    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────
#  SIDEBAR
# ─────────────────────────────────────────────

with st.sidebar:
    st.markdown("## 🚚 Cross-Docking\n**Optimizer**")
    st.markdown("---")

    st.markdown('<p class="section-title">Instancia</p>', unsafe_allow_html=True)

    uploaded = st.file_uploader("Archivo .txt de instancia", type=["txt"])

    use_demo = st.checkbox("Usar instancia demo (TS5)", value=True if not uploaded else False)

    st.markdown('<p class="section-title">Parámetros del solver</p>', unsafe_allow_html=True)

    time_limit = st.slider("Tiempo límite (seg)", 30, 600, 120, step=30)
    gap_rel    = st.select_slider("GAP relativo", options=[0.001, 0.005, 0.01, 0.02, 0.05], value=0.01)
    M_val      = st.number_input("Big-M", value=50000, step=1000, min_value=1000)

    st.markdown("---")
    solve_btn = st.button("⚡ RESOLVER MODELO")

# ─────────────────────────────────────────────
#  LOAD DATA
# ─────────────────────────────────────────────

DEMO_DATA = (
    "i\t5\t\to\t3\t\tn\t8\t\t"
    "r\t1\t1\t170\t"
    "r\t2\t1\t6\tr\t2\t2\t6\tr\t2\t3\t19\tr\t2\t4\t50\tr\t2\t5\t38\t"
    "r\t2\t6\t6\tr\t2\t7\t19\tr\t2\t8\t56\t"
    "r\t3\t1\t49\tr\t3\t2\t31\tr\t3\t3\t60\tr\t3\t6\t12\tr\t3\t7\t37\tr\t3\t8\t31\t"
    "r\t4\t5\t143\tr\t4\t7\t47\t"
    "r\t5\t4\t58\tr\t5\t5\t36\tr\t5\t7\t72\tr\t5\t8\t14\t"
    "s\t1\t1\t75\ts\t1\t2\t12\ts\t1\t3\t59\ts\t1\t6\t9\ts\t1\t7\t98\ts\t1\t8\t40\t"
    "s\t2\t1\t150\ts\t2\t5\t217\t"
    "s\t3\t2\t25\ts\t3\t3\t20\ts\t3\t4\t108\ts\t3\t6\t9\ts\t3\t7\t77\ts\t3\t8\t61"
)

raw_text = None
if uploaded:
    raw_text = uploaded.read().decode("utf-8")
elif use_demo:
    raw_text = DEMO_DATA

# ─────────────────────────────────────────────
#  HEADER
# ─────────────────────────────────────────────

col_logo, col_title = st.columns([1, 8])
with col_title:
    st.markdown("# 🏭 Cross-Docking MIP Optimizer")
    st.markdown(
        "<span style='color:#6b7280;font-size:14px'>Minimización de makespan — Modelo de Programación Entera Mixta</span>",
        unsafe_allow_html=True,
    )

st.markdown("---")

if raw_text is None:
    st.info("👈 Sube un archivo de instancia o activa la demo para comenzar.")
    st.stop()

# ─────────────────────────────────────────────
#  PARSE & DISPLAY DATA
# ─────────────────────────────────────────────

I, J, K, r, s = parse_data(raw_text)
warnings = validate_data(I, J, K, r, s)

# KPI row
c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Camiones Inbound</div><div class="kpi-value">{len(I)}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Camiones Outbound</div><div class="kpi-value">{len(J)}</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Productos</div><div class="kpi-value">{len(K)}</div></div>', unsafe_allow_html=True)
with c4:
    total_units = sum(r.values())
    st.markdown(f'<div class="kpi-card"><div class="kpi-label">Unidades totales</div><div class="kpi-value">{total_units:,}</div></div>', unsafe_allow_html=True)

if warnings:
    for w in warnings:
        st.warning(f"⚠️ {w}")

st.markdown('<p class="section-title">Datos de la instancia</p>', unsafe_allow_html=True)

tab_r, tab_s = st.tabs(["📦 Oferta Inbound (r_ik)", "📤 Demanda Outbound (s_jk)"])

with tab_r:
    r_df = pd.DataFrame(
        [[r[(i, k)] for k in K] for i in I],
        index=[f"Camión-In {i}" for i in I],
        columns=[f"Prod {k}" for k in K],
    )
    r_df["TOTAL"] = r_df.sum(axis=1)
    st.dataframe(r_df.style.background_gradient(cmap="YlOrBr", subset=r_df.columns[:-1]), use_container_width=True)

with tab_s:
    s_df = pd.DataFrame(
        [[s[(j, k)] for k in K] for j in J],
        index=[f"Camión-Out {j}" for j in J],
        columns=[f"Prod {k}" for k in K],
    )
    s_df["TOTAL"] = s_df.sum(axis=1)
    st.dataframe(s_df.style.background_gradient(cmap="YlGn", subset=s_df.columns[:-1]), use_container_width=True)

# ─────────────────────────────────────────────
#  SOLVE
# ─────────────────────────────────────────────

if solve_btn or ("results" in st.session_state):

    if solve_btn:
        with st.spinner("🔧 Resolviendo modelo MIP (PuLP/CBC)…"):
            t0 = time.time()
            results = solve_crossdock(
                I, J, K, r, s,
                M=M_val,
                time_limit=time_limit,
                gap_rel=gap_rel,
            )
            results["elapsed"] = time.time() - t0
        st.session_state["results"] = results
    else:
        results = st.session_state["results"]

    st.markdown("---")
    st.markdown('<p class="section-title">Resultados</p>', unsafe_allow_html=True)

    status = results["status"]
    badge_class = "badge-ok" if status == "Optimal" else ("badge-warn" if "Infeasible" not in status else "badge-err")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(
            f'<div class="kpi-card"><div class="kpi-label">Estado</div>'
            f'<div style="margin-top:8px"><span class="{badge_class}">{status}</span></div></div>',
            unsafe_allow_html=True,
        )
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Makespan (T*)</div><div class="kpi-value">{results["T"]:.1f}</div><div class="kpi-sub">unidades de tiempo</div></div>', unsafe_allow_html=True)
    with c3:
        active_z = sum(results["Z"].values())
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Transferencias activas</div><div class="kpi-value">{int(active_z)}</div><div class="kpi-sub">de {len(I)*len(J)} posibles</div></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Tiempo de cómputo</div><div class="kpi-value">{results["elapsed"]:.1f}s</div></div>', unsafe_allow_html=True)

    # ── TABS RESULTS ──────────────────────────
    st.markdown("")
    tab_gantt, tab_schedule, tab_flows, tab_model = st.tabs(
        ["📊 Gantt", "📋 Horarios", "🔗 Flujos", "📐 Modelo"]
    )

    # ── GANTT ─────────────────────────────────
    with tab_gantt:
        gantt_tasks = []
        colors = {}

        for i in I:
            start = results["A"][i]
            finish = results["B"][i]
            gantt_tasks.append(
                dict(Task=f"IN-{i}", Start=start, Finish=finish, Resource="Inbound")
            )

        for j in J:
            start = results["C"][j]
            finish = results["D"][j]
            gantt_tasks.append(
                dict(Task=f"OUT-{j}", Start=start, Finish=finish, Resource="Outbound")
            )

        color_map = {"Inbound": "#f0a832", "Outbound": "#4ade80"}

        fig = ff.create_gantt(
            gantt_tasks,
            colors=color_map,
            index_col="Resource",
            show_colorbar=True,
            group_tasks=True,
            showgrid_x=True,
            title="Diagrama de Gantt — Secuencia de Camiones",
        )
        fig.update_layout(
            paper_bgcolor="#0d0f14",
            plot_bgcolor="#13161e",
            font=dict(color="#e8e6e0", family="Syne"),
            title_font=dict(size=16),
            xaxis=dict(gridcolor="#2a2d38", title="Tiempo"),
        )
        # Add makespan line
        fig.add_vline(
            x=results["T"], line_dash="dash", line_color="#f87171",
            annotation_text=f"T*={results['T']:.0f}",
            annotation_font_color="#f87171",
        )
        st.plotly_chart(fig, use_container_width=True)

    # ── SCHEDULE TABLE ────────────────────────
    with tab_schedule:
        col_in, col_out = st.columns(2)

        with col_in:
            st.markdown("**Inbound trucks**")
            sched_in = pd.DataFrame(
                {
                    "Camión": [f"In-{i}" for i in I],
                    "Inicio descarga (A)": [round(results["A"][i], 1) for i in I],
                    "Fin descarga (B)": [round(results["B"][i], 1) for i in I],
                    "Duración": [round(results["B"][i] - results["A"][i], 1) for i in I],
                    "Unidades": [sum(r[(i, k)] for k in K) for i in I],
                }
            )
            st.dataframe(sched_in, use_container_width=True, hide_index=True)

        with col_out:
            st.markdown("**Outbound trucks**")
            sched_out = pd.DataFrame(
                {
                    "Camión": [f"Out-{j}" for j in J],
                    "Inicio carga (C)": [round(results["C"][j], 1) for j in J],
                    "Salida (D)": [round(results["D"][j], 1) for j in J],
                    "Duración": [round(results["D"][j] - results["C"][j], 1) for j in J],
                    "Unidades": [sum(s[(j, k)] for k in K) for j in J],
                }
            )
            st.dataframe(sched_out, use_container_width=True, hide_index=True)

    # ── FLOWS ─────────────────────────────────
    with tab_flows:
        col_z, col_x = st.columns([1, 2])

        with col_z:
            st.markdown("**Matriz de transferencias Z_ij**")
            Z_mat = pd.DataFrame(
                [[results["Z"][(i, j)] for j in J] for i in I],
                index=[f"In-{i}" for i in I],
                columns=[f"Out-{j}" for j in J],
            )
            fig_z = px.imshow(
                Z_mat, color_continuous_scale=[[0, "#1a1d26"], [1, "#f0a832"]],
                text_auto=True, aspect="auto",
                labels=dict(x="Outbound", y="Inbound", color="Z"),
            )
            fig_z.update_layout(
                paper_bgcolor="#0d0f14", plot_bgcolor="#13161e",
                font=dict(color="#e8e6e0"),
                coloraxis_showscale=False,
                margin=dict(l=40, r=20, t=20, b=40),
            )
            st.plotly_chart(fig_z, use_container_width=True)

        with col_x:
            st.markdown("**Flujos X_ijk > 0**")
            flow_rows = []
            for (i, j, k), v in results["X"].items():
                if v > 0:
                    flow_rows.append({"Inbound": f"In-{i}", "Outbound": f"Out-{j}", "Producto": f"P{k}", "Cantidad": v})
            if flow_rows:
                flow_df = pd.DataFrame(flow_rows).sort_values(["Inbound", "Outbound", "Producto"])
                fig_flow = px.bar(
                    flow_df, x="Producto", y="Cantidad", color="Outbound",
                    facet_col="Inbound", barmode="stack",
                    color_discrete_sequence=["#4ade80", "#f0a832", "#60a5fa"],
                )
                fig_flow.update_layout(
                    paper_bgcolor="#0d0f14", plot_bgcolor="#13161e",
                    font=dict(color="#e8e6e0"),
                    legend=dict(bgcolor="#13161e"),
                    margin=dict(l=0, r=0, t=40, b=0),
                )
                st.plotly_chart(fig_flow, use_container_width=True)
            else:
                st.info("No hay flujos positivos en la solución.")

    # ── MODEL SUMMARY ────────────────────────
    with tab_model:
        st.markdown(
            """
            **Función Objetivo:** $\\min Z = T$

            **Variables de decisión:**

            | Variable | Tipo | Descripción |
            |---|---|---|
            | $A_i$ | Continua | Inicio de descarga del camión inbound $i$ |
            | $B_i$ | Continua | Fin de descarga del camión inbound $i$ |
            | $C_j$ | Continua | Inicio de carga del camión outbound $j$ |
            | $D_j$ | Continua | Salida del camión outbound $j$ |
            | $T$ | Continua | Makespan total |
            | $U_{ii'}$ | Binaria | 1 si $i$ se descarga antes que $i'$ |
            | $V_{jj'}$ | Binaria | 1 si $j$ sale antes que $j'$ |
            | $Z_{ij}$ | Binaria | 1 si existe transferencia entre $i$ y $j$ |
            | $X_{ijk}$ | Entera | Cantidad del producto $k$ de $i$ hacia $j$ |

            **Restricciones activas:** 13 grupos
            """
        )

        c_left, c_right = st.columns(2)
        with c_left:
            st.markdown(
                """
                1. $T \\geq D_j$
                2. $\\sum_j x_{ijk} = r_{ik}$
                3. $\\sum_i x_{ijk} = s_{jk}$
                4. $x_{ijk} \\leq M z_{ij}$
                5. $B_i = A_i + \\sum_k r_{ik}$
                6. $A_{i'} \\geq B_i + 10 - M(1-u_{ii'})$
                7. $A_i \\geq B_{i'} + 10 - M \\cdot u_{ii'}$
                """
            )
        with c_right:
            st.markdown(
                """
                8. $u_{ii} = 0$
                9. $D_j = C_j + \\sum_k s_{jk}$
                10. $C_{j'} \\geq D_j + 10 - M(1-v_{jj'})$
                11. $C_j \\geq D_{j'} + 10 - M \\cdot v_{jj'}$
                12. $v_{jj} = 0$
                13. $C_j \\geq B_i + 5 - M(1-z_{ij})$
                """
            )

    # ── EXPORT ───────────────────────────────
    st.markdown("---")
    st.markdown('<p class="section-title">Exportar resultados</p>', unsafe_allow_html=True)

    buf = io.StringIO()
    buf.write(f"STATUS,{results['status']}\n")
    buf.write(f"MAKESPAN,{results['T']:.4f}\n\n")
    buf.write("INBOUND_SCHEDULES\n")
    buf.write("truck,A,B\n")
    for i in I:
        buf.write(f"{i},{results['A'][i]:.4f},{results['B'][i]:.4f}\n")
    buf.write("\nOUTBOUND_SCHEDULES\n")
    buf.write("truck,C,D\n")
    for j in J:
        buf.write(f"{j},{results['C'][j]:.4f},{results['D'][j]:.4f}\n")
    buf.write("\nFLOWS_X_ijk\n")
    buf.write("i,j,k,qty\n")
    for (i, j, k), v in results["X"].items():
        if v > 0:
            buf.write(f"{i},{j},{k},{v}\n")

    st.download_button(
        "⬇️ Descargar resultados CSV",
        data=buf.getvalue(),
        file_name="crossdock_results.csv",
        mime="text/csv",
    )
