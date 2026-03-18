import json
import os
import re
import argparse
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class K8Record:
    issue: str
    date: str
    time: str
    numbers: Tuple[int, ...]
    total: Optional[int]
    size: Optional[str]
    odd_even: Optional[str]
    up_down: Optional[str]
    parity: Optional[str]


ISSUE_RE = re.compile(r"^\d{7}$")
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
TIME_RE = re.compile(r"^\d{2}:\d{2}$")
NUM_RE = re.compile(r"^\d{2}$")


def _read_text(path: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "gbk", "gb18030"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _tokenize(text: str) -> List[str]:
    return [t for t in re.split(r"[\s\t\r\n]+", text) if t]


def _is_issue(tok: str) -> bool:
    return bool(ISSUE_RE.match(tok))


def _parse_records(tokens: Sequence[str]) -> List[K8Record]:
    records: List[K8Record] = []
    i = 0
    while i < len(tokens):
        if not _is_issue(tokens[i]):
            i += 1
            continue

        issue = tokens[i]
        if i + 2 >= len(tokens):
            break
        if not DATE_RE.match(tokens[i + 1]) or not TIME_RE.match(tokens[i + 2]):
            i += 1
            continue

        date = tokens[i + 1]
        time = tokens[i + 2]
        j = i + 3

        nums: List[int] = []
        while j < len(tokens) and len(nums) < 20:
            if NUM_RE.match(tokens[j]):
                nums.append(int(tokens[j]))
                j += 1
                continue
            break

        if len(nums) != 20:
            i += 1
            continue

        total: Optional[int] = None
        size: Optional[str] = None
        odd_even: Optional[str] = None
        up_down: Optional[str] = None
        parity: Optional[str] = None

        if j < len(tokens) and re.fullmatch(r"\d{1,4}", tokens[j]):
            total = int(tokens[j])
            if j + 4 < len(tokens):
                size = tokens[j + 1]
                odd_even = tokens[j + 2]
                up_down = tokens[j + 3]
                parity = tokens[j + 4]
                j = j + 5
            else:
                j += 1

        record = K8Record(
            issue=issue,
            date=date,
            time=time,
            numbers=tuple(nums),
            total=total,
            size=size,
            odd_even=odd_even,
            up_down=up_down,
            parity=parity,
        )
        records.append(record)
        i = j

    return records


def _freq(window: Iterable[K8Record]) -> Dict[int, int]:
    counts = {n: 0 for n in range(1, 81)}
    for r in window:
        for n in r.numbers:
            counts[n] += 1
    return counts


def _top_k(counts: Dict[int, int], k: int) -> List[Tuple[int, int]]:
    return sorted(counts.items(), key=lambda x: (-x[1], x[0]))[:k]


def _bottom_k(counts: Dict[int, int], k: int) -> List[Tuple[int, int]]:
    return sorted(counts.items(), key=lambda x: (x[1], x[0]))[:k]


def _tail_dist(window: Iterable[K8Record]) -> Dict[int, int]:
    d = {i: 0 for i in range(10)}
    for r in window:
        for n in r.numbers:
            d[n % 10] += 1
    return d


def _consecutive_pairs(nums: Sequence[int]) -> int:
    s = sorted(nums)
    pairs = 0
    for a, b in zip(s, s[1:]):
        if b == a + 1:
            pairs += 1
    return pairs


def _format_analysis(window: Sequence[K8Record]) -> str:
    last = window[-1]
    prev = window[-2] if len(window) >= 2 else None

    counts = _freq(window)
    hot = _top_k(counts, 10)
    cold = _bottom_k(counts, 10)

    total_numbers = len(window) * 20
    odd = sum(1 for r in window for n in r.numbers if n % 2 == 1)
    even = total_numbers - odd
    small = sum(1 for r in window for n in r.numbers if n <= 40)
    big = total_numbers - small

    totals = [r.total for r in window if r.total is not None]
    total_stat = None
    if totals:
        total_stat = (min(totals), sum(totals) / len(totals), max(totals))

    tail = _tail_dist(window)
    tail_sorted = sorted(tail.items(), key=lambda x: (-x[1], x[0]))

    cons = _consecutive_pairs(last.numbers)
    overlap = None
    if prev is not None:
        overlap = len(set(last.numbers).intersection(prev.numbers))

    hot_str = "，".join([f"{n:02d}({c})" for n, c in hot])
    cold_str = "，".join([f"{n:02d}({c})" for n, c in cold])
    tail_str = "，".join([f"{d}:{c}" for d, c in tail_sorted])

    lines: List[str] = []
    lines.append(f"统计窗口：{len(window)}期（最新期号 {last.issue}）")
    lines.append("")
    lines.append("1) 号码冷热（出现次数）")
    lines.append(f"- 热号Top10：{hot_str}")
    lines.append(f"- 冷号Bottom10：{cold_str}")
    lines.append("")
    lines.append("2) 结构分布（按窗口内所有号码统计）")
    lines.append(f"- 奇偶比：奇{odd} / 偶{even}")
    lines.append(f"- 大小比（1-40 / 41-80）：小{small} / 大{big}")
    lines.append(f"- 尾数分布（0-9）：{tail_str}")
    lines.append("")
    lines.append("3) 最新一期形态")
    lines.append(f"- 最新一期连号对数：{cons}")
    if overlap is not None:
        lines.append(f"- 与上一期重号数量：{overlap}")
    if total_stat is not None:
        mn, avg, mx = total_stat
        lines.append(f"- 总和区间/均值：min={mn} / avg={avg:.1f} / max={mx}")
    lines.append("")
    lines.append("4) 提示")
    lines.append("- 快乐8开奖是随机事件，历史统计只能描述分布特征，不构成稳定可复制的“预测优势”。")
    lines.append("- 建议把本结果当作数据解读模板，而不是下注依据。")
    return "\n".join(lines)


def _format_prompt(window: Sequence[K8Record]) -> str:
    lines: List[str] = []
    lines.append(f"以下是最近{len(window)}期快乐8开奖结果（每期20个号码，范围1-80）：")
    for r in window:
        nums = " ".join(f"{n:02d}" for n in r.numbers)
        tail = ""
        if r.total is not None:
            tail = f" | 总和:{r.total} 大小:{r.size} 单双:{r.odd_even} 上下盘:{r.up_down} 奇偶盘:{r.parity}"
        lines.append(f"{r.issue} {r.date} {r.time} | {nums}{tail}")
    lines.append("")
    lines.append("请做统计分析：")
    lines.append("1) 热号/冷号（出现次数）；2) 奇偶比、大小比（1-40/41-80）；3) 尾数分布；4) 最新一期连号与重号；5) 风险提示（不做必中预测）。")
    return "\n".join(lines)


def build_sft_sharegpt(records: Sequence[K8Record], window: int = 30) -> List[dict]:
    system = "你是快乐8数据分析助手，只做统计分析与解释，不承诺预测准确性。输出要结构化、可复核。"
    samples: List[dict] = []
    if len(records) < window:
        return samples

    for end in range(window - 1, len(records)):
        w = records[end - window + 1 : end + 1]
        samples.append(
            {
                "system": system,
                "conversations": [
                    {"from": "human", "value": _format_prompt(w)},
                    {"from": "gpt", "value": _format_analysis(w)},
                ]
            }
        )
    return samples


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--input", default=os.path.join(os.getcwd(), "1"))
    p.add_argument("--window", type=int, default=30)
    p.add_argument("--out-dir", default=os.getcwd())
    args = p.parse_args()

    src_path = args.input
    out_dir = args.out_dir
    out_records = os.path.join(out_dir, "k8_records.json")
    out_sft = os.path.join(out_dir, "k8_sft_sharegpt.json")

    text = _read_text(src_path)
    tokens = _tokenize(text)
    records = _parse_records(tokens)

    with open(out_records, "w", encoding="utf-8") as f:
        json.dump([r.__dict__ for r in records], f, ensure_ascii=False, indent=2)

    samples = build_sft_sharegpt(records, window=args.window)
    with open(out_sft, "w", encoding="utf-8") as f:
        json.dump(samples, f, ensure_ascii=False, indent=2)

    print(f"parsed_records={len(records)}")
    print(f"sft_samples={len(samples)}")
    if records:
        print(f"latest_issue={records[0].issue}..{records[-1].issue}")
    print(f"wrote: {out_records}")
    print(f"wrote: {out_sft}")


if __name__ == "__main__":
    main()
