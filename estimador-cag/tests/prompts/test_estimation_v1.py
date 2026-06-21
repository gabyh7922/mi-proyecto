"""Tests del template de estimación v1.

Son tests del TEMPLATE, no del modelo: verifican que, dado un input estructurado,
el prompt renderizado contiene lo que debe. Corren en milisegundos, sin tocar APIs.
"""

from app.prompts.loader import render_estimation_prompt
from app.schemas import (
    DetailLevel,
    EstimationRequest,
    OutputFormat,
    ProjectType,
)


def _request(**overrides) -> EstimationRequest:
    base = dict(
        description="Mobile app with login, chat and push notifications for our sales team.",
        project_type=ProjectType.MOBILE_APP,
        detail_level=DetailLevel.MEDIUM,
        output_format=OutputFormat.PHASES_TABLE,
    )
    base.update(overrides)
    return EstimationRequest(**base)


def test_description_is_included_in_user_block():
    request = _request()
    _system, user = render_estimation_prompt(request)

    assert "<project_description>" in user
    assert "Mobile app with login, chat and push notifications" in user


def test_output_format_phases_table_vs_narrative():
    system_table, _ = render_estimation_prompt(_request(output_format=OutputFormat.PHASES_TABLE))
    assert "phases_table" in system_table
    assert "confidence_pct" in system_table

    system_narrative, _ = render_estimation_prompt(_request(output_format=OutputFormat.NARRATIVE))
    assert "phases_table" not in system_narrative
    assert "confidence_pct" not in system_narrative


def test_detail_level_detailed_adds_assumptions_instruction():
    system_detailed, _ = render_estimation_prompt(_request(detail_level=DetailLevel.DETAILED))
    assert "list the assumptions you made for each phase" in system_detailed

    system_summary, _ = render_estimation_prompt(_request(detail_level=DetailLevel.SUMMARY))
    assert "list the assumptions you made for each phase" not in system_summary
