from sqlalchemy import Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class PhenotypeLabel(Base):
    """A user-editable display name for one cluster of a given k-means run
    (keyed by k + cluster_index, since re-running with a different k
    produces different clusters). Renaming never changes the underlying
    clustering — it only relabels it (README §12: descriptive, renamable
    phenotypes, not diagnostic subtypes)."""

    __tablename__ = "phenotype_labels"
    __table_args__ = (UniqueConstraint("k", "cluster_index", name="uq_phenotype_label_k_cluster"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    k: Mapped[int] = mapped_column(Integer)
    cluster_index: Mapped[int] = mapped_column(Integer)
    label: Mapped[str] = mapped_column(String(128))
