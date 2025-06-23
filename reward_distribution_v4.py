import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import requests

# Constants
BLOCKS_PER_SECOND = 1
SECONDS_PER_YEAR = 86400 * 365
MIN_STAKE = 5_000_000
MAX_STAKE = 500_000_000
MAX_TOTAL_STAKE = 3_000_000_000

RPC_URL = "https://public-en.node.kaia.io"

def cosolidate_staking():
    # request rpc call "kaia_getStakingInfo("latest")" and get the result
    response = requests.post(RPC_URL, json={"jsonrpc": "2.0", "method": "kaia_getStakingInfo", "params": ["latest"], "id": 1})
    result = response.json()["result"]
    reward_addrs = result["councilRewardAddrs"]
    council_staking_amounts = result["councilStakingAmounts"]

    rewardAddrsToStakingAmt = {}
    for i in range(len(reward_addrs)):
        if reward_addrs[i] not in rewardAddrsToStakingAmt:
            rewardAddrsToStakingAmt[reward_addrs[i]] = 0
        rewardAddrsToStakingAmt[reward_addrs[i]] += council_staking_amounts[i]

    staking_amounts = list(rewardAddrsToStakingAmt.values())
    staking_amounts = [int(amount) for amount in staking_amounts if amount >= MIN_STAKE]
    staking_amounts.sort()

    return staking_amounts

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
            "Proposer Reward with Commission (PD on)": proposer_reward_with_commission,
            "Total Reward (PD off)": total_reward,
            "APR (%)": apr,
            "User APR (%)": user_apr,
            "Proposer Reward": proposer_reward,
            "Staker Reward": staker_reward
        })
    df = pd.DataFrame(results)
    return df

# UI setup
st.title("Validator Reward Simulator (Kaia-style & Custom Distribution)")

st.sidebar.header("Simulation Parameters")
proposer_ratio = 15
commission_rate = st.sidebar.slider("Commission Rate (%)", min_value=0, max_value=100, value=5)
reward_per_block = st.sidebar.number_input("Reward per Block (KAIA)", min_value=0.1, max_value=100.0, value=4.8, step=0.1)

# Generate staking amounts
staking_amounts = cosolidate_staking()
vn = len(staking_amounts)

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
st.write("## Simulation Results (85% to Staker)")
st.dataframe(df.style.format({
    "Total Staking": "{:,.0f}",
    "Proposer Reward with Commission (PD on)": "{:,.0f}",
    "Total Reward (PD off)": "{:,.0f}",
    "APR (%)": "{:.2f}",
    "User APR (%)": "{:.2f}",
    "Proposer Reward": "{:,.0f}",
    "Staker Reward": "{:,.0f}"
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
