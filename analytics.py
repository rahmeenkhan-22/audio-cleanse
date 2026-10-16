import plotly.express as px
import pandas as pd
import streamlit as st

def render_mood_analytics(df: pd.DataFrame):
    """Render interactive Plotly charts for craving intensity over time."""
    if df.empty:
        st.info("No mood logs found yet. Start logging your daily status to see analytics!")
        return

    # 1. Craving Intensity Over Time Line Chart
    fig_line = px.line(
        df,
        x="created_at",
        y="craving_intensity",
        title="<b>Daily Music Craving Intensity (1-10)</b>",
        labels={"created_at": "Date", "craving_intensity": "Intensity"},
        markers=True,
        color_discrete_sequence=["#1A73E8"]
    )
    fig_line.update_layout(yaxis=dict(range=[1, 10]))
    st.plotly_chart(fig_line, use_container_width=True)

    # 2. Trigger Context Breakdown Pie Chart
    if "trigger_context" in df.columns:
        fig_pie = px.pie(
            df,
            names="trigger_context",
            title="<b>Primary Music Listening Triggers</b>",
            color_discrete_sequence=px.colors.sequential.RdBu
        )
        st.plotly_chart(fig_pie, use_container_width=True)