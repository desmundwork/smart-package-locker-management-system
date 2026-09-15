"""Size catalogue endpoint — physical spec per locker size (requirements 2).

The frontend reads dimensions/volume/labels from here instead of hardcoding
them, so the spec stays in one place (models.SIZE_DIMENSIONS)."""
from fastapi import APIRouter

from app.models import SIZE_ORDER, dimensions_for, label_for
from app.schemas import DimensionsOut, SizeSpecOut

router = APIRouter(prefix="/api/sizes", tags=["sizes"])


def _dims_out(size) -> DimensionsOut:
    d = dimensions_for(size)
    return DimensionsOut(
        width_cm=d.width_cm, depth_cm=d.depth_cm, height_cm=d.height_cm,
        volume_litres=d.volume_litres,
    )


@router.get("", response_model=list[SizeSpecOut])
def list_sizes() -> list[SizeSpecOut]:
    return [
        SizeSpecOut(size=size, dimensions=_dims_out(size), label=label_for(size))
        for size in SIZE_ORDER
    ]
