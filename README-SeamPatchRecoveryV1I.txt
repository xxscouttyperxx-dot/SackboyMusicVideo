Seam Patch Recovery v1I

This fixes the v1H crash. v1H rendered successfully but crashed because it removed temporary cameras and then tried to read their object names. v1I stores all camera names before cleanup.

This package does not change geometry and does not save the blend.
It only measures the current saved hoodie state, renders clean review images, and writes reports.
