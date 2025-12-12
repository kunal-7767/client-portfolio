import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from io import BytesIO
import base64
from pdf_creator import create_portfolio_pdf_report
import numpy as np

# Initialize session state for PDF
if 'pdf_ready' not in st.session_state:
    st.session_state.pdf_ready = False
if 'pdf_buffer' not in st.session_state:
    st.session_state.pdf_buffer = None

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Portfolio Health Report",
    page_icon=":chart_with_upwards_trend:",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== CUSTOM CSS - HIDE CODE ====================
st.markdown("""
<style>
    /* Hide code blocks */
    .stCodeBlock { display: none; }
    code { display: none; }
    pre { display: none; }
    
    /* Main styles */
    .main-title {
        font-size: 2.8rem;
        color: #1E3A8A;
        text-align: center;
        margin-bottom: 0.5rem;
        font-weight: 700;
    }
    .subtitle {
        text-align: center;
        color: #718096;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .upload-container {
        background: #f8f9fa;
        padding: 2.5rem;
        border-radius: 15px;
        border: 3px dashed #cbd5e0;
        text-align: center;
        margin: 2rem auto;
        max-width: 800px;
    }
    .metric-card {
        background: white;
        padding: 1.2rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        text-align: center;
        border-top: 5px solid #4299E1;
        height: 100%;
    }
    .metric-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #2D3748;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        color: #718096;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-weight: 600;
    }
    .positive { color: #10B981; }
    .negative { color: #EF4444; }
    .chart-container {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        margin-bottom: 1.5rem;
    }
</style>
""", unsafe_allow_html=True)

# ==================== HELPER FUNCTIONS ====================
def process_portfolio_data(df):
    """Process uploaded portfolio data"""
    # Ensure required columns exist
    required_cols = ['Stock Name', 'Quantity', 'Buy Price', 'Current Price']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    
    # Add optional columns if missing
    if 'Sector' not in df.columns:
        df['Sector'] = 'Uncategorized'
    if 'Market Cap' not in df.columns:
        df['Market Cap'] = 'Not Specified'
    
    # Clean data
    df = df.fillna({
        'Sector': 'Uncategorized', 
        'Market Cap': 'Not Specified',
        'Quantity': 0,
        'Buy Price': 0,
        'Current Price': 0
    })
    
    # Convert to numeric
    df['Quantity'] = pd.to_numeric(df['Quantity'], errors='coerce').fillna(0)
    df['Buy Price'] = pd.to_numeric(df['Buy Price'], errors='coerce').fillna(0)
    df['Current Price'] = pd.to_numeric(df['Current Price'], errors='coerce').fillna(0)
    
    # Calculate metrics
    df['Investment'] = df['Quantity'] * df['Buy Price']
    df['Current Value'] = df['Quantity'] * df['Current Price']
    df['Gain/Loss'] = df['Current Value'] - df['Investment']
    df['Gain/Loss %'] = (df['Gain/Loss'] / df['Investment'].replace(0, 1)) * 100
    df['Weight %'] = (df['Current Value'] / df['Current Value'].sum()) * 100
    
    return df

# ... after process_portfolio_data function ...

def prepare_pdf_data(df, total_investment, total_value, total_gain_loss, overall_return):
    """Prepare data for PDF generation"""
    
    # Sector distribution
    sector_dist = df.groupby('Sector')['Current Value'].sum().to_dict()
    
    # Market cap distribution
    cap_dist = df.groupby('Market Cap')['Current Value'].sum().to_dict()
    
    # Top holdings
    top_holdings = []
    top_df = df.nlargest(10, 'Current Value')
    for _, row in top_df.iterrows():
        top_holdings.append({
            'name': row['Stock Name'],
            'sector': row['Sector'],
            'value': row['Current Value'],
            'return_pct': row['Gain/Loss %']
        })
    
    # Top gainers and losers
    top_gainers = []
    gainers_df = df.nlargest(3, 'Gain/Loss %')
    for _, row in gainers_df.iterrows():
        top_gainers.append({
            'name': row['Stock Name'],
            'return_pct': row['Gain/Loss %'],
            'gain_loss': row['Gain/Loss']
        })
    
    top_losers = []
    losers_df = df.nsmallest(3, 'Gain/Loss %')
    for _, row in losers_df.iterrows():
        top_losers.append({
            'name': row['Stock Name'],
            'return_pct': row['Gain/Loss %'],
            'gain_loss': row['Gain/Loss']
        })
    
    # Risk metrics
    top_5_concentration = df.nlargest(5, 'Current Value')['Weight %'].sum()
    top_sector = df.groupby('Sector')['Current Value'].sum().idxmax()
    top_sector_pct = (df.groupby('Sector')['Current Value'].sum().max() / total_value) * 100
    
    pdf_data = {
        'total_investment': total_investment,
        'total_value': total_value,
        'total_gain_loss': total_gain_loss,
        'overall_return': overall_return,
        'num_holdings': len(df),
        'sectors': list(sector_dist.keys()),
        'sector_distribution': sector_dist,
        'market_cap_distribution': cap_dist,
        'top_holdings': top_holdings,
        'top_gainers': top_gainers,
        'top_losers': top_losers,
        'concentration_risk': top_5_concentration,
        'top_sector': top_sector,
        'top_sector_pct': top_sector_pct,
        'sector_chart': bool(sector_dist),
        'market_cap_chart': bool(cap_dist)
    }
    
    return pdf_data

# ... then the main() function starts ...

def create_pie_chart(data_dict, title, color_palette='Set3'):
    """Create a clean pie chart without percentage inside"""
    if not data_dict:
        return None
    
    labels = list(data_dict.keys())
    values = list(data_dict.values())
    
    # Filter out zero values
    nonzero_indices = [i for i, v in enumerate(values) if v > 0]
    labels = [labels[i] for i in nonzero_indices]
    values = [values[i] for i in nonzero_indices]
    
    if not values:
        return None
    
    fig, ax = plt.subplots(figsize=(8, 6))
    
    # Use seaborn color palette
    if color_palette == 'Set3':
        colors = sns.color_palette('Set3', len(labels))
    elif color_palette == 'viridis':
        colors = plt.cm.viridis(np.linspace(0, 1, len(labels)))
    else:
        colors = plt.cm.tab20c(range(len(labels)))
    
    # Create pie chart with better spacing
    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,  # No labels inside
        colors=colors,
        startangle=90,
        wedgeprops=dict(width=0.5, edgecolor='w', linewidth=1),
        autopct='',  # No percentages inside
        pctdistance=0.85
    )
    
    # Add legend with percentages
    percentages = [(v/sum(values))*100 for v in values]
    legend_labels = [f"{label} ({pct:.1f}%)" for label, pct in zip(labels, percentages)]
    
    # Position legend properly
    ax.legend(
        wedges,
        legend_labels,
        title=title,
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1),
        fontsize=9,
        title_fontsize=10
    )
    
    ax.set_title(title, fontsize=14, fontweight='bold', pad=20)
    ax.axis('equal')  # Equal aspect ratio ensures pie is drawn as circle
    
    plt.tight_layout()
    return fig

# ==================== MAIN APP ====================
def main():
    # Title Section
    st.markdown('<h1 class="main-title">Portfolio Health Report Generator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">Upload your portfolio Excel file and generate a professional health report instantly</p>', unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.header("File Upload")
        uploaded_file = st.file_uploader(
            "Choose Excel file",
            type=['xlsx', 'xls'],
            help="Upload Excel with columns: Stock Name, Quantity, Buy Price, Current Price"
        )
        
        st.divider()
        
        st.header("Report Options")
        include_ai = st.checkbox("Include AI Analysis", value=True)
        generate_charts = st.checkbox("Generate Charts", value=True)
        
        st.divider()
        
        st.header("Instructions")
        st.markdown("""
        1. **Upload** Excel file
        2. **Review** portfolio analysis
        3. **Generate** PDF report
        4. **Download** and share
        
        **Required columns:**
        - Stock Name
        - Quantity
        - Buy Price
        - Current Price
        """)
    
    # Main Content Area
    if uploaded_file is not None:
        try:
            # Read and process data
            df = pd.read_excel(uploaded_file)
            df = process_portfolio_data(df)
            
            # Calculate portfolio metrics
            total_investment = df['Investment'].sum()
            total_value = df['Current Value'].sum()
            total_gain_loss = df['Gain/Loss'].sum()
            overall_return = (total_gain_loss / total_investment) * 100 if total_investment > 0 else 0
            
            # Success message
            st.success(f"✅ Successfully processed {len(df)} holdings")
            
            # Portfolio Metrics
            st.subheader("Portfolio Summary")
            
            col1, col2, col3, col4 = st.columns(4)
            
            metrics = [
                ("Total Investment", f"₹{total_investment:,.0f}", "#4299E1"),
                ("Current Value", f"₹{total_value:,.0f}", "#48BB78"),
                ("Gain/Loss", f"₹{total_gain_loss:,.0f} ({overall_return:.2f}%)", 
                 "#10B981" if total_gain_loss >= 0 else "#EF4444"),
                ("Holdings", str(len(df)), "#9F7AEA")
            ]
            
            for col, (label, value, color) in zip([col1, col2, col3, col4], metrics):
                with col:
                    st.markdown(f"""
                    <div class="metric-card" style="border-top-color: {color};">
                        <div class="metric-label">{label}</div>
                        <div class="metric-value">{value}</div>
                    </div>
                    """, unsafe_allow_html=True)
            
            # Charts Section
            if generate_charts:
                st.subheader("Portfolio Analysis")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Sector Distribution
                    sector_dist = df.groupby('Sector')['Current Value'].sum().to_dict()
                    if sector_dist:
                        fig = create_pie_chart(sector_dist, "Sector Distribution", 'Set3')
                        if fig:
                            st.pyplot(fig)
                
                with col2:
                    # Market Cap Distribution
                    cap_dist = df.groupby('Market Cap')['Current Value'].sum().to_dict()
                    if cap_dist:
                        fig = create_pie_chart(cap_dist, "Market Cap Distribution", 'viridis')
                        if fig:
                            st.pyplot(fig)
            
            # Performance Highlights
            st.subheader("Performance Highlights")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("**Top Gainers**")
                top_gainers = df.nlargest(5, 'Gain/Loss %')
                for _, row in top_gainers.iterrows():
                    st.write(f"**{row['Stock Name']}**")
                    st.write(f"Return: {row['Gain/Loss %']:.1f}%")
                    st.write(f"Gain: ₹{row['Gain/Loss']:,.0f}")
                    st.write("---")
            
            with col2:
                st.markdown("**Top Losers**")
                top_losers = df.nsmallest(5, 'Gain/Loss %')
                for _, row in top_losers.iterrows():
                    st.write(f"**{row['Stock Name']}**")
                    st.write(f"Return: {row['Gain/Loss %']:.1f}%")
                    st.write(f"Loss: ₹{abs(row['Gain/Loss']):,.0f}")
                    st.write("---")
            
                       # Data Table
            with st.expander("View Portfolio Data"):
                display_df = df[['Stock Name', 'Quantity', 'Current Price', 'Sector', 
                               'Gain/Loss %', 'Current Value']].sort_values('Current Value', ascending=False)
                st.dataframe(display_df, use_container_width=True)
            
            # ==================== PDF GENERATION ====================
            st.markdown("---")
            st.subheader("Generate Report")
            
            col1, col2 = st.columns([1, 3])
            
            with col1:
                if st.button("Generate PDF Report", type="primary", use_container_width=True):
                    with st.spinner("Creating professional PDF report..."):
                        try:
                            # Prepare data for PDF
                            pdf_data = prepare_pdf_data(
                                df, 
                                total_investment, 
                                total_value, 
                                total_gain_loss, 
                                overall_return
                            )
                            
                            # Generate PDF
                            from pdf_creator import create_portfolio_pdf_report
                            pdf_buffer = create_portfolio_pdf_report(pdf_data)
                            
                            # Store in session state
                            st.session_state.pdf_buffer = pdf_buffer
                            st.session_state.pdf_ready = True
                            
                            st.success("✅ PDF report generated successfully!")
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
            
            # Show download button if PDF is ready
            if st.session_state.get('pdf_ready', False) and st.session_state.get('pdf_buffer'):
                with col2:
                    st.download_button(
                        label="📥 Download PDF Report",
                        data=st.session_state.pdf_buffer,
                        file_name=f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
            
        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            st.info("Please ensure your Excel file has the correct format.")
    
    else:
        # Upload Prompt
        st.markdown("""
        <div class="upload-container">
            <h3 style="color: #2D3748; margin-bottom: 1.5rem;">Upload Portfolio Excel File</h3>
            <p style="color: #718096; margin-bottom: 2rem; font-size: 1.1rem;">
                Upload an Excel file containing your portfolio holdings to generate a professional health report.
            </p>
            
            <div style="background: white; padding: 1.5rem; border-radius: 10px; text-align: left; max-width: 600px; margin: 0 auto;">
                <h4 style="color: #2D3748; margin-bottom: 1rem; border-bottom: 2px solid #E2E8F0; padding-bottom: 0.5rem;">
                    File Format Requirements
                </h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 0.95rem;">
                    <thead>
                        <tr style="background: #F7FAFC;">
                            <th style="padding: 12px; border: 1px solid #E2E8F0; text-align: left;">Column</th>
                            <th style="padding: 12px; border: 1px solid #E2E8F0; text-align: left;">Description</th>
                            <th style="padding: 12px; border: 1px solid #E2E8F0; text-align: left;">Required</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;"><strong>Stock Name</strong></td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;">Name of the stock/security</td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0; color: #10B981;">Required</td>
                        </tr>
                        <tr style="background: #F7FAFC;">
                            <td style="padding: 12px; border: 1px solid #E2E8F0;"><strong>Quantity</strong></td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;">Number of shares/units held</td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0; color: #10B981;">Required</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;"><strong>Buy Price</strong></td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;">Purchase price per unit</td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0; color: #10B981;">Required</td>
                        </tr>
                        <tr style="background: #F7FAFC;">
                            <td style="padding: 12px; border: 1px solid #E2E8F0;"><strong>Current Price</strong></td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;">Current market price per unit</td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0; color: #10B981;">Required</td>
                        </tr>
                        <tr>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;"><strong>Sector</strong></td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;">Industry sector classification</td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0; color: #F59E0B;">Optional</td>
                        </tr>
                        <tr style="background: #F7FAFC;">
                            <td style="padding: 12px; border: 1px solid #E2E8F0;"><strong>Market Cap</strong></td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0;">Large/Mid/Small cap classification</td>
                            <td style="padding: 12px; border: 1px solid #E2E8F0; color: #F59E0B;">Optional</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()