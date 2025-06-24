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
def calc_rewards(staking_amounts, proposer_ratio, vn, reward_per_block, commission_rate, node_idx, simulated_total_staking, pd_percentage):  
    total_reward_per_year = BLOCKS_PER_SECOND * reward_per_block * SECONDS_PER_YEAR

    if simulated_total_staking > MIN_STAKE and node_idx >= 0:
        staking_amounts[node_idx] = simulated_total_staking

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

        reward2 = 0
        if i == node_idx and pd_percentage >= 0:
            reward2 = staking * apr / 100 * (1 - pd_percentage / 100) + staking * apr / 100 * pd_percentage / 100 * commission_rate / 100

        common_template = {
            "Validator": f"Validator {i+1}",
            "Total Staking": staking,
            "Current Reward w/ PD": proposer_reward_with_commission,
            "Current Reward w/o PD": total_reward,
            "APR (%)": apr,
            "User APR (%)": user_apr,
            "Proposer Reward": proposer_reward,
            "Staker Reward": staker_reward
        }

        if reward2 > 0:
            common_template["Adjusted Reward w/ PD"] = reward2

        results.append(common_template)
        
    df = pd.DataFrame(results)
    
    if "Adjusted Reward w/ PD" in df.columns:
        column_order = [
            "Validator", "Total Staking", "Current Reward w/ PD", "Current Reward w/o PD", 
            "Adjusted Reward w/ PD", "APR (%)", "User APR (%)", "Proposer Reward", "Staker Reward"
        ]
        existing_columns = [col for col in column_order if col in df.columns]
        df = df[existing_columns]
    
    return df

# UI setup
st.title("Validator Reward Simulator")

proposer_ratio = 15
reward_per_block = 4.8

st.sidebar.header("Simulation Parameters")
node_idx = st.sidebar.number_input("Select your node id", min_value=0, max_value=100, value=0, step=1) - 1
simulated_total_staking = st.sidebar.number_input("Simulate your total staking amount", min_value=0, max_value=100_000_000_000, value=5_000_000)
pd_percentage = st.sidebar.slider("Adjust PD percentage from your total staking amount (%)", min_value=0, max_value=100, value=0)
commission_rate = st.sidebar.slider("PD Commission Rate (%)", min_value=0, max_value=100, value=5)

# Generate staking amounts
staking_amounts = cosolidate_staking()
vn = len(staking_amounts)

# Calculate rewards
df = calc_rewards(staking_amounts, proposer_ratio, vn, reward_per_block, commission_rate, node_idx, simulated_total_staking, pd_percentage)

# Show staking distribution chart
st.write("## Staking Distribution")
fig0, ax0 = plt.subplots(figsize=(10, 6))
ax0.bar(range(1, vn+1), staking_amounts)
ax0.set_xlabel("Validator")
ax0.set_ylabel("Staking Amount")
ax0.set_title("Validator Staking Distribution")
plt.xticks(rotation=90)
st.pyplot(fig0)

# How-to-use
st.markdown("## How to Use This Simulator")

with st.expander("Column Explanation", expanded=True):
    st.markdown("""
    - **Total Staking**: Total staking amount of the validator
    - **Current Reward w/ PD**: Reward you will receive with staking reward and PD commission (Assume fixed 5M self staking)
    - **Current Reward w/o PD**: Reward you will receive without PD commission (Assume all staking is from self staking)
    - **APR (%)**: Annualized Return on Investment (%)
    - **User APR (%)**: Annualized Return on Investment (%) for the user (After deducting PD commission)
    - **Proposer Reward**: Reward from a proposer reward (15%)
    - **Staker Reward**: Reward from a staker reward (85%)
    """)

with st.expander("Step-by-Step Guide", expanded=True):
    st.markdown("""
    ### Step 1: Identify Your Validator
    - Look at the staking distribution chart below
    - Find your validator by matching the total staking amount
    - Note your validator's position (1, 2, 3, etc.)
    
    ### Step 2: Configure Your Simulation
    - **Node ID**: Select your validator's position from the sidebar
    - **Total Staking**: Enter your desired total staking amount (in KAIA tokens)
    - **PD Percentage**: Set your desired PD percentage from your total staking amount (%)
    - **PD Commission Rate**: Set your desired commission rate percentage
    
    ### **Step 3: Analyze Results**
    - Your selected validator will appear highlighted in **green** at the top
    - Compare rewards with and without PD adjustments
    - Review APR calculations and staking distribution
    """)

st.markdown("### Example Scenario")
st.info("""
**Current Situation**: Your validator has 20M KAIA staked  
        
**Goal**: Simulate 30M total staking with 10M from PD with 5% commission rate
        
**Settings**: 
- Node ID: Your validator position
- Total Staking: 30,000,000
- PD Percentage: 33
- Commission Rate: 5%

**Result**:
- Adjusted Reward w/ PD represents the reward you will receive with staking reward and PD commission
""")

st.markdown("---")

# Show results
st.write("## Simulation Results (85% to Staker)")

# Reorder dataframe to put selected node at the top
if node_idx >= 0 and node_idx < len(df):
    # Get the selected row
    selected_row = df.iloc[node_idx:node_idx+1]
    # Get all other rows
    other_rows = df.drop(node_idx)
    # Combine: selected row first, then others
    df_reordered = pd.concat([selected_row, other_rows]).reset_index(drop=True)
else:
    df_reordered = df

# Create a function to highlight the selected node (now at index 0)
def highlight_selected_node(row):
    if row.name == 0:  # First row is the selected node
        return ['background-color: green'] * len(row)
    return [''] * len(row)

# Apply highlighting and formatting
styled_df = df_reordered.style.format({
    "Total Staking": "{:,.0f}",
    "Current Reward w/ PD": "{:,.0f}",
    "Current Reward w/o PD": "{:,.0f}",
    "Adjusted Reward w/ PD": "{:,.0f}",
    "APR (%)": "{:.2f}",
    "User APR (%)": "{:.2f}",
    "Proposer Reward": "{:,.0f}",
    "Staker Reward": "{:,.0f}"
}).apply(highlight_selected_node, axis=1)

st.dataframe(styled_df)

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
