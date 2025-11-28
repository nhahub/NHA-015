"""
Export page - data download capabilities
"""
import streamlit as st


def render_export(df):
    """Render export and reports page"""
    st.markdown("### 💾 Data Export")
    
    if df.empty:
        st.info("No data to export.")
        return
    
    st.success(f"Ready to export {len(df)} records.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Download CSV",
            csv,
            "mokhber_data.csv",
            "text/csv",
            key='download-csv'
        )
    
    with col2:
        json_str = df.to_json(orient='records', force_ascii=False, indent=2)
        st.download_button(
            "📥 Download JSON",
            json_str,
            "mokhber_data.json",
            "application/json",
            key='download-json'
        )