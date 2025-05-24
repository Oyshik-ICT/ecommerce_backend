import logging

from rest_framework import serializers

logger = logging.getLogger(__name__)


def quantity_validation(items):
    """Validates that each item has at least 1 quantity and does not exceed available stock."""
    try:
        for item in items:
            if item["quantity"] == 0:
                raise serializers.ValidationError(
                    "You have to choose atleast 1 quantity"
                )
            if item["product"].stock < item["quantity"]:
                raise serializers.ValidationError("You have to choose less quantity")
    except Exception as e:
        logger.error(f"Error in quantity_validation: {str(e)}")
        raise
