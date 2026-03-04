"""Unit tests for image-processing handlers."""

import pytest


# ---------------------------------------------------------------------------
# ValidateImage handler tests
# ---------------------------------------------------------------------------


class TestValidateImageHandler:
    """Unit tests for the ValidateImage handler."""

    def test_validate_image_valid_jpeg(self):
        """A valid JPEG image should return valid=True with correct format and size."""
        from handlers.validate_image import validate_image

        result = validate_image(
            {"image_id": "img-001", "format": "jpeg", "size_bytes": 1024 * 1024}
        )
        assert result["valid"] is True
        assert result["format"] == "jpeg"
        assert result["size_bytes"] == 1024 * 1024

    def test_validate_image_valid_png(self):
        """A valid PNG image should return valid=True."""
        from handlers.validate_image import validate_image

        result = validate_image(
            {"image_id": "img-002", "format": "png", "size_bytes": 512 * 1024}
        )
        assert result["valid"] is True
        assert result["format"] == "png"

    def test_validate_image_invalid_format(self):
        """An unsupported image format should raise InvalidImageError."""
        from handlers.validate_image import validate_image, InvalidImageError

        with pytest.raises(InvalidImageError, match="Unsupported image format"):
            validate_image({"image_id": "img-003", "format": "bmp", "size_bytes": 100})

    def test_validate_image_too_large(self):
        """An image exceeding 10 MB should raise InvalidImageError."""
        from handlers.validate_image import validate_image, InvalidImageError

        size_over_limit = 10 * 1024 * 1024 + 1  # 10 MB + 1 byte
        with pytest.raises(InvalidImageError, match="exceeds limit"):
            validate_image({"image_id": "img-004", "format": "jpeg", "size_bytes": size_over_limit})

    def test_validate_image_exact_size_limit(self):
        """An image exactly at 10 MB should pass validation."""
        from handlers.validate_image import validate_image

        result = validate_image(
            {"image_id": "img-005", "format": "webp", "size_bytes": 10 * 1024 * 1024}
        )
        assert result["valid"] is True

    def test_validate_image_gif_format(self):
        """A valid GIF image should pass validation."""
        from handlers.validate_image import validate_image

        result = validate_image({"image_id": "img-006", "format": "gif", "size_bytes": 256 * 1024})
        assert result["valid"] is True
        assert result["format"] == "gif"


# ---------------------------------------------------------------------------
# ResizeImage handler tests
# ---------------------------------------------------------------------------


class TestResizeImageHandler:
    """Unit tests for the ResizeImage handler."""

    def test_resize_image_computes_dimensions(self):
        """Resize should compute correct target_height from aspect ratio."""
        from handlers.resize_image import resize_image

        result = resize_image(
            {"image_id": "img-010", "width": 1920, "height": 1080, "target_width": 960}
        )
        assert result["resized"] is True
        assert result["original_width"] == 1920
        assert result["original_height"] == 1080
        assert result["target_width"] == 960
        assert result["target_height"] == 540  # 1080 * (960/1920)

    def test_resize_image_square_image(self):
        """Resizing a square image should produce a square target."""
        from handlers.resize_image import resize_image

        result = resize_image(
            {"image_id": "img-011", "width": 800, "height": 800, "target_width": 400}
        )
        assert result["target_height"] == 400

    def test_resize_image_portrait_image(self):
        """Resizing a portrait image should maintain aspect ratio."""
        from handlers.resize_image import resize_image

        result = resize_image(
            {"image_id": "img-012", "width": 600, "height": 900, "target_width": 300}
        )
        assert result["target_height"] == 450  # 900 * (300/600)


# ---------------------------------------------------------------------------
# AnalyzeContent handler tests
# ---------------------------------------------------------------------------


class TestAnalyzeContentHandler:
    """Unit tests for the AnalyzeContent handler."""

    def test_analyze_content_returns_tags(self):
        """Content analysis should return a non-empty tags list."""
        from handlers.analyze_content import analyze_content

        result = analyze_content({"image_id": "img-020", "format": "jpeg"})
        assert result["analyzed"] is True
        assert isinstance(result["tags"], list)
        assert len(result["tags"]) > 0

    def test_analyze_content_jpeg_tags(self):
        """JPEG images should return photo-related tags."""
        from handlers.analyze_content import analyze_content

        result = analyze_content({"image_id": "img-021", "format": "jpeg"})
        assert "photo" in result["tags"]

    def test_analyze_content_confidence_score(self):
        """Analysis should include a confidence score between 0 and 1."""
        from handlers.analyze_content import analyze_content

        result = analyze_content({"image_id": "img-022", "format": "png"})
        assert 0.0 <= result["confidence"] <= 1.0

    def test_analyze_content_png_tags(self):
        """PNG images should return graphic-related tags."""
        from handlers.analyze_content import analyze_content

        result = analyze_content({"image_id": "img-023", "format": "png"})
        assert "graphic" in result["tags"]


# ---------------------------------------------------------------------------
# CatalogueImage handler tests
# ---------------------------------------------------------------------------


class TestCatalogueImageHandler:
    """Unit tests for the CatalogueImage handler."""

    def test_catalogue_image_returns_timestamp(self):
        """Cataloguing should return catalogued=True with ISO timestamp."""
        from handlers.catalogue_image import catalogue_image

        result = catalogue_image({"image_id": "img-030"})
        assert result["catalogued"] is True
        assert "timestamp" in result
        # Verify it's a non-empty ISO timestamp string
        assert isinstance(result["timestamp"], str)
        assert len(result["timestamp"]) > 0

    def test_catalogue_image_returns_image_id(self):
        """Cataloguing should return the correct image_id."""
        from handlers.catalogue_image import catalogue_image

        result = catalogue_image({"image_id": "img-031"})
        assert result["image_id"] == "img-031"

    def test_catalogue_image_timestamp_is_iso_format(self):
        """Catalogue timestamp should be parseable as ISO 8601."""
        from datetime import datetime
        from handlers.catalogue_image import catalogue_image

        result = catalogue_image({"image_id": "img-032"})
        # Should not raise
        dt = datetime.fromisoformat(result["timestamp"])
        assert dt is not None
