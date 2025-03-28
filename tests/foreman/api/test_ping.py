"""Test Class for api ping

:Requirement: Ping

:CaseAutomation: Automated

:CaseComponent: API

:Team: Endeavour

:CaseImportance: Critical

"""

import pytest


@pytest.mark.e2e
@pytest.mark.build_sanity
@pytest.mark.upgrade
def test_positive_ping(target_sat):
    """Check if all services are running

    :id: b8ecc7ba-8007-4067-bf99-21a82c833de7

    :expectedresults: Overall and individual services status should be 'ok'.
    """
    response = target_sat.api.Ping().search_json()
    assert response['status'] == 'ok'  # overall status

    # Check that all services are OK. ['services'] is in this format:
    #
    # {'services': {
    #    'candlepin': {'duration_ms': '40', 'status': 'ok'},
    #    'candlepin_auth': {'duration_ms': '41', 'status': 'ok'},
    #    …
    # }, 'status': 'ok'}
    services = response['services']
    assert all([service['status'] == 'ok' for service in services.values()]), (
        'Not all services seem to be up and running!'
    )
