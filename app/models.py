import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ProvisionStatus(str, enum.Enum):
    pending = "pending"
    terraform_running = "terraform_running"
    terraform_done = "terraform_done"
    ansible_running = "ansible_running"
    succeeded = "succeeded"
    failed = "failed"


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    rustfs_terraform_prefix: Mapped[str] = mapped_column(String(512))
    rustfs_ansible_prefix: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class ProvisionRun(Base):
    __tablename__ = "provision_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[ProvisionStatus] = mapped_column(Enum(ProvisionStatus), default=ProvisionStatus.pending)
    trigger_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    log_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
