st.markdown("---")
st.subheader("🔒 Shutdown checklist")
if st.button("Save & prepare to close"):
    try:
        ts = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H%M%SZ")
        commit_msg = f"snapshot: {ts}"
        # Add and commit
        add = subprocess.run(["git", "add", "-A"], capture_output=True, text=True)
        commit = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True)
        # Push
        push = subprocess.run(["git", "push"], capture_output=True, text=True)
        # Backup branch
        backup_branch = f"backup/{ts}"
        branch = subprocess.run(["git", "branch", backup_branch], capture_output=True, text=True)
        push_branch = subprocess.run(["git", "push", "-u", "origin", backup_branch], capture_output=True, text=True)
        # Tag
        tag = f"snapshot-{ts}"
        tag_create = subprocess.run(["git", "tag", "-a", tag, "-m", f"workspace snapshot {ts}"], capture_output=True, text=True)
        push_tag = subprocess.run(["git", "push", "origin", tag], capture_output=True, text=True)
        # Lockfile
        freeze = subprocess.run(["pip", "freeze"], capture_output=True, text=True)
        with open("requirements.lock.txt", "w") as f:
            f.write(freeze.stdout)
        add_lock = subprocess.run(["git", "add", "requirements.lock.txt"], capture_output=True, text=True)
        commit_lock = subprocess.run(["git", "commit", "-m", f"chore: add requirements.lock.txt ({ts})"], capture_output=True, text=True)
        push_lock = subprocess.run(["git", "push"], capture_output=True, text=True)
        st.success(f"Shutdown snapshot complete!\nBranch: {backup_branch}\nTag: {tag}")
    except Exception as e:
        st.error(f"Shutdown checklist failed: {e}")
import subprocess
import datetime
st.markdown("---")
st.subheader("💾 Save Git Snapshot")
if st.button("Save Git Snapshot"):
    try:
        ts = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
        commit_msg = f"snapshot: {ts}"
        add = subprocess.run(["git", "add", "-A"], capture_output=True, text=True, check=False)
        commit = subprocess.run(["git", "commit", "-m", commit_msg], capture_output=True, text=True, check=False)
        push = subprocess.run(["git", "push"], capture_output=True, text=True, check=False)
        if push.returncode == 0:
            st.success(f"Snapshot saved and pushed! Commit: {commit_msg}")
        elif commit.returncode == 1 and 'nothing to commit' in commit.stderr:
            st.info("No changes to commit.")
        else:
            st.error(f"Git push failed: {push.stderr}")
    except Exception as e:
        st.error(f"Snapshot failed: {e}")
import io
import pandas as pd
import streamlit as st
import plotly.express as px

st.set_page_config(page_title="CDR Analyzer", layout="wide")
st.title("CDR Analyzer")

def best_sep(sample:str)->str:
    return "\t" if sample.count("\t") > sample.count(",") else ","

uploaded = st.file_uploader("Upload CDR (CSV/TSV/TXT)", type=["csv","tsv","txt"])
if not uploaded:
    st.info("Upload a file to begin.")
    st.stop()

sample = uploaded.read(4096).decode("utf-8", errors="ignore")
sep = best_sep(sample)
uploaded.seek(0)
df = pd.read_csv(uploaded, sep=sep, low_memory=False)

st.success(f"Loaded {len(df):,} rows (detected {'TAB' if sep=='\\t' else 'COMMA'})")
st.dataframe(df.head(50), use_container_width=True)
