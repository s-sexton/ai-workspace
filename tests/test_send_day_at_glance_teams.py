from assistant.src.send_day_at_glance_teams import main, send_day_at_glance_teams


def test_send_day_at_glance_teams_uses_refresh_defaults(monkeypatch):
    calls = []

    class Brief:
        output_path = "reports/clarity-daily-brief.md"
        manifest_path = "reports/clarity-daily-brief.json"
        outlook_attention_count = 1
        calendar_window_days = 7
        calendar_event_count = 2
        jira_ticket_count = 3
        open_task_count = 4
        pending_action_count = 5

    class Result:
        brief = Brief()
        teams_posted = True

    def fake_build_transport(**_):
        return object()

    def fake_send_daily_brief(**kwargs):
        calls.append(kwargs)
        return Result()

    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_graph_read_transport_from_config",
        fake_build_transport,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_gmail_read_transport_from_config",
        fake_build_transport,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_graph_calendar_read_transport_from_config",
        fake_build_transport,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_google_calendar_read_transport_from_config",
        fake_build_transport,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.send_daily_brief",
        fake_send_daily_brief,
    )

    result = send_day_at_glance_teams(execute=True)

    assert result.daily_brief.teams_posted is True
    assert calls[0]["refresh_email"] is True
    assert calls[0]["use_graph_email"] is True
    assert calls[0]["use_gmail"] is True
    assert calls[0]["refresh_calendars"] is True
    assert calls[0]["use_graph_calendars"] is True
    assert calls[0]["use_google_calendars"] is True
    assert calls[0]["refresh_jira"] is True
    assert calls[0]["post_to_teams"] is True
    assert calls[0]["execute"] is True
    assert calls[0]["calendar_window_days"] == 7
    assert calls[0]["continue_on_refresh_error"] is True


def test_send_day_at_glance_teams_defers_provider_auth_until_refresh(monkeypatch):
    class Brief:
        output_path = "reports/clarity-daily-brief.md"
        manifest_path = "reports/clarity-daily-brief.json"
        outlook_attention_count = 1
        calendar_window_days = 7
        calendar_event_count = 2
        jira_ticket_count = 3
        open_task_count = 4
        pending_action_count = 5

    class Result:
        brief = Brief()
        teams_posted = False

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("Transport builder was called eagerly.")

    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_graph_read_transport_from_config",
        fail_if_called,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_gmail_read_transport_from_config",
        fail_if_called,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_graph_calendar_read_transport_from_config",
        fail_if_called,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.build_google_calendar_read_transport_from_config",
        fail_if_called,
    )
    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.send_daily_brief",
        lambda **_: Result(),
    )

    result = send_day_at_glance_teams(execute=True)

    assert result.daily_brief.teams_posted is False


def test_main_prints_day_at_glance_summary(monkeypatch, capsys):
    class Brief:
        output_path = "reports/clarity-daily-brief.md"
        manifest_path = "reports/clarity-daily-brief.json"
        outlook_attention_count = 1
        calendar_window_days = 7
        calendar_event_count = 2
        jira_ticket_count = 3
        open_task_count = 4
        pending_action_count = 5

    class DailyBrief:
        brief = Brief()
        teams_posted = False

    class Result:
        daily_brief = DailyBrief()

    monkeypatch.setattr(
        "assistant.src.send_day_at_glance_teams.send_day_at_glance_teams",
        lambda **_: Result(),
    )

    main(["--no-refresh-email", "--no-refresh-calendars", "--no-refresh-jira"])

    output = capsys.readouterr().out
    assert "Clarity Day at a Glance Teams" in output
    assert "Inbox attention: 1" in output
    assert "Calendar events (7 days): 2" in output
    assert "Teams posted: no" in output
