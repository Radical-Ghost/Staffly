"""Salary slip templates."""

from .base_template import BaseSlipTemplate
from .endee_template import EndeeTemplate
from .hnl_template import HNLTemplate

TEMPLATES = {
    "Endee": EndeeTemplate,
    "HNL": HNLTemplate,
}

__all__ = ["BaseSlipTemplate", "EndeeTemplate", "HNLTemplate", "TEMPLATES"]
