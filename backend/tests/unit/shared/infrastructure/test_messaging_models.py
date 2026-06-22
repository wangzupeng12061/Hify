from __future__ import annotations

from hify.shared.infrastructure.messaging import InboxReceiptModel, OutboxMessageModel


def test_platform_messaging_table_names_are_stable() -> None:
    assert OutboxMessageModel.__tablename__ == "platform_outbox"
    assert InboxReceiptModel.__tablename__ == "platform_inbox_receipts"


def test_inbox_receipt_has_event_consumer_unique_constraint() -> None:
    constraint_names = {constraint.name for constraint in InboxReceiptModel.__table__.constraints}

    assert "uq_platform_inbox_receipts__event_consumer" in constraint_names


def test_outbox_has_named_event_constraint_and_pending_index() -> None:
    constraint_names = {constraint.name for constraint in OutboxMessageModel.__table__.constraints}
    index_names = {index.name for index in OutboxMessageModel.__table__.indexes}

    assert "uq_platform_outbox__event_id" in constraint_names
    assert "ix_platform_outbox__pending_next_attempt" in index_names
