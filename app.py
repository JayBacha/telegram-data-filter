import io, re
from datetime import datetime, timezone, timedelta
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Telegram Number Filter V2", page_icon="📱", layout="wide")
st.title("📱 Telegram Number Filter — Version 2")
st.caption("Phone validation • Authorized status matching • Last-seen filters • Reports")
st.warning("This app does not query Telegram or discover accounts from phone numbers. It matches your list against an authorized status file. Missing data means Unknown, not 'no Telegram account'.")

def normalize_phone(v):
    if pd.isna(v) or not str(v).strip(): return None, "Empty value"
    raw = str(v).strip()
    if re.fullmatch(r"\d+\.0", raw): raw = raw[:-2]
    s = re.sub(r"[\s().\-]", "", raw)
    if s.startswith("00"): s = "+" + s[2:]
    if not re.fullmatch(r"\+?\d+", s): return None, "Unsupported characters"
    digits = s[1:] if s.startswith("+") else s
    if s.startswith("+"):
        if not digits.startswith("91"): return None, "Not an India (+91) number"
        national = digits[2:]
    elif digits.startswith("91") and len(digits) == 12: national = digits[2:]
    else: national = digits
    if len(national) != 10: return None, "Must have 10 national digits"
    if national[0] not in "6789": return None, "Must start with 6, 7, 8, or 9"
    return "+91" + national, None

def read_file(f):
    raw = f.getvalue()
    if len(raw) > 10 * 1024 * 1024: raise ValueError("File exceeds 10 MB.")
    ext = f.name.rsplit(".", 1)[-1].lower()
    if ext == "csv": df = pd.read_csv(io.BytesIO(raw), dtype=str, keep_default_na=False)
    elif ext == "xlsx": df = pd.read_excel(io.BytesIO(raw), dtype=str, keep_default_na=False)
    elif ext == "txt": df = pd.DataFrame({"phone": raw.decode("utf-8-sig", errors="replace").splitlines()})
    else: raise ValueError("Use CSV, XLSX, or TXT.")
    if df.empty: raise ValueError("File has no rows.")
    return df

def col_index(cols, choices):
    for i, c in enumerate(cols):
        if str(c).strip().lower().replace(" ", "_") in choices: return i
    return 0

def parse_seen(v):
    if not str(v).strip(): return None, "", "No last-seen value"
    raw = str(v).strip()
    labels = {
        "recently":"Approximate: recently", "last seen recently":"Approximate: recently",
        "within a week":"Approximate: within a week", "last seen within a week":"Approximate: within a week",
        "within a month":"Approximate: within a month", "last seen within a month":"Approximate: within a month",
        "a long time ago":"Approximate: a long time ago", "last seen a long time ago":"Approximate: a long time ago",
        "hidden":"Hidden / unavailable", "private":"Hidden / unavailable", "unavailable":"Hidden / unavailable"
    }
    if raw.lower() in labels: return None, labels[raw.lower()], "Approximate/hidden; exact-day filter unavailable"
    try:
        ts = pd.to_datetime(raw, utc=True, errors="raise")
        return ts.to_pydatetime(), "", ""
    except Exception: return None, "", "Unrecognized timestamp"

def csv_bytes(df): return df.to_csv(index=False).encode("utf-8-sig")

numbers_file = st.file_uploader("1. Upload phone list (CSV/XLSX/TXT, max 10 MB)", type=["csv","xlsx","txt"], key="numbers")
if numbers_file:
    try: source = read_file(numbers_file)
    except Exception as e: st.error(str(e)); st.stop()
    cols = source.columns.tolist()
    pcol = st.selectbox("Phone-number column", cols, index=col_index(cols, {"phone","phone_number","mobile","mobile_number","number","telephone"}))
    st.subheader("2. Optional: authorized status data")
    st.write("Upload CSV/XLSX with columns for phone, telegram_status, and optionally last_seen. This app does not fetch these fields from Telegram.")
    status_file = st.file_uploader("Authorized status file (optional)", type=["csv","xlsx"], key="status")
    sdf = None
    if status_file:
        try: sdf = read_file(status_file)
        except Exception as e: st.error(str(e)); st.stop()
        scols = sdf.columns.tolist()
        spcol = st.selectbox("Status file: phone column", scols, index=col_index(scols, {"phone","phone_number","mobile","mobile_number","number","telephone"}))
        scol = st.selectbox("Status file: account status column", scols, index=col_index(scols, {"telegram_status","account_status","status"}))
        seen_choices = ["(none)"] + scols
        seen_idx = next((i+1 for i,c in enumerate(scols) if str(c).strip().lower().replace(" ","_") in {"last_seen","last_seen_at","last_seen_date","last_active"}), 0)
        seen_choice = st.selectbox("Status file: last-seen column (optional)", seen_choices, index=seen_idx)
        lcol = None if seen_choice == "(none)" else seen_choice
    if st.button("Process and generate reports", type="primary"):
        now = datetime.now(timezone.utc)
        lookup = {}
        if sdf is not None:
            for _, r in sdf.iterrows():
                n, _ = normalize_phone(r[spcol])
                if not n or n in lookup: continue
                raw_status = str(r[scol]).strip()
                raw_seen = str(r[lcol]).strip() if lcol else ""
                dt, approx, note = parse_seen(raw_seen) if raw_seen else (None, "", "No last-seen value")
                lookup[n] = {"source_status":raw_status, "last_seen_raw":raw_seen,
                             "last_seen_utc":dt.isoformat() if dt else "", "approx":approx, "seen_note":note}
        rows, seen_numbers = [], set()
        for idx, value in enumerate(source[pcol].tolist(), start=2):
            n, err = normalize_phone(value)
            dup = bool(n and n in seen_numbers)
            if n and not dup: seen_numbers.add(n)
            info = lookup.get(n, {}) if n else {}
            rs = info.get("source_status","")
            low = rs.lower().strip()
            if not n: status = "Invalid number"
            elif sdf is None: status = "Unknown — no status data imported"
            elif not rs: status = "Unknown — no matching status record"
            elif low in {"active","exists","account exists","telegram account exists","confirmed"}: status = "Active / confirmed in supplied data"
            elif low in {"no account","not found","no telegram","no telegram account","not registered","inactive"}: status = "No account indicated by supplied data"
            else: status = "Unknown — status not recognized"
            iso = info.get("last_seen_utc","")
            dt = pd.to_datetime(iso, utc=True).to_pydatetime() if iso else None
            if not n: bucket = "Not applicable"
            elif not sdf or not info: bucket = "Unknown"
            elif info.get("approx"): bucket = info["approx"]
            elif dt is None: bucket = "Unknown / unavailable"
            else:
                age = now - dt
                if age < timedelta(0): bucket = "Timestamp in future"
                elif age <= timedelta(hours=24): bucket = "Within 24 hours"
                elif age <= timedelta(days=3): bucket = "Within 3 days"
                elif age <= timedelta(days=7): bucket = "Within 7 days"
                else: bucket = "More than 7 days"
            rows.append({"source_row":idx,"original_value":str(value),"normalized_number":n or "",
                         "validation_status":"Valid format" if n else "Invalid","validation_note":err or "",
                         "duplicate":dup,"telegram_status":status,"source_status_value":rs,
                         "last_seen_raw":info.get("last_seen_raw",""),"last_seen_utc":iso,
                         "last_seen_bucket":bucket,"last_seen_note":info.get("seen_note","")})
        all_df = pd.DataFrame(rows)
        valid = all_df[(all_df.validation_status=="Valid format") & (~all_df.duplicate)].copy()
        invalid = all_df[all_df.validation_status=="Invalid"].copy()
        duplicates = all_df[all_df.duplicate].copy()
        active = all_df[all_df.telegram_status=="Active / confirmed in supplied data"].copy()
        no_account = all_df[all_df.telegram_status=="No account indicated by supplied data"].copy()
        unknown = all_df[all_df.telegram_status.str.startswith("Unknown")].copy()
        summary = pd.DataFrame([
            {"Metric":"Rows processed","Count":len(all_df)},
            {"Metric":"Valid unique numbers","Count":len(valid)},
            {"Metric":"Invalid rows","Count":len(invalid)},
            {"Metric":"Duplicate rows","Count":len(duplicates)},
            {"Metric":"Active / confirmed in supplied data","Count":len(active)},
            {"Metric":"No account indicated by supplied data","Count":len(no_account)},
            {"Metric":"Unknown / not verified","Count":len(unknown)},
            {"Metric":"Last seen within 24 hours","Count":int((all_df.last_seen_bucket=="Within 24 hours").sum())},
            {"Metric":"Last seen within 3 days","Count":int(all_df.last_seen_bucket.isin(["Within 24 hours","Within 3 days"]).sum())},
            {"Metric":"Last seen within 7 days","Count":int(all_df.last_seen_bucket.isin(["Within 24 hours","Within 3 days","Within 7 days"]).sum())}
        ])
        st.session_state["v2"] = {"all":all_df,"valid":valid,"invalid":invalid,"duplicates":duplicates,
                                  "active":active,"no_account":no_account,"unknown":unknown,"summary":summary,
                                  "processed":now.strftime("%Y-%m-%d %H:%M UTC")}

if "v2" in st.session_state:
    d = st.session_state["v2"]; a = d["all"]
    st.divider(); st.header("3. Results and filters")
    c1,c2,c3,c4 = st.columns(4)
    c1.metric("Rows processed",len(a)); c2.metric("Valid unique",len(d["valid"]))
    c3.metric("Active / confirmed",len(d["active"])); c4.metric("Unknown",len(d["unknown"]))
    st.caption("Processed at: " + d["processed"])
    statuses = sorted(a.telegram_status.unique().tolist())
    buckets = sorted(a.last_seen_bucket.unique().tolist())
    chosen_status = st.multiselect("Filter by Telegram status", statuses, default=statuses)
    chosen_buckets = st.multiselect("Filter by last seen", buckets, default=buckets)
    filtered = a[a.telegram_status.isin(chosen_status) & a.last_seen_bucket.isin(chosen_buckets)].copy()
    st.subheader(f"Filtered records ({len(filtered)})")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    tabs = st.tabs(["All","Active / confirmed","No account indicated","Unknown","Invalid","Duplicates","Summary"])
    frames = [a,d["active"],d["no_account"],d["unknown"],d["invalid"],d["duplicates"],d["summary"]]
    for tab, frame in zip(tabs,frames):
        with tab: st.dataframe(frame,use_container_width=True,hide_index=True)
    st.subheader("4. Download reports")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.download_button("filtered.csv",csv_bytes(filtered),"filtered.csv","text/csv")
        st.download_button("active_confirmed.csv",csv_bytes(d["active"]),"active_confirmed.csv","text/csv")
    with c2:
        st.download_button("no_account_indicated.csv",csv_bytes(d["no_account"]),"no_account_indicated.csv","text/csv")
        st.download_button("unknown.csv",csv_bytes(d["unknown"]),"unknown.csv","text/csv")
    with c3:
        st.download_button("invalid.csv",csv_bytes(d["invalid"]),"invalid.csv","text/csv")
        st.download_button("duplicates.csv",csv_bytes(d["duplicates"]),"duplicates.csv","text/csv")
        b = io.BytesIO()
        with pd.ExcelWriter(b,engine="openpyxl") as w:
            for name, frame in [("All Records",a),("Filtered",filtered),("Active Confirmed",d["active"]),
                                ("No Account Indicated",d["no_account"]),("Unknown",d["unknown"]),
                                ("Invalid",d["invalid"]),("Duplicates",d["duplicates"]),("Summary",d["summary"])]:
                frame.to_excel(w,sheet_name=name,index=False)
        st.download_button("all_reports.xlsx",b.getvalue(),"telegram_number_filter_v2_reports.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
st.caption("Use only data you are authorized to process. Supplied statuses are not independently verified. Approximate last-seen labels cannot be treated as exact time windows.")
