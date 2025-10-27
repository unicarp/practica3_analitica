import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="NBA Elos", layout="wide")

# ---------------------------
# Cargar datos
# ---------------------------
@st.cache_data
def load_data(path="data/nba_all_elo.csv"):
    # Leer CSV
    df = pd.read_csv(path, dtype=str)  # leer como str para limpieza inicial
    # Renombrar columnas que nos interesan
    rename_map = {
        "year_id": "season",
        "team_id": "team",
        "date_game": "game_date",
        "seasongame": "seasongame",
        "is_playoffs": "is_playoffs",
        "game_result": "game_result"
    }
    # Solo renombrar si existen
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    # Convertir tipos útiles (si existen)
    if "season" in df.columns:
        df["season"] = pd.to_numeric(df["season"], errors="coerce").astype("Int64")
    # seasongame -> número dentro de la temporada (orden por equipo)
    if "seasongame" in df.columns:
        df["seasongame"] = pd.to_numeric(df["seasongame"], errors="coerce").astype("Int64")

    # game_date -> datetime (provee varios formatos)
    if "game_date" in df.columns:
        df["game_date"] = pd.to_datetime(df["game_date"], errors="coerce", dayfirst=False)

    # is_playoffs -> 0/1
    if "is_playoffs" in df.columns:
        df["is_playoffs"] = pd.to_numeric(df["is_playoffs"], errors="coerce").fillna(0).astype(int)

    # limpiamos filas sin team o sin resultado
    df = df.dropna(subset=[c for c in ["team", "game_result", "season"] if c in df.columns])

    # crear columna 'type'
    df["type"] = df["is_playoffs"].apply(lambda x: "Playoffs" if int(x) == 1 else "Temporada regular")

    # normalizar valores de game_result: mantener solo 'W' o 'L'
    df["game_result"] = df["game_result"].str.strip().str.upper().where(df["game_result"].notna())
    df = df[df["game_result"].isin(["W", "L"])]

    return df

# Carga
df = load_data()

# ---------------------------
# Sidebar - filtros
# ---------------------------
st.sidebar.header("Filtros")

# Años disponibles (orden ascendente)
years = sorted(df["season"].dropna().unique())
years = [int(y) for y in years]
selected_year = st.sidebar.selectbox("Año", years, index=len(years)-1)

# Equipos disponibles (orden alfabético)
teams = sorted(df[df["season"] == selected_year]["team"].unique())
if not teams:
    teams = sorted(df["team"].unique())
selected_team = st.sidebar.selectbox("Equipos", teams)

# Tipo de juego: usamos radio horizontal para simular 'pills'
game_type = st.sidebar.radio(
    "Tipo de juego",
    options=["Temporada regular", "Playoffs", "Ambos"],
    horizontal=True
)

st.sidebar.markdown("---")
st.sidebar.write("Dataset: nba_all_elo.csv")

# ---------------------------
# Filtrado de datos
# ---------------------------
df_sel = df[df["season"] == int(selected_year)]

if game_type != "Ambos":
    df_sel = df_sel[df_sel["type"] == game_type]

df_sel = df_sel[df_sel["team"] == selected_team].copy()

# Orden correcto por número de juego en la temporada si existe; si no, por fecha
if "seasongame" in df_sel.columns and df_sel["seasongame"].notna().any():
    df_sel = df_sel.sort_values(["seasongame"])
else:
    df_sel = df_sel.sort_values(["game_date"])

st.title(f"⛹️ {selected_team} — Temporada {selected_year}")

if df_sel.empty:
    st.warning("No hay datos para los filtros seleccionados.")
else:
    # Crear columnas booleans y acumulados
    df_sel["is_win"] = (df_sel["game_result"] == "W").astype(int)
    df_sel["is_loss"] = (df_sel["game_result"] == "L").astype(int)

    # cumsum respetando orden actual del df_sel
    df_sel["Acum Ganados"] = df_sel["is_win"].cumsum()
    df_sel["Acum Perdidos"] = df_sel["is_loss"].cumsum()

    col1_up, col2_up = st.columns([3, 1])

    # ---------------------------
    # Gráfica de líneas (ambas series)
    # ---------------------------
    with col1_up:    
        fig_line = px.line(
            df_sel,
            x="game_date" if "game_date" in df_sel.columns and df_sel["game_date"].notna().any() else "seasongame",
            y=["Acum Ganados", "Acum Perdidos"],
            labels={"value": "Acumulado", "variable": "Tipo", "game_date": "Fecha", "seasongame": "Juego #"},
            title=f"Acumulado de juegos ganados y perdidos — {selected_team} ({selected_year})",
            template="plotly_white",
            color_discrete_map={
                "Acum Ganados": "#53ed6a",
                "Acum Perdidos": "#e43131"
            }
        )
        st.plotly_chart(fig_line, use_container_width=True)

    # ---------------------------
    # Gráfica de pastel (porcentaje en la temporada filtrada)
    # ---------------------------
    total_wins = int(df_sel["is_win"].sum())
    total_losses = int(df_sel["is_loss"].sum())

    with col2_up:
        fig_pie = px.pie(
            names=["Ganados", "Perdidos"],
            values=[total_wins, total_losses],
            title="Porcentaje de juegos ganados vs perdidos",
            color_discrete_sequence=["#53ed6a", "#e43131"]
        )
        st.plotly_chart(fig_pie, use_container_width=True)

    # ---------------------------
    # Información adicional y tabla
    # ---------------------------
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Juegos totales:", total_wins + total_losses)
        st.metric("Victorias:", total_wins)
    with col2:
        st.metric("Derrotas:", total_losses)
        if total_wins + total_losses > 0:
            st.metric("Win Rate:", f"{total_wins / (total_wins + total_losses) * 100:.2f}%")

    st.markdown("### Tabla (últimos juegos)")
    st.dataframe(df_sel[["season", "seasongame", "game_date", "team", "game_result", "type", "pts", "opp_id", "opp_pts"]].sort_values(
        by=["seasongame"] if "seasongame" in df_sel.columns and df_sel["seasongame"].notna().any() else ["game_date"], ascending=False
    ).head(50), use_container_width=True)