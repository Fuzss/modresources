from PIL import Image
import sys


def copy_region(src, dst, src_box, dst_xy, rotate=False):
    """
    src_box: (left, bottom, width, height)
    dst_xy: (x, y)
    """

    left, bottom, width, height = src_box

    right = left + width
    top = bottom + height

    part = src.crop((left, bottom, right, top))

    if rotate:
        part = part.rotate(180, expand=False)

    dst.paste(part, dst_xy, part)


def convert_hanging_sign_texture(input_path, output_path):
    src = Image.open(input_path).convert("RGBA")

    if src.size != (64, 32):
        raise ValueError("Input texture must be exactly 64×32")

    # Transparent output
    dst = Image.new("RGBA", (32, 32), (0, 0, 0, 0))

    #
    # Texture remap
    # Coordinates are:
    # (left, top, width, height)
    #

    # Top
    copy_region(src, dst, (4, 0, 16, 4), (0, 0))
    # Front
    copy_region(src, dst, (4, 4, 16, 2), (0, 4))
    # Left
    copy_region(src, dst, (0, 4, 4, 2), (16, 7))
    # Bottom
    copy_region(src, dst, (20, 0, 16, 4), (0, 9), rotate=True)
    # Back
    copy_region(src, dst, (24, 4, 16, 2), (0, 7))
    # Right
    copy_region(src, dst, (20, 4, 4, 2), (16, 4))

    # Top
    copy_region(src, dst, (2, 12, 14, 2), (2, 14))
    # Front
    copy_region(src, dst, (2, 14, 14, 10), (2, 16))
    # Left
    copy_region(src, dst, (0, 14, 2, 10), (0, 16))
    # Bottom
    copy_region(src, dst, (16, 12, 14, 2), (2, 26), rotate=True)
    # Back
    copy_region(src, dst, (18, 14, 14, 10), (18, 16))
    # Right
    copy_region(src, dst, (16, 14, 2, 10), (16, 16))

    # Chains
    copy_region(src, dst, (0, 6, 9, 6), (22, 7))
    copy_region(src, dst, (14, 6, 12, 6), (20, 0))

    dst.save(output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_hanging_sign_texture.py input.png output.png")
        sys.exit(1)

    convert_hanging_sign_texture(sys.argv[1], sys.argv[2])
