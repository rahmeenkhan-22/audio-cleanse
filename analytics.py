import plotly.express as px
import pandas as pd
import streamlit as st

def render_analytics(db, user_id="00000000-0000-0000-0000-000000000000"):
    st.subheader("📊 Your Recovery & Craving Analytics")
    
    # Fetch user mood logs from Supabase
    try:
        response = db.client.table("mood_logs").select("*").eq("user_id", user_id).order("created_at").execute()
        logs = response.data
    except Exception as e:
        st.error(f"Failed to fetch mood logs: {e}")
        logs = []

    if not logs:
        st.info("No craving logs found yet! Use the 'Daily Craving & Mood Log' panel on the sidebar to log your first entry.")
        return

    df = pd.DataFrame(logs)
    df['created_at'] = pd.to_datetime(df['created_at'])

    # Key Summary Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    total_logs = len(df)
    avg_craving = df['craving_score'].mean() if 'craving_score' in df.columns else 0
    latest_craving = df['craving_score'].iloc[-1] if 'craving_score' in df.columns else 0
    primary_trigger = df['trigger_context'].mode()[0] if 'trigger_context' in df.columns and not df['trigger_context'].empty else "N/A"

    col1.metric("Total Logs", total_logs)
    col2.metric("Avg Craving Intensity", f"{avg_craving:.1f} / 10")
    col3.metric("Latest Craving Level", f"{latest_craving} / 10")
    col4.metric("Top Trigger", primary_trigger)

    st.divider()

    # Interactive Plotly Charts
    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.markdown("### 📈 Craving Intensity Trend")
        if 'craving_score' in df.columns:
            fig_line = px.line(
                df, 
                x='created_at', 
                y='craving_score', 
                markers=True,
                labels={'created_at': 'Date / Time', 'craving_score': 'Intensity (1-10)'},
                title="Craving Intensity Over Time"
            )
            fig_line.update_traces(line_color="#4CAF50", marker_size=8)
            st.plotly_chart(fig_line, use_container_width=True)

    with chart_col2:
        st.markdown("### 🎯 Trigger Context Breakdown")
        if 'trigger_context' in df.columns:
            trigger_counts = df['trigger_context'].value_counts().reset_index()
            trigger_counts.columns = ['Trigger', 'Count']
            fig_pie = px.pie(
                trigger_counts, 
                values='Count', 
                names='Trigger', 
                title="Triggers Distribution",
                hole=0.4
            )
            st.plotly_chart(fig_pie, use_container_width=True)