"""HNL salary slip template using Endee layout."""

from .endee_template import EndeeTemplate


class HNLTemplate(EndeeTemplate):
    """Salary slip template for HNL with the same layout as Endee."""

    name = "HNL"
    description = "HNL template"

    def _get_logo_filename(self) -> str:
        """Use HNL-specific header logo."""
        return "HNL.jpeg"
