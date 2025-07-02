import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

#----------------------------------------------------------------------

st.set_page_config(layout="wide")
st.title("DC Space Utilization Dashboard")

#----------------------------------------------------------------------

# Upload only SOH file
soh_file = st.file_uploader("Upload SOH File", type=["csv", "xlsx"])

if soh_file:
    # Load SOH data
    soh_df = pd.read_csv(soh_file, encoding='cp874') if soh_file.name.endswith(".csv") else pd.read_excel(soh_file)

    # Load master data from local file in repo
    master_df = pd.read_excel("master_product.xlsx")

#----------------------------------------------------------------------
    
    df = pd.merge(soh_df, master_df, on="SKU", how="left")
    df["Pallets"] = df["SOH"] / df["Case per pallet"]
    df["Pallets"] = df["Pallets"].fillna(0).round(2)

#----------------------------------------------------------------------
    
    def get_stacking(row):
        if row["Zone"] == 2:
            return 1
        elif row["DEPT_NAME"] == "REFRIGERATOR":
            return 2.2
        elif row["DEPT_NAME"] == "WASHING MACHINE":
            return 3
        else:
            return 3
            
    df["Stacking"] = df.apply(get_stacking, axis=1)
    df["Effective_Pallets"] = (df["Pallets"] / df["Stacking"]).round(2)

#----------------------------------------------------------------------
    
    # Zone & dept config
    zone_area = {1: 2520, 2: 1140, 3: 480}
    zone_stack_limit = {1: 3, 2: 1, 3: 1}
    dept_area = {"REFRIGERATOR": 1060, "TKB": 200, "WASHING MACHINE": 670, "T.V.": 590}
    dept_stack_limit = {"T.V.": 2.2, "REFRIGERATOR": 2.2, "WASHING MACHINE": 3, "TKB": 2.5}
    pallet_area = 1.2

    # Dept capacity
    dept_capacity = {}
    for dept, area in dept_area.items():
        usable_area = area * 0.9
        stack = dept_stack_limit.get(dept, 3)
        capacity = (usable_area / pallet_area) * stack
        dept_capacity[dept] = round(capacity)

    # Zone capacity
    zone_capacity = {}
    for zone, area in zone_area.items():
        usable_area = area * (0.9 if zone in [1, 3] else 1)
        stack = zone_stack_limit[zone]
        capacity = (usable_area / pallet_area) * stack
        zone_capacity[zone] = round(capacity)
    zone_capacity[1] = sum(dept_capacity.values())
    
#----------------------------------------------------------------------
    
    # Summary per zone
    zone_summary = df.groupby("Zone")["Effective_Pallets"].sum().reset_index()
    zone_summary.columns = ["Zone", "Total_Pallets"]
    zone_summary["Capacity"] = zone_summary["Zone"].map(zone_capacity)
    zone_summary["Utilization_%"] = (zone_summary["Total_Pallets"] / zone_summary["Capacity"]) * 100
    zone_summary["Utilization_%"] = zone_summary["Utilization_%"].round(2)

    # Dept breakdown in zone 1
    dept_usage_zone1 = df[df["Zone"] == 1].groupby("DEPT_NAME")["Effective_Pallets"].sum().reset_index()
    dept_usage_zone1["Capacity"] = dept_usage_zone1["DEPT_NAME"].map(dept_capacity)
    dept_usage_zone1["Utilization_%"] = (dept_usage_zone1["Effective_Pallets"] / dept_usage_zone1["Capacity"]) * 100
    dept_usage_zone1["Utilization_%"] = dept_usage_zone1["Utilization_%"].round(2)

    st.subheader("Zone Summary")
    st.dataframe(zone_summary)

    st.subheader("Zone 1: Dept Breakdown")
    st.dataframe(dept_usage_zone1)

#----------------------------------------------------------------------
    
    # คำนวณ zone utilization %
zone_labels = {1: "Zone 1: Floor", 2: "Zone 2: Rack", 3: "Zone 3: Receiving"}
labels_zone = zone_summary["Zone"].map(zone_labels).tolist()
used = zone_summary["Total_Pallets"]
unused = zone_summary["Capacity"] - used
total = used + unused
used_percent_zone = (used / total) * 100
unused_percent_zone = (unused / total) * 100

# คำนวณ dept utilization %
dept_used = dept_used[dept_used.index.isin(dept_cap)]
cap = dept_cap[dept_used.index]
unused_dept = cap - dept_used
unused_dept[unused_dept < 0] = 0
total_dept = dept_used + unused_dept
used_percent_dept = (dept_used / total_dept) * 100
unused_percent_dept = (unused_dept / total_dept) * 100

# Layout กราฟคู่
col1, col2 = st.columns(2)

with col1:
    fig1, ax1 = plt.subplots(figsize=(6, 4))
    ax1.bar(labels_zone, used_percent_zone, label="Used", color="steelblue")
    ax1.bar(labels_zone, unused_percent_zone, bottom=used_percent_zone, label="Unused", color="lightgray")
    ax1.set_ylabel("Utilization (%)")
    ax1.set_title("Zone Utilization (100%)")
    ax1.legend()
    st.pyplot(fig1)

with col2:
    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.bar(used_percent_dept.index, used_percent_dept, label="Used", color="steelblue")
    ax2.bar(used_percent_dept.index, unused_percent_dept, bottom=used_percent_dept, label="Unused", color="lightgray")
    ax2.set_ylabel("Utilization (%)")
    ax2.set_title("Dept Utilization in Zone 1 (100%)")
    ax2.legend()
    st.pyplot(fig2)
