from PIL import Image
import sys


def copy_region(src, dst, src_box, dst_xy):
    """
    src_box: (left, bottom, width, height)
    dst_xy: (x, y)
    """

    left, bottom, width, height = src_box

    right = left + width
    top = bottom + height

    part = src.crop((left, bottom, right, top))

    dst.paste(part, dst_xy, part)


def create_sign_texture(input_path, output_path):
    src = Image.open(input_path).convert("RGBA")

    if src.size != (32, 32):
        raise ValueError("Input texture must be exactly 32×32")

    # Transparent output
    dst = Image.new("RGBA", (24, 26), (0, 0, 0, 0))

    #
    # Texture remap
    # Coordinates are:
    # (left, top, width, height)
    #

    copy_region(src, dst, (0, 2, 24, 12), (0, 0))
    copy_region(src, dst, (28, 0, 2, 14), (11, 12))

    dst.save(output_path)
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_sign_texture.py input.png output.png")
        sys.exit(1)

    create_sign_texture(sys.argv[1], sys.argv[2])
