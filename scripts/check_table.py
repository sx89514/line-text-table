"""檢查要貼到 LINE 的框線表格會不會歪。

用法：
    python check_table.py table.txt
    python check_table.py table.txt --max-width 13

計寬規則（依 2026-09-14 LINE Android 實測）：
- 框線字元、中日文字、全形英數、全形空白、● 都算 1 格。
- 半形字（ASCII 英數、半形空白、標點）算 0.5 格，而且寬度會跟全形不成比例 → 一律報錯。
- 其他符號（○ ✕ ★ emoji…）寬度沒實測過 → 報警告。
"""
import argparse
import sys
import unicodedata

# 已在 LINE 手機實測，確定跟中文字一樣寬
VERIFIED_SYMBOLS = {"●"}

BOX_START, BOX_END = 0x2500, 0x257F
# 會形成「直線」位置的框線字元
VERTICAL = set("│┼┬┴├┤┌┐└┘")


def char_kind(ch):
    code = ord(ch)
    if BOX_START <= code <= BOX_END or ch in VERIFIED_SYMBOLS:
        return "full"
    if ch == "　":
        return "full"
    eaw = unicodedata.east_asian_width(ch)
    if eaw in ("W", "F"):
        return "full"
    if eaw in ("Na", "H") or ch == " ":
        return "half"
    return "unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    parser.add_argument("--max-width", type=int, default=13)
    args = parser.parse_args()

    with open(args.path, encoding="utf-8") as f:
        lines = [line.rstrip("\r\n") for line in f]

    errors, warnings = [], []
    blocks = []  # 連續的框線列算同一張表：[(行號, 寬度, 直線位置), ...]
    in_table = False

    for no, line in enumerate(lines, 1):
        if not line.strip():
            in_table = False
            continue
        width = 0
        verticals = []
        half, unknown = [], []
        for ch in line:
            kind = char_kind(ch)
            if kind == "half":
                half.append(ch)
            elif kind == "unknown":
                unknown.append(ch)
            if ch in VERTICAL:
                verticals.append(width)
            width += 1
        if half:
            errors.append(f"第 {no} 行有 {len(half)} 個半形字 {''.join(dict.fromkeys(half))!r}，要換成全形")
        for ch in dict.fromkeys(unknown):
            warnings.append(f"第 {no} 行的 {ch!r}（U+{ord(ch):04X}）寬度未實測，可能會歪")
        if width > args.max_width:
            errors.append(f"第 {no} 行寬 {width} 格，超過手機上限 {args.max_width} 格，會換行")
        if line[0] in VERTICAL:
            if not in_table or line[0] == "┌":
                blocks.append([])
                in_table = True
            blocks[-1].append((no, width, verticals))
        else:
            in_table = False

    for rows in blocks:
        base_no, base_width, base_vert = rows[0]
        for no, width, vert in rows[1:]:
            if width != base_width:
                errors.append(f"第 {no} 行寬 {width} 格，跟第 {base_no} 行的 {base_width} 格不同")
            elif vert != base_vert:
                errors.append(f"第 {no} 行的直線位置 {vert} 跟第 {base_no} 行 {base_vert} 對不上")

    for no, line in enumerate(lines, 1):
        if line.strip():
            print(f"{no:>3} | 寬 {sum(1 for _ in line):>2} | {line}")
    print()
    for msg in errors:
        print("錯誤：" + msg)
    for msg in warnings:
        print("警告：" + msg)
    if not errors and not warnings:
        print("通過：寬度一致、直線對齊、沒有半形字")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
