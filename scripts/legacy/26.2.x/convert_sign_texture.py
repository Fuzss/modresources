from PIL import Image
import sys


def copy_region(src, dst, src_box, dst_xy, flip=False):
    """
    src_box: (left, bottom, width, height)
    dst_xy: (x, y)
    """

    left, bottom, width, height = src_box

    right = left + width
    top = bottom + height

    part = src.crop((left, bottom, right, top))

    if flip:
        part = part.transpose(Image.FLIP_TOP_BOTTOM)

    dst.paste(part, dst_xy, part)


def convert_sign_texture(input_path, output_path):
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
    copy_region(src, dst, (2, 0, 24, 2), (0, 0))
    # Front
    copy_region(src, dst, (2, 2, 24, 12), (0, 2))
    # Left
    copy_region(src, dst, (0, 2, 2, 12), (24, 16))
    # Bottom
    copy_region(src, dst, (26, 0, 24, 2), (0, 28), flip=True)
    # Back
    copy_region(src, dst, (28, 2, 24, 12), (0, 16))
    # Right
    copy_region(src, dst, (26, 2, 2, 12), (24, 2))

    # Top
    copy_region(src, dst, (2, 14, 2, 2), (28, 14))
    # Front
    copy_region(src, dst, (2, 16, 2, 14), (28, 0))
    # Left
    copy_region(src, dst, (0, 16, 2, 14), (30, 16))
    # Bottom
    copy_region(src, dst, (4, 14, 2, 2), (28, 30), flip=True)
    # Back
    copy_region(src, dst, (6, 16, 2, 14), (28, 16))
    # Right
    copy_region(src, dst, (4, 16, 2, 14), (30, 0))

    dst.save(output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python convert_sign_texture.py input.png output.png")
        sys.exit(1)

    convert_sign_texture(sys.argv[1], sys.argv[2])
