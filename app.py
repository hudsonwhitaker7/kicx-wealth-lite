import streamlit as st

st.set_page_config(page_title="Kicx Wealth Lite", page_icon="💹", layout="centered")

st.title("Kicx Wealth — Lite (Educational Simulator)")
st.caption("Enter your amount and get a model portfolio instantly. Educational simulation only — not financial advice.")

# ----- Inputs
col1, col2 = st.columns(2)
with col1:
    capital = st.number_input("Amount to invest", min_value=100, value=10000, step=100)
with col2:
    risk = st.selectbox("Risk level", ["conservative", "balanced", "growth"])

col3, col4 = st.columns(2)
with col3:
    country = st.selectbox("Country", ["AU", "US"])
with col4:
    horizon_years = st.slider("Horizon (years)", 1, 50, 5)

st.divider()

# ----- Guardrails
GUARDS = {
    "conservative": {"cashMin":0.20,"cashMax":0.40,"cryptoMax":0.10,"singleMax":0.15,"eqMin":0.40,"eqMax":0.60,"reitMin":0.05,"reitMax":0.15},
    "balanced":     {"cashMin":0.05,"cashMax":0.20,"cryptoMax":0.12,"singleMax":0.18,"eqMin":0.55,"eqMax":0.75,"reitMin":0.05,"reitMax":0.15},
    "growth":       {"cashMin":0.03,"cashMax":0.10,"cryptoMax":0.25,"singleMax":0.20,"eqMin":0.60,"eqMax":0.80,"reitMin":0.00,"reitMax":0.10},
}

def clamp(x,a,b): return max(a, min(b, x))

CORE = {
    "AU": {"cashETF": ("AAA.AX","Aussie Cash ETF","bond"), "auETF": ("VAS.AX","ASX 300 ETF","etf")},
    "US": {"usETF": ("VOO","S&P 500 ETF","etf"), "reitETF": ("VNQ","US REITs ETF","reit")},
    "STOCKS": [("NVDA","NVIDIA","stock"), ("AAPL","Apple","stock"), ("CSL.AX","CSL Limited","stock")],
    "CRYPTO": [("BTC","Bitcoin","crypto"), ("ETH","Ethereum","crypto"), ("SOL","Solana","crypto")],
}

def normalize(rows):
    s = sum(w for _,_,_,w in rows)
    return [(sym,name,typ,(w/s if s>0 else 0)) for sym,name,typ,w in rows]

def build_allocations(risk:str, country:str):
    g = GUARDS[risk]
    # base suggestions, then clamped to risk rails
    cash   = clamp(0.30 if risk=="conservative" else (0.12 if risk=="balanced" else 0.06), g["cashMin"], g["cashMax"])
    crypto = clamp(0.06 if risk=="conservative" else (0.10 if risk=="balanced" else 0.20), 0, g["cryptoMax"])
    reit   = clamp(0.10 if risk!="growth" else 0.06, g["reitMin"], g["reitMax"])
    equities = clamp(1 - (cash + crypto + reit), g["eqMin"], g["eqMax"])

    # core ETFs 70% of equities; split US/AU
    core_eq = equities * 0.70
    us_share = 0.6 if country=="AU" else 0.7
    us_core = core_eq * us_share
    au_core = core_eq - us_core
    sat_eq  = equities - core_eq

    rows = []
    rows.append((CORE["AU"]["cashETF"][0], CORE["AU"]["cashETF"][1], CORE["AU"]["cashETF"][2], cash))
    rows.append((CORE["US"]["usETF"][0],   CORE["US"]["usETF"][1],   CORE["US"]["usETF"][2],   us_core))
    rows.append((CORE["AU"]["auETF"][0],   CORE["AU"]["auETF"][1],   CORE["AU"]["auETF"][2],   au_core))
    rows.append((CORE["US"]["reitETF"][0], CORE["US"]["reitETF"][1], CORE["US"]["reitETF"][2], reit))

    # satellites (NVDA/AAPL/CSL)
    sat_names = CORE["STOCKS"]
    sat_each = min(sat_eq / len(sat_names) if len(sat_names)>0 else 0, g["singleMax"])
    for sym,name,typ in sat_names:
        rows.append((sym,name,typ,sat_each))

    # crypto mix
    if risk=="conservative":
        rows.append((CORE["CRYPTO"][0][0], CORE["CRYPTO"][0][1], CORE["CRYPTO"][0][2], crypto))
    elif risk=="balanced":
        rows.append((CORE["CRYPTO"][0][0], CORE["CRYPTO"][0][1], CORE["CRYPTO"][0][2], crypto*0.6))
        rows.append((CORE["CRYPTO"][1][0], CORE["CRYPTO"][1][1], CORE["CRYPTO"][1][2], crypto*0.4))
    else:
        rows.append((CORE["CRYPTO"][0][0], CORE["CRYPTO"][0][1], CORE["CRYPTO"][0][2], crypto*0.5))
        rows.append((CORE["CRYPTO"][1][0], CORE["CRYPTO"][1][1], CORE["CRYPTO"][1][2], crypto*0.3))
        rows.append((CORE["CRYPTO"][2][0], CORE["CRYPTO"][2][1], CORE["CRYPTO"][2][2], crypto*0.2))

    # cap single position then normalize to 100%
    capped = [(s,n,t,min(w, GUARDS[risk]["singleMax"])) for s,n,t,w in rows]
    return normalize(capped)

def property_card(country:str):
    if country=="AU":
        return {
            "proxy":"VNQ",
            "regions":[
                {"code":"SA3-NEWC","name":"Newcastle / Lake Macquarie","score":82,"buy_box":"$550–650k 3-bed townhouse, yield ≥4.7%, vacancy ≤1.5%"},
                {"code":"SA3-IPSW","name":"Ipswich","score":79,"buy_box":"$450–600k house, yield ≥4.8%, vacancy ≤1.6%"},
            ]
        }
    return {"proxy":"VNQ","regions":[{"code":"US-SUN","name":"US Sun Belt (proxy)","score":78,"buy_box":"REIT exposure only in v1"}]}

summary = {
    "conservative":"Steady compounding: higher cash, quality ETFs, capped BTC.",
    "balanced":"Balanced growth: broad ETFs + selective growth + BTC/ETH sleeve.",
    "growth":"High growth tilt: tech, small caps, and a larger crypto sleeve."
}[risk]

allocs = build_allocations(risk, country)

st.subheader("Your Plan")
st.write(summary)
st.caption(f"Horizon: {horizon_years} years · Country: {country}")

# Allocations table
import pandas as pd
df = pd.DataFrame([{
    "Symbol": s, "Name": n, "Type": t.upper(), "Weight %": round(w*100, 2),
    "Target $": round(w*capital, 2)
} for s,n,t,w in allocs])

st.dataframe(df, use_container_width=True)

# Simple progress bars
for _, row in df.iterrows():
    st.progress(min(100, max(0,int(row["Weight %"]))), text=f'{row["Symbol"]} · {row["Weight %"]}%')

# Buy plan
st.subheader("Buy Plan")
st.write("• ETFs: buy in 2 tranches over 1–2 weeks\n• Stocks: enter on minor pullbacks\n• Crypto: DCA weekly")
st.write("Note: This is a simulation helper, not financial advice.")

# Property card
st.subheader("Property (v1)")
pc = property_card(country)
st.write(f"Proxy via REIT ETF: **{pc['proxy']}**")
for r in pc["regions"]:
    st.markdown(f"- **{r['name']}** (Score {r['score']}): {r['buy_box']}")

st.info("Educational simulation only — not financial advice.")
