"""Download MONA's raw training data from Hugging Face.

Run from C:\\LLM (each group can run in parallel in its own terminal):
    python -m pipeline.mona_download english     # FineWeb-Edu, 3 shards (~6.5 GB)
    python -m pipeline.mona_download hindi       # Sangraha verified Hindi, files 0-9 (~3.7 GB)
    python -m pipeline.mona_download hinglish    # Sangraha romanized Hindi, 3 files (~0.6 GB)
    python -m pipeline.mona_download sft         # instruction data (smol-smoltalk + Aya)
    python -m pipeline.mona_download hindi_wiki  # 1 file of Hindi Wikipedia, for Hindi Q&A pairs

Files land in data/raw/<group>/ and are skipped if already present; an interrupted
download resumes where it stopped (curl -C -).
"""
import subprocess
import sys
import time
from pathlib import Path

from huggingface_hub import HfApi, get_token

from mona import config

RAW = config.DATA_DIR / "raw"

GROUPS = {
    "english":  ("HuggingFaceFW/fineweb-edu", "sample/10BT", 3, RAW / "english_fineweb"),
    "hindi":    ("ai4bharat/sangraha", "verified/hin", 10, RAW / "hindi_sangraha"),
    "hinglish": ("ai4bharat/sangraha", "synthetic/hin_Latn", 3, RAW / "hinglish_sangraha"),
    "hindi_wiki": ("ai4bharat/sangraha", "synthetic/hin_Deva", 1, RAW / "sft" / "hindi_wiki"),  # SFT Q&A
}
SFT_REPOS = [  # (repo, folder or None, how many files at most)
    ("HuggingFaceTB/smol-smoltalk", "data", 99),
    ("CohereLabs/aya_dataset", None, 99),
]


def files_in(repo, folder):
    api = HfApi()
    entries = api.list_repo_tree(repo, path_in_repo=folder, repo_type="dataset", recursive=folder is None)
    return sorted(e.path for e in entries if e.path.endswith(".parquet"))


def fetch(repo, path, local_dir):
    """Plain HTTPS download with curl: resumable (-C -) and retried.

    (huggingface_hub's default "xet" transfer stalled on this connection.)
    """
    dest = Path(local_dir) / path
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        print(f"  {path}  already present", flush=True)
        return
    part = dest.with_suffix(dest.suffix + ".part")
    url = f"https://huggingface.co/datasets/{repo}/resolve/main/{path}"
    cmd = ["curl", "-sSL", "-C", "-", "--retry", "20", "--retry-delay", "5", "--retry-all-errors",
           "-o", str(part), url]
    token = get_token()
    if token:
        cmd[1:1] = ["-H", f"Authorization: Bearer {token}"]
    t = time.time()
    subprocess.run(cmd, check=True)
    part.rename(dest)
    print(f"  {path}  {dest.stat().st_size / 1e6:,.0f} MB  in {time.time() - t:,.0f} s", flush=True)


def main(group):
    if group == "sft":
        for repo, folder, n in SFT_REPOS:
            try:
                for path in files_in(repo, folder)[:n]:
                    fetch(repo, path, RAW / "sft" / repo.split("/")[1])
            except Exception as e:
                print(f"  {repo}: {type(e).__name__}: {e}")
        return
    repo, folder, n, local = GROUPS[group]
    paths = files_in(repo, folder)
    if group == "hindi":   # Sangraha files are data-0, data-1, ... -> keep numeric order
        paths = sorted(paths, key=lambda p: int(p.rsplit("-", 1)[1].split(".")[0]))
    for path in paths[:n]:
        fetch(repo, path, local)


if __name__ == "__main__":
    for g in sys.argv[1:]:
        print(f"[{g}]", flush=True)
        main(g)
    print("DONE", flush=True)
