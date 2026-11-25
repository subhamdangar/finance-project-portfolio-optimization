"""Display the original notebook's results without refitting its model."""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

st.set_page_config(page_title="Mean-Variance Portfolio Optimizer", layout="wide")
st.title("Mean-Variance Portfolio Optimizer")
root = Path(__file__).resolve().parent / "data" / "streamlit_results"
required = ["frontier.csv", "portfolio_weights.csv", "in_sample.csv", "training_weights.csv", "out_of_sample.csv", "settings.csv"]
if any(not (root / f).is_file() for f in required):
    st.error("Run all cells in data.ipynb first to generate the Streamlit results.")
    st.stop()
frontier = pd.read_csv(root / "frontier.csv")
weights = pd.read_csv(root / "portfolio_weights.csv", index_col="Stock")
comparison = pd.read_csv(root / "in_sample.csv", index_col="Portfolio")
training_weights = pd.read_csv(root / "training_weights.csv", index_col="Stock")
holdout = pd.read_csv(root / "out_of_sample.csv", index_col="Portfolio")
settings = pd.read_csv(root / "settings.csv", index_col="Setting")["Value"]
rf = float(settings["Risk-free rate"])
ret_col, risk_col = "Annualized mean return", "Annualized volatility"
assets = list(weights.index)
labels = {"INFOSYS":"Infosys", "HDFCBANK":"HDFC Bank", "HINDUNILVR":"Hindustan Unilever", "RELIANCE":"Reliance", "TCS":"TCS", "AIRTEL":"Bharti Airtel", "ICICI":"ICICI Bank", "L&T":"Larsen & Toubro", "SUNPHARMA":"Sun Pharma"}
strategies = ["Target expected return", "Minimum variance", "Maximum Sharpe", "Equal weight"]
st.caption(f"Original notebook results | {settings['Study start']} to {settings['Study end']} | Nine stocks | Assumed risk-free rate: {rf:.2%}")
if "applied" not in st.session_state:
    st.session_state.applied = (100000, strategies[0], 0)
with st.sidebar:
    st.header("Portfolio settings")
    with st.form("portfolio_settings"):
        amount = st.number_input("Hypothetical investment (INR)", min_value=1, max_value=10**12, value=100000, step=1000)
        objective = st.radio("Optimization objective", strategies)
        target = st.select_slider("Target annual return", options=list(range(len(frontier))), value=0, format_func=lambda i: f"{frontier.iloc[i][ret_col]:.2%}")
        st.caption("Target applies only to Target expected return.")
        submitted = st.form_submit_button("Apply", use_container_width=True, type="primary")
    if submitted:
        st.session_state.applied = (amount, objective, target)
        st.success("Portfolio settings applied.")
    st.caption("All nine stocks are available. Risk-free rate and estimation period are fixed by the notebook.")
    st.write(", ".join(labels.get(s,s) for s in assets))
capital, selected, idx = st.session_state.applied
if selected == strategies[0]:
    row = frontier.iloc[min(idx, len(frontier)-1)]
    w = row[assets].astype(float)
    annual_return, volatility = float(row[ret_col]), float(row[risk_col])
    sharpe = (annual_return - rf) / volatility
else:
    w = weights[selected]
    annual_return, volatility, sharpe = comparison.loc[selected, [ret_col, risk_col, "Sharpe ratio"]].astype(float)
p, q = st.tabs(["Portfolio optimization", "Strategy comparison"])
with p:
    st.subheader(selected)
    st.caption("Full five-year in-sample estimates, matching the original notebook's interactive cell. Not forecasts.")
    a,b,c,d = st.columns(4)
    a.metric("Estimated annual return", f"{annual_return:.2%}")
    b.metric("Estimated annual volatility", f"{volatility:.2%}")
    c.metric("Estimated Sharpe ratio", f"{sharpe:.3f}")
    d.metric("Hypothetical capital", f"₹{capital:,.0f}")
    alloc = pd.DataFrame({"Stock":[labels.get(s,s) for s in assets], "Weight (%)":w.to_numpy()*100, "Allocation (INR)":w.to_numpy()*capital})
    left,right = st.columns(2)
    with left:
        st.subheader("Portfolio allocation")
        st.dataframe(alloc.style.format({"Weight (%)":"{:.2f}", "Allocation (INR)":"{:,.2f}"}), hide_index=True, use_container_width=True)
        st.caption(f"Total weight: {w.sum():.2%} | Total allocation: ₹{alloc['Allocation (INR)'].sum():,.2f}")
        st.download_button("Download allocation CSV", alloc.to_csv(index=False), "allocation.csv", "text/csv")
        st.plotly_chart(px.pie(alloc[alloc['Weight (%)'] > 1e-7], names="Stock", values="Weight (%)", hole=.4), use_container_width=True)
    with right:
        st.subheader("Efficient frontier")
        fig = go.Figure(go.Scatter(x=frontier[risk_col]*100, y=frontier[ret_col]*100, name="Efficient frontier", mode="lines"))
        for name in ["Minimum variance", "Maximum Sharpe", "Equal weight"]:
            fig.add_scatter(x=[comparison.loc[name,risk_col]*100],y=[comparison.loc[name,ret_col]*100],mode="markers",name=name,marker=dict(size=10))
        fig.add_scatter(x=[volatility*100],y=[annual_return*100],mode="markers",name="Selected portfolio",marker=dict(size=17,symbol="star",color="#e74c3c"))
        fig.update_layout(xaxis_title="Annualized volatility (%)",yaxis_title="Annualized mean return (%)",legend=dict(orientation="h",y=-.22),height=475)
        st.plotly_chart(fig,use_container_width=True)
        st.caption("The frontier is the original notebook's 50 computed portfolios; the app does not refit the model.")
with q:
    def styled(table):
        return table.style.format({ret_col:"{:.2%}",risk_col:"{:.2%}","Sharpe ratio":"{:.3f}"})
    st.subheader("Five-year in-sample results")
    st.dataframe(styled(comparison),use_container_width=True)
    st.subheader("Out-of-sample results")
    st.caption(f"Weights estimated through {settings['Training end']}; evaluated afterward. Annualized mean returns, not cumulative returns.")
    st.dataframe(styled(holdout),use_container_width=True)
    st.subheader("Weights estimated using the first three years")
    st.dataframe(training_weights.rename(index=labels).style.format("{:.2%}"),use_container_width=True)
    st.caption("The holdout table is the original notebook's strategy comparison; it does not evaluate the full-window target-return portfolio selected on the first tab.")
st.caption("Historical educational analysis. No live prices or personalized investment recommendations.")
