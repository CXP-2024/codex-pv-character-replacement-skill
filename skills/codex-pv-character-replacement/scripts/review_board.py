"""Make a source / replacement / 50% overlay review board (Pillow required)."""
from pathlib import Path
import argparse
from PIL import Image, ImageDraw, ImageFont


def make_board(source, edited, output, frame, allow_resize=False):
    with Image.open(source) as im:
        a = im.convert("RGB")
    with Image.open(edited) as im:
        b = im.convert("RGB")
    if a.size != b.size:
        if not allow_resize:
            raise ValueError("Different sizes; explicitly allow same-aspect-ratio resize")
        if abs(a.width / a.height - b.width / b.height) > 0.002:
            raise ValueError("Aspect ratio mismatch; do not distort character geometry")
        b = b.resize(a.size, Image.Resampling.LANCZOS)
    label_height = 40
    board = Image.new("RGB", (a.width * 3, a.height + label_height), "white")
    draw = ImageDraw.Draw(board)
    for i, (label, im) in enumerate([
        ("source", a), ("replacement", b), ("50% overlay", Image.blend(a, b, 0.5))
    ]):
        x = i * a.width
        board.paste(im, (x, label_height))
        draw.text((x + 8, 12), f"A{frame} | {label}", fill="black",
                  font=ImageFont.load_default())
    # Exclusive open: never silently replace an existing review artifact.
    with Path(output).open("xb") as stream:
        board.save(stream, format="PNG")
    return board.size


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("source")
    p.add_argument("edited")
    p.add_argument("output", help="PNG output; existing files are not overwritten")
    p.add_argument("--frame", type=int, required=True)
    p.add_argument("--allow-resize", action="store_true")
    args = p.parse_args()
    print(make_board(args.source, args.edited, args.output, args.frame, args.allow_resize))
