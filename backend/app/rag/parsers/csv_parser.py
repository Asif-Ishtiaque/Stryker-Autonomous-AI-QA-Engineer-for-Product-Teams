from __future__ import annotations

import io

import pandas as pd


def parse_csv(raw: bytes, filename: str) -> list[str]:
    df = pd.read_csv(io.BytesIO(raw))
    blocks = [f"{filename} columns: {', '.join(df.columns.astype(str))}"]

    for _, row in df.iterrows():
        pairs = [f"{col}={row[col]}" for col in df.columns]
        blocks.append(", ".join(pairs))

    return blocks
