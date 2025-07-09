import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

#----------------------------------------------------------------------

st.set_page_config(layout="wide")
st.title("DC Space Utilization Dashboard")
st.markdown("<div style='text-align:right; font-size:12px; color:gray;'>Master Product Update on May-25 Version 1.0.0 Developed by Jidapa Buranachan</div>", unsafe_allow_html=True)

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
    df["Total Cost"] = df["SOH"] * df["Cost"]

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
    zone_area = {1: 2520, 2: 1680, 3: 480}
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

    st.subheader("Space Utilization 7886")

    # สร้างตารางรวมตามแผนก
    dept_summary = df.groupby("DEPT_NAME").agg({
        "SOH": "sum",
        "Pallets": "sum",
        "Total Cost": "sum"  
    }).reset_index()

    dept_summary.columns = ["Dept.", "Sum of SOH", "Sum of Pallet", "Sum of Total Cost"]
    dept_summary = dept_summary.sort_values(by="Dept.")

    # เพิ่มแถว Grand Total
    grand_total = pd.DataFrame({
        "Dept.": ["Grand Total"],
        "Sum of SOH": [dept_summary["Sum of SOH"].sum()],
        "Sum of Pallet": [dept_summary["Sum of Pallet"].sum()],
        "Sum of Total Cost": [dept_summary["Sum of Total Cost"].sum()]
    })
    dept_summary = pd.concat([dept_summary, grand_total], ignore_index=True)

    # จัดรูปแบบแสดงผล
    def format_table(df):
        df["Sum of SOH"] = df["Sum of SOH"].apply(lambda x: f"{int(x):,}")
        df["Sum of Pallet"] = df["Sum of Pallet"].apply(lambda x: f"{int(x):,}")
        df["Sum of Total Cost"] = df["Sum of Total Cost"].apply(lambda x: f"{int(x):,}")
        return df

    st.dataframe(format_table(dept_summary), use_container_width=True)
    
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

    #st.subheader("Zone Summary")
    #st.dataframe(zone_summary)

    #st.subheader("Zone 1: Dept Breakdown")
    #st.dataframe(dept_usage_zone1)

#----------------------------------------------------------------------
    
    # เตรียมข้อมูลกราฟ zone
    used = zone_summary["Total_Pallets"]
    unused = zone_summary["Capacity"] - zone_summary["Total_Pallets"]
    total = used + unused
    used_percent = (used / total) * 100
    unused_percent = (unused / total) * 100


    # ใช้ตัวเลขคำนวณต่อได้ เช่น
    unused = zone_summary["Capacity"] - zone_summary["Total_Pallets"]
    zone_summary["Unused"] = unused

    # จากนั้น ถ้าจะโชว์ใน dataframe ให้ format เป็น string แยกออกมา
    zone_summary_display = zone_summary.copy()
    zone_summary_display["Sum of SOH"] = zone_summary_display["Sum of SOH"].apply(lambda x: f"{int(x):,}")
    zone_summary_display["Total_Pallets"] = zone_summary_display["Total_Pallets"].apply(lambda x: f"{int(x):,}")
    zone_summary_display["Capacity"] = zone_summary_display["Capacity"].apply(lambda x: f"{int(x):,}")

    st.subheader("Zone Summary")
    st.dataframe(zone_summary_display, use_container_width=True)

# ------------------ Dept Summary -------------------
    # สร้างตารางรวมตามแผนก
    dept_summary = df.groupby("DEPT_NAME").agg({
        "SOH": "sum",
        "Pallets": "sum",
        "Total Cost": "sum"  
    }).reset_index()
    
    dept_summary.columns = ["Dept.", "Sum of SOH", "Sum of Pallet", "Sum of Total Cost"]
    dept_summary = dept_summary.sort_values(by="Dept.")
    
    # เพิ่มแถว Grand Total
    grand_total = pd.DataFrame({
        "Dept.": ["Grand Total"],
        "Sum of SOH": [dept_summary["Sum of SOH"].sum()],
        "Sum of Pallet": [dept_summary["Sum of Pallet"].sum()],
        "Sum of Total Cost": [dept_summary["Sum of Total Cost"].sum()]
    })
    dept_summary = pd.concat([dept_summary, grand_total], ignore_index=True)
    
    # เตรียม DataFrame สำหรับแสดงผล
    dept_summary_display = dept_summary.copy()
    dept_summary_display["Sum of SOH"] = dept_summary_display["Sum of SOH"].apply(lambda x: f"{int(x):,}")
    dept_summary_display["Sum of Pallet"] = dept_summary_display["Sum of Pallet"].apply(lambda x: f"{int(x):,}")
    dept_summary_display["Sum of Total Cost"] = dept_summary_display["Sum of Total Cost"].apply(lambda x: f"{int(x):,}")

    st.subheader("Dept Summary")
    st.dataframe(dept_summary_display, use_container_width=True)

#----------------------------------------------------------------------
    
    # สร้างคอลัมน์แนวนอนสำหรับกราฟ
    col1, col2 = st.columns(2)

    zone_labels = {
        1: "Zone 1: Floor",
        2: "Zone 2: Rack",
        3: "Zone 3: Receiving"
    }
    labels = zone_summary["Zone"].map(zone_labels).tolist()

    # กราฟซ้าย: Zone Utilization
    with col1:
        fig, ax = plt.subplots(figsize=(6, 4))
        ax.bar(labels, used_percent, label="Used", color="steelblue")
        ax.bar(labels, unused_percent, bottom=used_percent, label="Unused", color="lightgray")
        ax.set_ylabel("Utilization (%)")
        ax.set_title("Zone Utilization (100%)")
        ax.legend()
        st.pyplot(fig)

    # เตรียมข้อมูลกราฟ dept
    name_map = {"TV": "T.V.", "WASHING": "WASHING MACHINE"}
    dept_used = df[df["Zone"] == 1].groupby("DEPT_NAME")["Effective_Pallets"].sum()
    dept_used_renamed = dept_used.rename(index=name_map)
    dept_used_renamed = dept_used_renamed[dept_used_renamed.index.isin(dept_capacity)]
    cap = pd.Series(dept_capacity)[dept_used_renamed.index]
    unused = cap - dept_used_renamed
    unused[unused < 0] = 0
    total = dept_used_renamed + unused
    used_percent = (dept_used_renamed / total) * 100
    unused_percent = (unused / total) * 100

    # กราฟขวา: Dept Utilization
    with col2:
        fig2, ax2 = plt.subplots(figsize=(6, 4))
        ax2.bar(used_percent.index, used_percent, label="Used", color='steelblue')
        ax2.bar(used_percent.index, unused_percent, bottom=used_percent, label="Unused", color='lightgray')
        ax2.set_ylabel("Utilization (%)")
        ax2.set_title("Dept Utilization in Zone 1 (100%)")
        ax2.legend()
        st.pyplot(fig2)

