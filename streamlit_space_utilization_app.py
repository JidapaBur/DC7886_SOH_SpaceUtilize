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

    # ตัดรายการที่ SOH <= 0 ทิ้ง
    soh_df = soh_df[soh_df["SOH"] > 0]

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
    #df["Effective_Pallets"] = (df["Pallets"] / df["Stacking"]).round(2)

#----------------------------------------------------------------------
    
    # Zone & dept config
    zone_area = {1: 3300, 2: 2880, 3: 480}
    zone_stack_limit = {1: 3, 2: 1, 3: 1}
    dept_area = {"REFRIGERATOR": 1060, "TKB": 200, "WASHING MACHINE": 670, "T.V.": 590}
    dept_stack_limit = {"T.V.": 2.2, "REFRIGERATOR": 2.2, "WASHING MACHINE": 3, "TKB": 2.5}
    pallet_area = 1.2

    # Dept capacity
    dept_capacity = {}
    for dept, area in dept_area.items():
        usable_area = area * 0.90
        stack = dept_stack_limit.get(dept, 1.3)
        capacity = (usable_area / pallet_area) * stack
        dept_capacity[dept] = round(capacity)

    # Zone capacity
    zone_capacity = {}
    for zone, area in zone_area.items():
        usable_area = area * (0.90 if zone in [1, 3] else 1)
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

    zone_summary = df.groupby("Zone")["Pallets"].sum().reset_index()
    zone_summary.columns = ["Zone", "Total_Pallets"]
    zone_summary["Capacity"] = zone_summary["Zone"].map(zone_capacity)
    zone_summary["Utilization_%"] = (zone_summary["Total_Pallets"] / zone_summary["Capacity"]) * 100
    zone_summary["Utilization_%"] = zone_summary["Utilization_%"].round(2)

    
    # เปลี่ยนชื่อ zone
    zone_summary["Zone_Name"] = zone_summary["Zone"].replace({1: "Floor", 2: "Rack", 3: "Recieve"})


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
    zone_summary_display["Zone"] = zone_summary_display["Zone_Name"]  # ✅ ใช้ชื่อที่เปลี่ยน
    zone_summary_display = zone_summary_display[["Zone", "Total_Pallets", "Capacity", "Utilization_%"]]

    
    st.subheader("Zone Summary")
    st.dataframe(zone_summary_display, use_container_width=True)

# ------------------ Dept Summary -------------------

    # ✅ สร้าง Dept Summary ด้วย Effective Pallets จาก Zone 1
    zone1_df = df[df["Zone"] == 1]
    dept_summary = zone1_df.groupby("DEPT_NAME")["Pallets"].sum().reset_index()
    dept_summary.columns = ["Dept.", "Total_Pallets"]
    
    # ✅ ใช้ capacity เดียวกันทั้งตาราง (Zone 1)
    dept_summary["Capacity"] = zone_capacity[1]
    
    # ✅ คำนวณ Utilization%
    dept_summary["%Utilization"] = (dept_summary["Total_Pallets"] / dept_summary["Capacity"]) * 100
    dept_summary["%Utilization"] = dept_summary["%Utilization"].round(2)
    
    # ✅ Format for display
    dept_summary_display = dept_summary.copy()
    dept_summary_display["Total_Pallets"] = dept_summary_display["Total_Pallets"].apply(lambda x: f"{int(x):,}")
    dept_summary_display["Capacity"] = dept_summary_display["Capacity"].apply(lambda x: f"{int(x):,}")
    dept_summary_display["%Utilization"] = dept_summary_display["%Utilization"].apply(lambda x: f"{x:.2f}%")
    
    # ✅ Add total row
    total_pallets = dept_summary["Total_Pallets"].sum()
    total_capacity = zone_capacity[1]
    total_utilization = (total_pallets / total_capacity) * 100
    
    total_row = pd.DataFrame([{
        "Dept.": "Total",
        "Total_Pallets": f"{int(total_pallets):,}",
        "Capacity": f"{int(total_capacity):,}",
        "%Utilization": f"{total_utilization:.2f}%"
    }])
    
    dept_summary_display = pd.concat([dept_summary_display, total_row], ignore_index=True)
    
    st.subheader("Dept Summary (Capacity & Utilization)")
    st.dataframe(dept_summary_display, use_container_width=True)



    #-----------------------------SKU Table-----------------------------------------
    
    # สร้างตารางแสดงรายการสินค้า พร้อมข้อมูล pallet และการใช้พื้นที่
    # เตรียมเฉพาะ Description
    desc_map = soh_df[["SKU", "Description"]].drop_duplicates().set_index("SKU").to_dict()["Description"]
    
    # map เข้า df
    df["Description"] = df["SKU"].map(desc_map)
    
    # แล้วค่อยใช้:
    detail_table = df[["SKU", "Description", "DEPT_NAME", "Zone", "Pallets"]].copy()

    
    # เปลี่ยนชื่อ column ให้อ่านง่าย
    detail_table.columns = ["SKU", "Description", "Dept", "Zone", "Pallets"]
    
    # จัดรูปแบบตัวเลขให้ดูสวย
    detail_table["Pallets"] = detail_table["Pallets"].round(2)
    
    
    # แสดงผลใน Streamlit
    st.subheader("SKU-Level Pallet & Space Utilization")
    st.dataframe(detail_table, use_container_width=True)

    # ------------------------------- Missing Product ---------------------------------------
    
    # แปลง SKU เป็น string ทั้ง 2 ฝั่งเพื่อเทียบค่าถูกต้อง
    soh_df["SKU"] = soh_df["SKU"].astype(str)
    master_df["SKU"] = master_df["SKU"].astype(str)
    
    # ดึงรายการ SKU ที่มีใน master
    master_skus = master_df["SKU"].unique()
    
    # ✅ กรองเฉพาะสินค้าที่ไม่มีใน master จาก SOH โดยตรง
    missing_sku_df = soh_df[~soh_df["SKU"].isin(master_skus)]
    
    # ✅ สร้างตารางเฉพาะคอลัมน์ที่ต้องการแสดง
    # ตรวจสอบว่าคอลัมน์ชื่ออะไรบ้างในไฟล์ SOH (บางครั้งชื่ออาจไม่ตรง)
    expected_cols = ["STORE_NO", "SKU", "Barcode", "Description", "SOH"]
    available_cols = [col for col in expected_cols if col in missing_sku_df.columns]
    
    missing_detail_table = missing_sku_df[available_cols].copy()
    
    # ✅ แสดงผล
    st.subheader("❌ SKUs Missing from Master Product (From Uploaded SOH File)")
    st.dataframe(missing_detail_table.reset_index(drop=True), use_container_width=True)



    
#----------------------------------------------------------------------
    # สร้างคอลัมน์แนวนอนสำหรับกราฟ
    col1, col2 = st.columns(2)

    zone_labels = {
        1: "Zone 1: Floor",
        2: "Zone 2: Rack",
        3: "Zone 3: Receiving"
    }
    labels = zone_summary["Zone"].map(zone_labels).tolist()

    # ---------------------- กราฟซ้าย (Zone Summary) ---------------------
    # เตรียมข้อมูล pie chart สำหรับแต่ละโซน
    zone_labels_map = {1: "Zone 1: Floor", 2: "Zone 2: Rack"}
    colors = ['steelblue', 'lightgray']
    
    fig, axes = plt.subplots(1, 2, figsize=(8, 2))
    
    for i, zone_id in enumerate([1, 2]):
        zone_name = zone_labels_map[zone_id]
        
        zone_row = zone_summary[zone_summary["Zone"] == zone_id]
        if not zone_row.empty:
            used = float(zone_row["Total_Pallets"])
            unused = float(zone_row["Capacity"] - zone_row["Total_Pallets"])
            used = max(used, 0)
            unused = max(unused, 0)
            
            wedges, texts, autotexts = axes[i].pie(
                [used, unused],
                labels=["Used", "Unused"],
                autopct="%1.1f%%",
                startangle=90,
                colors=colors,
                textprops={'fontsize': 8}
            )
            axes[i].axis('equal')
            axes[i].set_title(f"{zone_name} Utilization", fontsize=10)
    
    # แสดงกราฟ
    st.pyplot(fig)
    
    
    # ---------------------- กราฟขวา (Dept Summary) เต็มหน้า ---------------------
    # เตรียมข้อมูล
    zone1_df = df[df["Zone"] == 1]
    dept_used = zone1_df.groupby("DEPT_NAME")["Pallets"].sum()
    zone1_capacity = zone_capacity[1]
    
    dept_percent = (dept_used / zone1_capacity) * 100
    unused_percent = 100 - dept_percent
    dept_percent = dept_percent.clip(upper=100)
    unused_percent = unused_percent.clip(lower=0)
    
    dept_percent = dept_percent.sort_values(ascending=True)
    unused_percent = unused_percent[dept_percent.index]
    
    # ---------- สร้างกราฟแนวนอนเต็มจอ ----------
    fig2, ax2 = plt.subplots(figsize=(16, max(6, 0.6 * len(dept_percent))))
    bars1 = ax2.barh(dept_percent.index, dept_percent, label="Used", color='steelblue')
    bars2 = ax2.barh(dept_percent.index, unused_percent, left=dept_percent, label="Unused", color='lightgray')
    
    ax2.set_xlabel("Utilization (%)", fontsize=12)
    ax2.set_title("Dept-wise Utilization (vs Zone 1 Capacity)", fontsize=16, pad=15)
    ax2.legend(loc="upper right", fontsize=10)
    
    # Label บน bar
    for bar, percent in zip(bars1, dept_percent):
        ax2.text(bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                 f"{percent:.1f}%", ha='center', va='center', color='white', fontsize=9)
    for bar, percent in zip(bars2, unused_percent):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_y() + bar.get_height() / 2,
                 f"{percent:.1f}%", ha='center', va='center', color='black', fontsize=9)
    
    # ✅ แสดงกราฟแนวนอนเต็มจอ ตรงกลาง
    st.markdown("<div style='text-align: center;'>", unsafe_allow_html=True)
    st.pyplot(fig2, use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)



    st.image("7886Layout.png", use_container_width=True)

