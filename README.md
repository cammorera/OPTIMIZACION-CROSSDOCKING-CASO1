# 🚚 Cross-Docking MIP Optimizer

Solución de un modelo de **Programación Entera Mixta (MIP)** para la optimización de operaciones de *cross-docking*: minimización del makespan total en la descarga de camiones inbound y carga de camiones outbound.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://share.streamlit.io)

---

## 📐 Modelo matemático

### Índices
| Símbolo | Descripción |
|---------|-------------|
| $i, i' \in I$ | Camiones inbound |
| $j, j' \in J$ | Camiones outbound |
| $k \in K$ | Productos |

### Variables de decisión

**Continuas**
| Variable | Descripción |
|----------|-------------|
| $A_i$ | Instante de inicio de descarga del camión inbound $i$ |
| $B_i$ | Instante de fin de descarga del camión inbound $i$ |
| $C_j$ | Instante de inicio de carga del camión outbound $j$ |
| $D_j$ | Instante de salida del camión outbound $j$ |
| $T$ | Makespan total (variable objetivo) |

**Enteras binarias**
| Variable | Descripción |
|----------|-------------|
| $U_{ii'}$ | 1 si camión $i$ se descarga antes que $i'$ |
| $V_{jj'}$ | 1 si camión $j$ carga antes que $j'$ |
| $Z_{ij}$ | 1 si existe transferencia entre $i$ y $j$ |

**Enteras no binarias**
| Variable | Descripción |
|----------|-------------|
| $X_{ijk}$ | Cantidad del producto $k$ transferida de $i$ a $j$ |

### Función objetivo
$$\min Z = T$$

### Restricciones

| # | Nombre | Formulación |
|---|--------|-------------|
| 1 | Makespan | $T \geq D_j \quad \forall j$ |
| 2 | Conservación flujo inbound | $\sum_j x_{ijk} = r_{ik} \quad \forall i,k$ |
| 3 | Conservación flujo outbound | $\sum_i x_{ijk} = s_{jk} \quad \forall j,k$ |
| 4 | Flujo-transferencia | $x_{ijk} \leq M z_{ij} \quad \forall i,j,k$ |
| 5 | Tiempo descarga | $B_i = A_i + \sum_k r_{ik} \quad \forall i$ |
| 6 | Secuencia inbound | $A_{i'} \geq B_i + 10 - M(1-u_{ii'}) \quad \forall i \neq i'$ |
| 7 | Inversa inbound | $A_i \geq B_{i'} + 10 - M u_{ii'} \quad \forall i \neq i'$ |
| 8 | Sin auto-prioridad inbound | $u_{ii} = 0$ |
| 9 | Tiempo carga | $D_j = C_j + \sum_k s_{jk} \quad \forall j$ |
| 10 | Secuencia outbound | $C_{j'} \geq D_j + 10 - M(1-v_{jj'}) \quad \forall j \neq j'$ |
| 11 | Inversa outbound | $C_j \geq D_{j'} + 10 - M v_{jj'} \quad \forall j \neq j'$ |
| 12 | Sin auto-prioridad outbound | $v_{jj} = 0$ |
| 13 | Sincronización I/O | $C_j \geq B_i + 5 - M(1-z_{ij}) \quad \forall i,j$ |

---

## 🗂 Formato del archivo de instancia

```
i  <n_inbound>  o  <n_outbound>  n  <n_productos>
r  <i>  <k>  <cantidad>   ...
s  <j>  <k>  <cantidad>   ...
```

**Ejemplo (TS5.txt):** 5 camiones inbound, 3 outbound, 8 productos.

---

## 🚀 Instalación y uso local

```bash
git clone https://github.com/TU_USUARIO/crossdocking-optimizer.git
cd crossdocking-optimizer

pip install -r requirements.txt

# Ejecutar la app
streamlit run app.py
```

---

## ☁️ Despliegue en Streamlit Cloud

1. Fork este repositorio
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repositorio
4. Configura:
   - **Main file path:** `app.py`
   - **Python version:** 3.11

---

## 🏗 Estructura del proyecto

```
crossdocking-optimizer/
├── app.py              # Aplicación Streamlit
├── solver.py           # Modelo MIP con PuLP
├── requirements.txt    # Dependencias
├── instances/
│   └── TS5.txt         # Instancia de prueba
└── README.md
```

---

## 🔧 Tecnologías

| Herramienta | Rol |
|-------------|-----|
| [PuLP](https://coin-or.github.io/pulp/) | Formulación y resolución MIP (solver CBC) |
| [Streamlit](https://streamlit.io) | Interfaz web interactiva |
| [Plotly](https://plotly.com) | Gráficos (Gantt, heatmap, barras) |
| [pandas](https://pandas.pydata.org) | Manejo de datos |

---

## 📄 Licencia

MIT
