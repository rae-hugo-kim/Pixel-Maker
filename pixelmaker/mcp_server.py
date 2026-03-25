"""PixelMaker MCP Server."""
from __future__ import annotations

from PIL import Image

from pixelmaker.core.errors import GridHintConflictError, GridNotDetectedError
from pixelmaker.core.extractor import extract_pixel_art
from pixelmaker.core.grid_detector import detect_grid

from mcp.server.fastmcp import FastMCP


mcp_app = FastMCP("pixelmaker")


def extract_pixel_art_tool(
    input_path: str,
    output_path: str,
    grid_size: int | None = None,
    ref_path: str | None = None,
    force_grid_size: int | None = None,
    scale: int | None = None,
    transparent_color: str | None = None,
    transparent_bg: bool = False,
) -> dict:
    """Extract pixel art from a grid-overlay image.

    Returns dict with output_path and metadata, or error dict on failure.
    """
    try:
        # Parse hex color if provided
        tc_tuple = None
        if transparent_color:
            hex_str = transparent_color.lstrip('#')
            tc_tuple = (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))

        image = Image.open(input_path)
        image.load()

        ref_image = None
        if ref_path:
            ref_image = Image.open(ref_path)
            ref_image.load()

        # Run detection first for metadata
        detection = detect_grid(
            image,
            grid_size=grid_size,
            ref_image=ref_image,
            force_grid_size=force_grid_size,
        )

        # Run extraction
        result_img = extract_pixel_art(
            image,
            grid_size=grid_size,
            ref_image=ref_image,
            force_grid_size=force_grid_size,
            scale=scale,
            transparent_color=tc_tuple,
            transparent_bg=transparent_bg,
        )

        # Save output
        result_img.save(output_path)

        # Count unique colors
        pixel_set = set()
        for y in range(result_img.height):
            for x in range(result_img.width):
                pixel_set.add(result_img.getpixel((x, y)))
        unique_colors = len(pixel_set)

        # grid_detected: high-confidence auto-detection (not fallback, not force)
        grid_detected = detection.confidence > 0.5

        # fallback_used: low confidence AND a grid_size hint was provided (not force override)
        fallback_used = (
            detection.confidence <= 0.5
            and grid_size is not None
            and force_grid_size is None
        )

        return {
            "output_path": output_path,
            "confidence": detection.confidence,
            "grid_detected": grid_detected,
            "fallback_used": fallback_used,
            "grid_size": detection.grid_size,
            "unique_colors": unique_colors,
            "warnings": detection.warnings,
        }

    except GridNotDetectedError as e:
        return {
            "error": True,
            "is_error": True,
            "error_type": "GridNotDetectedError",
            "message": str(e),
        }
    except GridHintConflictError as e:
        return {
            "error": True,
            "is_error": True,
            "error_type": "GridHintConflictError",
            "message": str(e),
        }


@mcp_app.tool(name="extract_pixel_art")
def extract_pixel_art_mcp(
    input_path: str,
    output_path: str,
    grid_size: int | None = None,
    ref_path: str | None = None,
    force_grid_size: int | None = None,
    scale: int | None = None,
    transparent_color: str | None = None,
    transparent_bg: bool = False,
) -> str:
    """Extract pixel art from a grid-overlay image."""
    import json
    result = extract_pixel_art_tool(
        input_path, output_path, grid_size, ref_path, force_grid_size, scale,
        transparent_color, transparent_bg,
    )
    return json.dumps(result)


if __name__ == "__main__":
    mcp_app.run()
