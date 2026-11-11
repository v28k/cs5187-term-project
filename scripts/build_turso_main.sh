#!/usr/bin/env bash
# Build pyturso from Turso `main` into /root/arbor/pyturso-main (used by src/configs/turso_main.yaml)
# and the tursodb shell (for re-checking reproducers). About 20-30 min on 2 cores.
#   scripts/build_turso_main.sh [turso checkout, default /root/arbor/turso-src]
set -euo pipefail
SRC=${1:-/root/arbor/turso-src}
export PATH=$HOME/.cargo/bin:$PATH
[ -d "$SRC" ] || git clone https://github.com/tursodatabase/turso "$SRC"
git -C "$SRC" pull -q --ff-only || true
git -C "$SRC" log -1 --format='turso main %h %ci'
python3 -m pip install -q maturin
( cd "$SRC/bindings/python" && maturin build --release -j 2 )
W=$(ls -t "$SRC"/target/wheels/*.whl | head -1)
rm -rf /root/arbor/pyturso-main && python3 -m pip install -q --target /root/arbor/pyturso-main "$W"
( cd "$SRC" && cargo build --bin tursodb -j 2 )
echo "pyturso main: /root/arbor/pyturso-main; shell: $SRC/target/debug/tursodb"
