"""PixelMaker CLI entry point."""
import argparse
import sys
from pathlib import Path

from PIL import Image

from pixelmaker.core.errors import GridNotDetectedError, GridHintConflictError
from pixelmaker.core.grid_detector import detect_grid
from pixelmaker.core.extractor import extract_pixel_art


def main():
    parser = argparse.ArgumentParser(
        prog="pixelmaker",
        description="Extract pixel art from grid-overlay images",
    )
    subparsers = parser.add_subparsers(dest="command")

    extract_parser = subparsers.add_parser("extract", help="Extract pixel art from grid image")
    extract_parser.add_argument("input", help="Input image path")
    extract_parser.add_argument("output", help="Output image path")
    extract_parser.add_argument("--grid-size", type=int, default=None, help="Expected grid size (NxN)")
    extract_parser.add_argument("--scale", type=int, default=None, help="Scale factor for output (nearest neighbor)")
    extract_parser.add_argument("--ref", type=str, default=None, help="Reference image for grid size inference")
    extract_parser.add_argument("--force-grid-size", type=int, default=None, help="Force grid size, ignoring auto-detection")
    extract_parser.add_argument("--transparent-color", type=str, default=None, help="Make edge-connected pixels of this color transparent (hex, e.g. '#000000')")
    extract_parser.add_argument("--transparent-bg", action="store_true", default=False, help="Auto-detect background color from edges and make it transparent")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "extract":
        try:
            # Mutual exclusion check
            transparent_color_str = getattr(args, 'transparent_color', None)
            transparent_bg = getattr(args, 'transparent_bg', False)
            if transparent_color_str and transparent_bg:
                print("Error: --transparent-color and --transparent-bg cannot be used together.", file=sys.stderr)
                sys.exit(1)

            # Parse hex color
            transparent_color = None
            if transparent_color_str:
                hex_str = transparent_color_str.lstrip('#')
                transparent_color = (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))

            input_path = Path(args.input)
            if not input_path.exists():
                print(f"Error: Input file not found: {args.input}", file=sys.stderr)
                sys.exit(1)

            image = Image.open(str(input_path))
            image.load()

            ref_image = None
            if args.ref:
                ref_path = Path(args.ref)
                if not ref_path.exists():
                    print(f"Error: Reference file not found: {args.ref}", file=sys.stderr)
                    sys.exit(1)
                ref_image = Image.open(str(ref_path))
                ref_image.load()

            # Run detection first so we can emit warnings before extraction
            detection = detect_grid(
                image,
                grid_size=args.grid_size,
                ref_image=ref_image,
                force_grid_size=args.force_grid_size,
            )

            for warning in detection.warnings:
                print(warning, file=sys.stderr)

            result = extract_pixel_art(
                image,
                grid_size=args.grid_size,
                ref_image=ref_image,
                force_grid_size=args.force_grid_size,
                scale=args.scale,
                transparent_color=transparent_color,
                transparent_bg=transparent_bg,
            )

            output_path = Path(args.output)
            result.save(str(output_path))

        except GridNotDetectedError as e:
            print(f"GridNotDetectedError: {e}", file=sys.stderr)
            sys.exit(1)
        except GridHintConflictError as e:
            print(f"GridHintConflictError: {e}", file=sys.stderr)
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
