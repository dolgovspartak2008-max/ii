from app.infrastructure.telegram.business_bot.router import parse_business_profile


def test_business_command_parser_splits_name_and_description() -> None:
    profile = parse_business_profile("Кофейня | Кофе и десерты")

    assert profile == ("Кофейня", "Кофе и десерты")


def test_business_command_parser_rejects_missing_separator() -> None:
    assert parse_business_profile("Кофейня") is None
