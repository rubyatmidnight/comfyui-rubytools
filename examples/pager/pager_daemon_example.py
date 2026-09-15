"""Minimal pager daemon: watch an inbox folder, render text pages to 1-bit PNG,
and hand each PNG to a print command of your choosing.

This is a sample. Point PRINT_COMMAND at whatever prints a PNG on your
printer, for example:
    ["TiMini-Print-Command-Line.exe", "--bluetooth", "MyPrinter", "{file}"]
    ["lp", "-o", "fit-to-page", "{file}"]
    ["python", "my_escpos_print.py", "{file}"]
"{file}" is replaced with the PNG path.

Inbox file format (what the ComfyUI "Pager: Send Page" node writes):
    From: Sender          <- optional header lines until the first blank line
    Icon: fox             <- optional: fox | cat | none

    Body text.
A .png in the inbox is printed as-is.

Run:  python pager_daemon_example.py [--inbox PATH] [--once]
Log:  pager.jsonl next to the inbox (the node's wait_for_print reads this).
"""
import argparse
import json
import shutil
import subprocess
import textwrap
import time
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

PRINT_COMMAND = ["echo", "would print {file}"]   # <- replace with your printer command
WIDTH = 384                                       # dots across the strip (384 = 57 mm)
MARGIN = 10
ICONS = {
    "fox": ["  /\\_/\\ ", " ( o.o )", "  > ^ < "],
    "cat": ["  /\\_/\\ ", " ( =.= )", "  (\")_(\")"],
}


def font(size, bold=False):
    for name in (("consolab.ttf" if bold else "consola.ttf"), "DejaVuSansMono-Bold.ttf" if bold else "DejaVuSansMono.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def parse_message(text):
    headers, body = {}, text
    head, sep, rest = text.partition("\n\n")
    if sep and all(":" in line for line in head.splitlines() if line.strip()):
        for line in head.splitlines():
            key, _, value = line.partition(":")
            headers[key.strip().lower()] = value.strip()
        body = rest
    return headers, body.strip("\n")


def render(headers, body, out_path):
    body_font, head_font, small_font = font(22), font(20, bold=True), font(17)
    sender = headers.get("from", "pager")
    stamp = datetime.now().strftime("%a %d %b  %H:%M")
    icon = ICONS.get(headers.get("icon", "none").lower(), [])
    probe = ImageDraw.Draw(Image.new("1", (10, 10), 1))
    columns = max(10, int((WIDTH - 2 * MARGIN) // probe.textlength("M", font=body_font)))
    lines = []
    for paragraph in body.splitlines() or [""]:
        lines.extend(textwrap.wrap(paragraph, columns) or [""])
    line_h, header_h = 27, (max(60 if icon else 0, 50) + 8)
    image = Image.new("1", (WIDTH, MARGIN + header_h + len(lines) * line_h + 40 + MARGIN), 1)
    draw = ImageDraw.Draw(image)
    y, x_text = MARGIN, MARGIN
    if icon:
        for i, row in enumerate(icon):
            draw.text((MARGIN, y + i * 20), row, font=head_font, fill=0)
        x_text = MARGIN + 110
    draw.text((x_text, y), sender, font=head_font, fill=0)
    draw.text((x_text, y + 26), stamp, font=small_font, fill=0)
    y += header_h
    draw.line((MARGIN, y - 4, WIDTH - MARGIN, y - 4), fill=0, width=2)
    for line in lines:
        draw.text((MARGIN, y), line, font=body_font, fill=0)
        y += line_h
    y += 18
    for x in range(MARGIN, WIDTH - MARGIN, 12):
        draw.line((x, y, x + 6, y), fill=0, width=1)
    out_path.parent.mkdir(exist_ok=True)
    image.save(out_path)
    return out_path


def print_png(path):
    command = [part.replace("{file}", str(path)) for part in PRINT_COMMAND]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    return result.returncode == 0, (result.stdout + result.stderr).strip()[-600:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inbox", default="inbox")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll", type=float, default=2.0)
    args = parser.parse_args()
    inbox = Path(args.inbox).resolve()
    base = inbox.parent
    done, failed, rendered, log_path = base / "done", base / "failed", base / "rendered", base / "pager.jsonl"
    for folder in (inbox, done, failed, rendered):
        folder.mkdir(parents=True, exist_ok=True)

    def log(event, **fields):
        record = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event, **fields}
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(record, flush=True)

    while True:
        for path in sorted(p for p in inbox.iterdir() if p.suffix.lower() in {".txt", ".png"} and not p.name.startswith(".")):
            try:
                if path.suffix.lower() == ".png":
                    bitmap = path
                else:
                    headers, body = parse_message(path.read_text(encoding="utf-8", errors="replace"))
                    bitmap = render(headers, body, rendered / (path.stem + ".png"))
            except Exception as error:
                log("render_failed", file=path.name, error=repr(error))
                shutil.move(str(path), failed / path.name)
                continue
            for attempt in range(1, 4):
                ok, output = print_png(bitmap)
                if ok:
                    log("printed", file=path.name, attempt=attempt)
                    shutil.move(str(path), done / path.name)
                    break
                log("print_failed", file=path.name, attempt=attempt, error=output)
                time.sleep(5 * attempt)
            else:
                shutil.move(str(path), failed / path.name)
        if args.once:
            break
        time.sleep(args.poll)


if __name__ == "__main__":
    main()
