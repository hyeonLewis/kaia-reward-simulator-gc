import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Constants
BLOCKS_PER_SECOND = 1
REWARD_PER_BLOCK = 4.8
SECONDS_PER_YEAR = 86400 * 365
TOTAL_REWARD_PER_YEAR = BLOCKS_PER_SECOND * REWARD_PER_BLOCK * SECONDS_PER_YEAR
MIN_STAKE = 5_000_000
MAX_STAKE = 500_000_000
MAX_TOTAL_STAKE = 3_000_000_000

st.title("Validator Reward Distribution Simulator")

# User Input
st.sidebar.header("Simulation Parameters")
vn = st.sidebar.slider("Validator Count (Vn)", min_value=1, max_value=100, value=10)
spread = st.sidebar.slider("Staking Distribution Spread (0: Uniform ~ 100: Extreme)", min_value=0, max_value=100, value=50)
proposer_ratio = st.sidebar.slider("Proposer Reward Ratio (%)", min_value=0, max_value=100, value=20)

staker_ratio = 100 - proposer_ratio

# Auto-generate Staking Distribution
np.random.seed(42)
spread_factor = np.interp(spread, [0, 100], [0, 5])  # 0이면 균등, 5면 극단
raw_stakings = np.random.pareto(spread_factor, vn) if spread > 0 else np.ones(vn)
scaled_stakings = MIN_STAKE + (raw_stakings / raw_stakings.max()) * (MAX_STAKE - MIN_STAKE)
staking_amounts = np.clip(scaled_stakings, MIN_STAKE, MAX_STAKE)
staking_amounts = np.sort(staking_amounts)

# Limit Total Staking Sum
total_stake = staking_amounts.sum()
if total_stake > MAX_TOTAL_STAKE:
    scaling_factor = MAX_TOTAL_STAKE / total_stake
    staking_amounts *= scaling_factor
    st.info(f"Total staking exceeds {MAX_TOTAL_STAKE:,} tokens, so it has been automatically scaled by {scaling_factor:.4f}.")

staking_amounts = np.clip(staking_amounts, MIN_STAKE, MAX_STAKE)

staking_amounts = staking_amounts.astype(int)

# Calculate Function
def calc_rewards(staking_amounts, proposer_ratio):
    effective_stakings = [max(0, s - MIN_STAKE) for s in staking_amounts]
    total_effective_stake = sum(effective_stakings)

    results = []
    for i, staking in enumerate(staking_amounts):
        effective_stake = max(0, staking - MIN_STAKE)

        proposer_reward = TOTAL_REWARD_PER_YEAR * (proposer_ratio / 100) / vn
        staker_reward = (TOTAL_REWARD_PER_YEAR * (1 - proposer_ratio / 100) * (effective_stake / total_effective_stake)) if effective_stake > 0 else 0
        total_reward = proposer_reward + staker_reward
        apr = (total_reward / staking) * 100

        results.append({
            "Validator": f"Validator {i+1}",
            "Total Staking": staking,
            "Proposer Reward": proposer_reward,
            "Staker Reward": staker_reward,
            "Total Reward": total_reward,
            "APR (%)": apr
        })
    df = pd.DataFrame(results)
    return df

df = calc_rewards(staking_amounts, proposer_ratio)

# Output Results
st.write("## Simulation Results")
st.dataframe(df.style.format({
    "Total Staking": "{:,.0f}",
    "Proposer Reward": "{:,.0f}",
    "Staker Reward": "{:,.0f}",
    "Total Reward": "{:,.0f}",
    "APR (%)": "{:.2f}"
}))

# APR Graph
st.write("## Validator APR Comparison")
fig, ax = plt.subplots(figsize=(10, 6))
df_sorted = df.sort_values("APR (%)")
ax.bar(df_sorted["Validator"], df_sorted["APR (%)"])
ax.set_xlabel("Validator")
ax.set_ylabel("APR (%)")
ax.set_title("Validator APR Comparison")
plt.xticks(rotation=90)
st.pyplot(fig)

# Network Average APR Change with Proposer:Staker Ratio
st.write("## Network Average APR Change with Proposer:Staker Ratio")
ratios = np.linspace(0, 100, 101)
average_aprs = []

for r in ratios:
    df_tmp = calc_rewards(staking_amounts, r)
    average_aprs.append(df_tmp["APR (%)"].mean())

fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.plot(ratios, average_aprs, marker='o')
ax2.axvline(x=proposer_ratio, color='red', linestyle='--', label=f"Current Ratio: {proposer_ratio}%")
ax2.set_xlabel("Proposer Ratio (%)")
ax2.set_ylabel("Network Average APR (%)")
ax2.set_title("Network Average APR Change with Proposer:Staker Ratio")
ax2.legend()
st.pyplot(fig2)
