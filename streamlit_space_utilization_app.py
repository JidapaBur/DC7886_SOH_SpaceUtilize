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
    #zone_capacity[1] = sum(dept_capacity.values())
    
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
    
    zone_summary = df.groupby("Zone")["Effective_Pallets"].sum().reset_index()
    zone_summary.columns = ["Zone", "Total_Pallets"]
    zone_summary["Capacity"] = zone_summary["Zone"].map(zone_capacity)
    zone_summary["Utilization_%"] = (zone_summary["Total_Pallets"] / zone_summary["Capacity"]) * 100
    zone_summary["Utilization_%"] = zone_summary["Utilization_%"].round(2)

    # เปลี่ยนชื่อ zone
    zone_summary["Zone"] = zone_summary["Zone"].replace({1: "Floor", 2: "Rack", 3: "Recieve"})

#----------------------------------------------------------------------
    
    # เตรียมข้อมูลกราฟ zone
    used = zone_summary["Total_Pallets"]
    unused = zone_summary["Capacity"] - zone_summary["Total_Pallets"]
    total = used + unused
    used_percent = (used / total) * 100
    unused_percent = (unused / total) * 100


    # ใช้ตัวเลขคำนวณต่อได้ เช่น
    unused = zone_summary["Capacity"] - zone_summary["Total_Pallets"]

    # จากนั้น ถ้าจะโชว์ใน dataframe ให้ format เป็น string แยกออกมา
    zone_summary_display = zone_summary.copy()
    zone_summary_display["Total_Pallets"] = zone_summary_display["Total_Pallets"].apply(lambda x: f"{int(x):,}")
    zone_summary_display["Capacity"] = zone_summary_display["Capacity"].apply(lambda x: f"{int(x):,}")
    zone_summary_display["Utilization_%"] = zone_summary_display["Utilization_%"].apply(lambda x: f"{x:.2f}%")
    
    st.subheader("Zone Summary")
    st.dataframe(zone_summary_display, use_container_width=True)

# ------------------ Dept Summary -------------------

    # Summary per zone
    zone_summary = df.groupby("Zone")["Effective_Pallets"].sum().reset_index()
    zone_summary.columns = ["Zone", "Total_Pallets"]
    zone_summary["Capacity"] = zone_summary["Zone"].map(zone_capacity)
    zone_summary["Utilization_%"] = (zone_summary["Total_Pallets"] / zone_summary["Capacity"]) * 100
    zone_summary["Utilization_%"] = zone_summary["Utilization_%"].round(2)

    # สร้าง dept_summary ใหม่
    dept_summary = df.groupby("DEPT_NAME")["Pallets"].sum().reset_index()
    dept_summary.columns = ["Dept.", "Total_Pallets"]
    
    # ใส่ capacity
    #dept_summary["Capacity"] = dept_summary["Dept."].map(dept_capacity)
    dept_summary["Capacity"] = zone_capacity[1]  # ใช้ cap ของ Zone 1 แทน
    
    # คำนวณ % utilization
    dept_summary["%Utilization"] = (dept_summary["Total_Pallets"] / dept_summary["Capacity"]) * 100
    dept_summary["%Utilization"] = dept_summary["%Utilization"].round(2)
    
    # เตรียม dataframe สำหรับแสดงผล
    dept_summary_display = dept_summary.copy()
    dept_summary_display["Total_Pallets"] = dept_summary_display["Total_Pallets"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "-"
    )
    dept_summary_display["Capacity"] = dept_summary_display["Capacity"].apply(
        lambda x: f"{int(x):,}" if pd.notna(x) else "-"
    )
    dept_summary_display["%Utilization"] = dept_summary_display["%Utilization"].apply(
        lambda x: f"{x:.2f}%" if pd.notna(x) else "-"
    )
    
    st.subheader("Dept Summary (Capacity & Utilization)")
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
        bars1 = ax.bar(labels, used_percent, label="Used", color="steelblue")
        bars2 = ax.bar(labels, unused_percent, bottom=used_percent, label="Unused", color="lightgray")
        ax.set_ylabel("Utilization (%)")
        ax.set_title("7886 Utilization (100%)")
        ax.legend()
    
        # เพิ่ม label บนแต่ละแท่ง
        ax.bar_label(bars1, labels=[f"{v:.1f}%" for v in used_percent], label_type='center', fontsize=9, color='white')
        ax.bar_label(bars2, labels=[f"{v:.1f}%" for v in unused_percent], label_type='center', fontsize=9, color='black')
    
        st.pyplot(fig)

        # เตรียมข้อมูล Effective Pallets ของแต่ละแผนกที่อยู่ใน Zone 1
        dept_used = df[df["Zone"] == 1].groupby("DEPT_NAME")["Effective_Pallets"].sum()
        dept_used = dept_used[dept_used > 0].sort_values(ascending=False)
        
        # ตรวจสอบก่อนว่ามีแผนกใดบ้าง
        if not dept_used.empty:
            zone1_capacity = zone_capacity[1]
            
            # คำนวณ cap share ตามสัดส่วนการใช้จริง
            total_used = dept_used.sum()
            dept_cap_share = (dept_used / total_used) * zone1_capacity
            unused = dept_cap_share - dept_used
            unused[unused < 0] = 0
            
            # คำนวณเปอร์เซ็นต์
            total = dept_used + unused
            used_percent = (dept_used / total) * 100
            unused_percent = (unused / total) * 100
        
            # สร้างกราฟ
            with col2:
                fig2, ax2 = plt.subplots(figsize=(6, 4))
                bars1 = ax2.bar(used_percent.index, used_percent, label="Used", color='steelblue')
                bars2 = ax2.bar(used_percent.index, unused_percent, bottom=used_percent, label="Unused", color='lightgray')
                ax2.set_ylabel("Utilization (%)")
                ax2.set_title("Dept-wise Utilization (Relative to Zone 1 Capacity)")
                ax2.legend()
        
                ax2.bar_label(bars1, labels=[f"{v:.1f}%" for v in used_percent], label_type='center', fontsize=9, color='white')
                ax2.bar_label(bars2, labels=[f"{v:.1f}%" for v in unused_percent], label_type='center', fontsize=9, color='black')
        
                st.pyplot(fig2)




    
    st.image("7886Layout.png", use_container_width=True)

