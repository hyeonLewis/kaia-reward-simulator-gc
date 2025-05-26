import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Constants
BLOCKS_PER_SECOND = 1
SECONDS_PER_YEAR = 86400 * 365
MIN_STAKE = 5_000_000
MAX_STAKE = 500_000_000
MAX_TOTAL_STAKE = 3_000_000_000

# Staking distribution function
def generate_staking_distribution(vn, spread, mode="normal"):
    if mode == "kaia_exact_style":
        staking_amounts = np.array([663_000_000, 289_000_000, 285_000_000, 177_000_000, 135_000_000, 113_000_000, 70_000_000, 63_000_000, 61_000_000, 60_000_000, 54_000_000, 53_000_000, 53_000_000, 48_000_000, 25_000_000, 25_000_000, 25_000_000, 25_000_000, 21_000_000, 21_000_000, 21_000_000, 20_000_000, 20_000_000, 17_000_000, 17_000_000, 14_000_000, 14_000_000, 12_000_000, 12_000_000, 10_000_000, 9_000_000, 9_000_000, 8_000_000, 6_000_000, 5_500_000, 5_000_001, 5_000_001, 5_000_000, 5_000_000, 5_000_000, 5_000_000, 5_000_000])

    elif mode == "kaia_style":
        major_stakers = np.array([663_000_000, 289_000_000, 285_000_000, 177_000_000, 135_000_000, 113_000_000, 70_000_000, 63_000_000])
        remaining = vn - len(major_stakers)
        if remaining < 0:
            st.error("Number of validators must be at least 8 for Kaia-style mode")
            return major_stakers[:vn]
        
        # Remaining stakers between 5M and 50M (log uniform)
        log_min = np.log10(MIN_STAKE)
        log_max = np.log10(50_000_000)
        small_stakers = np.power(10, np.random.uniform(log_min, log_max, remaining-2))

        # Add 2 5M validators
        small_stakers = np.concatenate([np.array([5_000_000] * 2), small_stakers])
        
        staking_amounts = np.concatenate([major_stakers, small_stakers])
    else:
        # Normal spread logic
        if spread == 0:
            staking_amounts = np.full(vn, MIN_STAKE)
        elif spread <= 33:
            log_min = np.log10(50_000_000)
            log_max = np.log10(MAX_STAKE)
            staking_amounts = np.power(10, np.random.uniform(log_min, log_max, vn))
        elif spread <= 66:
            log_min = np.log10(MIN_STAKE)
            log_max = np.log10(MAX_STAKE)
            staking_amounts = np.power(10, np.random.uniform(log_min, log_max, vn))
        else:
            high = int(vn * 0.1)
            low = vn - high
            staking_amounts = np.array([MIN_STAKE] * low + [MAX_STAKE] * high)
            np.random.shuffle(staking_amounts)

    # Cap total staking at 3B and ensure no validator drops below 5M after scaling
    total_stake = staking_amounts.sum()
    if total_stake > MAX_TOTAL_STAKE:
        scaling_factor = MAX_TOTAL_STAKE / total_stake
        staking_amounts *= scaling_factor
        staking_amounts = np.clip(staking_amounts, MIN_STAKE, None)

    return staking_amounts.astype(int)

# Reward calculation function
def calc_rewards(staking_amounts, proposer_ratio, vn, reward_per_block, commission_rate):
    total_reward_per_year = BLOCKS_PER_SECOND * reward_per_block * SECONDS_PER_YEAR
    effective_stakings = [max(0, s - MIN_STAKE) for s in staking_amounts]
    total_effective_stake = sum(effective_stakings)

    results = []
    for i, staking in enumerate(staking_amounts):
        effective_stake = max(0, staking - MIN_STAKE)

        proposer_reward = total_reward_per_year * (proposer_ratio / 100) / vn
        staker_reward = (total_reward_per_year * (1 - proposer_ratio / 100) * (effective_stake / total_effective_stake)) if effective_stake > 0 else 0
        total_reward = proposer_reward + staker_reward
        apr = (total_reward / staking) * 100
        proposer_reward_with_commission = MIN_STAKE * apr / 100 + (staking - MIN_STAKE) * apr / 100 * commission_rate / 100
        user_apr = apr * (100 - commission_rate) / 100

        results.append({
            "Validator": f"Validator {i+1}",
            "Total Staking": staking,
            "Proposer Reward": proposer_reward,
            "Staker Reward": staker_reward,
            "Proposer Reward with Commission": proposer_reward_with_commission,
            "Total Reward": total_reward,
            "APR (%)": apr,
            "User APR (%)": user_apr
        })
    df = pd.DataFrame(results)
    return df

# UI setup
st.title("Validator Reward Simulator (Kaia-style & Custom Distribution)")

st.sidebar.header("Simulation Parameters")
vn = st.sidebar.slider("Number of Validators (Vn)", min_value=8, max_value=100, value=20)
spread = st.sidebar.slider("Staking Distribution Spread (0: Uniform ~ 100: Extreme Bimodal)", min_value=0, max_value=100, value=50)
proposer_ratio = st.sidebar.slider("Proposer Reward Ratio (%)", min_value=0, max_value=100, value=20)
commission_rate = st.sidebar.slider("Commission Rate (%)", min_value=0, max_value=100, value=5)
reward_per_block = st.sidebar.number_input("Reward per Block (KAIA)", min_value=0.1, max_value=100.0, value=4.8, step=0.1)
distribution_mode = st.sidebar.selectbox("Staking Distribution Mode", ["normal", "kaia_style", "kaia_exact_style"])

# Generate staking amounts
staking_amounts = generate_staking_distribution(vn, spread, mode=distribution_mode)
if distribution_mode == "kaia_exact_style":
    vn = len(staking_amounts)

staking_amounts.sort()

# Calculate rewards
df = calc_rewards(staking_amounts, proposer_ratio, vn, reward_per_block, commission_rate)

# Show staking distribution chart
st.write("## Staking Distribution (Tokens)")
fig0, ax0 = plt.subplots(figsize=(10, 6))
ax0.bar(range(1, vn+1), staking_amounts)
ax0.set_xlabel("Validator")
ax0.set_ylabel("Staking Amount")
ax0.set_title("Validator Staking Distribution")
plt.xticks(rotation=90)
st.pyplot(fig0)

# Show results
st.write("## Simulation Results")
st.dataframe(df.style.format({
    "Total Staking": "{:,.0f}",
    "Proposer Reward": "{:,.0f}",
    "Staker Reward": "{:,.0f}",
    "Proposer Reward with Commission": "{:,.0f}",
    "Total Reward": "{:,.0f}",
    "APR (%)": "{:.2f}",
    "User APR (%)": "{:.2f}"
}))

# Show APR per validator
st.write("## Validator APR (%)")
fig1, ax1 = plt.subplots(figsize=(10, 6))
df_sorted = df.sort_values("APR (%)")
ax1.bar(df_sorted["Validator"], df_sorted["APR (%)"])
ax1.set_xlabel("Validator")
ax1.set_ylabel("APR (%)")
ax1.set_title("Validator APR (%) Comparison")
plt.xticks(rotation=90)
st.pyplot(fig1)

# Network average APR by proposer ratio sweeping
st.write("## Network Average APR by Proposer Ratio")
ratios = np.linspace(0, 100, 101)
average_aprs = []

for r in ratios:
    df_tmp = calc_rewards(staking_amounts, r, vn, reward_per_block, commission_rate)
    average_aprs.append(df_tmp["APR (%)"].mean())

fig2, ax2 = plt.subplots(figsize=(10, 6))
ax2.plot(ratios, average_aprs, marker='o')
ax2.axvline(x=proposer_ratio, color='red', linestyle='--', label=f"Current Ratio: {proposer_ratio}%")
ax2.set_xlabel("Proposer Ratio (%)")
ax2.set_ylabel("Network Average APR (%)")
ax2.set_title("Network Average APR vs Proposer Ratio")
ax2.legend()
st.pyplot(fig2)
