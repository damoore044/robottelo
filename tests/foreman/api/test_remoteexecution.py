"""Test for Remote Execution

:Requirement: Remoteexecution

:CaseAutomation: Automated

:CaseComponent: RemoteExecution

:Team: Endeavour

:CaseImportance: High

"""

import pytest

from robottelo.config import settings
from robottelo.utils import ohsnap


def test_positive_find_capsule_upgrade_playbook(target_sat):
    """Check that Capsule Upgrade playbook is present on Satellite

    :id: 7d9fd42f-289f-4b14-a65e-93ddc8ea759a

    :expectedresults: Capsule upgrade playbook is found on Satellite

    :BZ: 2152951

    :CaseImportance: Medium
    """
    template_name = 'Capsule Upgrade Playbook'
    templates = target_sat.api.JobTemplate().search(query={'search': f'name="{template_name}"'})
    assert len(templates) > 0


def test_positive_run_capsule_update_playbook(module_capsule_configured, target_sat):
    """Run Capsule Upgrade playbook against an External Capsule

    :id: 9ec6903d-2bb7-46a5-8002-afc74f06d83b

    :steps:
        1. Create a Capsule VM, add REX key.
        2. Run the Capsule Upgrade Playbook.

    :expectedresults: Capsule is upgraded successfully

    :CaseImportance: Medium
    """

    template_name = 'Capsule Update Playbook'
    template_id = (
        target_sat.api.JobTemplate().search(query={'search': f'name="{template_name}"'})[0].id
    )
    module_capsule_configured.add_rex_key(satellite=target_sat)
    job = target_sat.api.JobInvocation().run(
        synchronous=False,
        data={
            'job_template_id': template_id,
            'inputs': {
                'whitelist_options': 'repositories-validate,repositories-setup,non-rh-packages',
            },
            'targeting_type': 'static_query',
            'search_query': f'name = {module_capsule_configured.hostname}',
        },
    )
    target_sat.wait_for_tasks(f'resource_type = JobInvocation and resource_id = {job["id"]}')
    result = target_sat.api.JobInvocation(id=job['id']).read()
    assert result.succeeded == 1
    result = target_sat.execute('satellite-maintain health check')
    assert result.status == 0
    for line in result.stdout:
        assert 'FAIL' not in line
    result = target_sat.api.SmartProxy(
        id=target_sat.api.SmartProxy(name=target_sat.hostname).search()[0].id
    ).refresh()
    feature_set = {feat['name'] for feat in result['features']}
    assert {'Dynflow', 'Script', 'Pulpcore', 'Logs'}.issubset(feature_set)


@pytest.mark.no_containers
@pytest.mark.rhel_ver_list([settings.content_host.default_rhel_version])
@pytest.mark.parametrize(
    'setting_update',
    ['remote_execution_global_proxy=False'],
    ids=["no_global_proxy"],
    indirect=True,
)
def test_negative_time_to_pickup(
    module_org,
    module_target_sat,
    smart_proxy_location,
    module_ak_with_cv,
    module_capsule_configured_mqtt,
    rhel_contenthost_with_repos,
    setting_update,
):
    """Time to pickup setting is honored for host registered to mqtt

    :id: a082f599-fbf7-4779-aa18-5139e2bce774

    :expectedresults: Time to pickup aborts the job if mqtt client doesn't
        respond in time

    :CaseImportance: High

    :bz: 2158738

    :parametrized: yes
    """
    client = rhel_contenthost_with_repos
    client_repo = ohsnap.dogfood_repository(
        settings.ohsnap,
        product='client',
        repo='client',
        release='client',
        os_release=client.os_version.major,
    )
    # Update module_capsule_configured_mqtt to include module_org/smart_proxy_location
    module_target_sat.cli.Capsule.update(
        {
            'name': module_capsule_configured_mqtt.hostname,
            'organization-ids': module_org.id,
            'location-ids': smart_proxy_location.id,
        }
    )
    # register host with pull provider rex
    result = client.register(
        module_org,
        smart_proxy_location,
        module_ak_with_cv.name,
        module_capsule_configured_mqtt,
        setup_remote_execution_pull=True,
        repo_data=f'repo={client_repo.baseurl}',
    )
    template_id = (
        module_target_sat.api.JobTemplate()
        .search(query={'search': 'name="Run Command - Script Default"'})[0]
        .id
    )
    assert result.status == 0, f'Failed to register host: {result.stderr}'
    # check mqtt client is running
    service_name = client.get_yggdrasil_service_name()
    result = client.execute(f'systemctl status {service_name}')
    assert result.status == 0, f'Failed to start yggdrasil on client: {result.stderr}'
    # stop yggdrasil client on host
    result = client.execute(f'systemctl stop {service_name}')
    assert result.status == 0, f'Failed to stop yggdrasil on client: {result.stderr}'

    # run script provider rex command with time_to_pickup
    job = module_target_sat.api.JobInvocation().run(
        synchronous=False,
        data={
            'job_template_id': template_id,
            'organization': module_org.name,
            'location': smart_proxy_location.name,
            'inputs': {
                'command': 'ls -la',
            },
            'targeting_type': 'static_query',
            'search_query': f'name = {client.hostname}',
            'time_to_pickup': '10',
        },
    )
    module_target_sat.wait_for_tasks(
        f'resource_type = JobInvocation and resource_id = {job["id"]}', must_succeed=False
    )
    result = module_target_sat.api.JobInvocation(id=job['id']).read()
    assert result.status_label == "failed"
    result = module_target_sat.api.ForemanTask().search(
        query={'search': f'resource_type = JobInvocation and resource_id = {job["id"]}'}
    )
    assert 'The job was not picked up in time' in result[0].humanized['output']

    # Check that global setting is applied
    global_ttp = module_target_sat.api.Setting().search(
        query={'search': 'name="remote_execution_time_to_pickup"'}
    )[0]
    default_global_ttp = global_ttp.value
    global_ttp.value = '10'
    global_ttp.update(['value'])
    job = module_target_sat.api.JobInvocation().run(
        synchronous=False,
        data={
            'job_template_id': template_id,
            'organization': module_org.name,
            'location': smart_proxy_location.name,
            'inputs': {
                'command': 'ls -la',
            },
            'targeting_type': 'static_query',
            'search_query': f'name = {client.hostname}',
        },
    )
    module_target_sat.wait_for_tasks(
        f'resource_type = JobInvocation and resource_id = {job["id"]}', must_succeed=False
    )
    result = module_target_sat.api.JobInvocation(id=job['id']).read()
    assert result.status_label == "failed"
    result = module_target_sat.api.ForemanTask().search(
        query={'search': f'resource_type = JobInvocation and resource_id = {job["id"]}'}
    )
    assert 'The job was not picked up in time' in result[0].humanized['output']
    global_ttp.value = default_global_ttp
    global_ttp.update(['value'])
    # start yggdrasil client on host
    result = client.execute(f'systemctl start {service_name}')
    assert result.status == 0, f'Failed to start on client: {result.stderr}'
    result = client.execute(f'systemctl status {service_name}')
    assert result.status == 0, f'Failed to start yggdrasil on client: {result.stderr}'


@pytest.mark.no_containers
@pytest.mark.rhel_ver_list([settings.content_host.default_rhel_version])
@pytest.mark.parametrize(
    'setting_update',
    ['remote_execution_global_proxy=False'],
    ids=["no_global_proxy"],
    indirect=True,
)
def test_positive_check_longrunning_job(
    module_org,
    module_target_sat,
    smart_proxy_location,
    module_ak_with_cv,
    module_capsule_configured_mqtt,
    rhel_contenthost_with_repos,
    setting_update,
):
    """Time to pickup setting doesn't disrupt longrunning jobs

    :id: e6eeb948-faa5-4b76-9a86-5e934f7bee77

    :expectedresults: Time to pickup doesn't aborts the long running job if
        it already started

    :CaseImportance: Medium

    :bz: 2118651, 2158738

    :parametrized: yes
    """
    client = rhel_contenthost_with_repos
    client_repo = ohsnap.dogfood_repository(
        settings.ohsnap,
        product='client',
        repo='client',
        release='client',
        os_release=client.os_version.major,
    )
    # Update module_capsule_configured_mqtt to include module_org/smart_proxy_location
    module_target_sat.cli.Capsule.update(
        {
            'name': module_capsule_configured_mqtt.hostname,
            'organization-ids': module_org.id,
            'location-ids': smart_proxy_location.id,
        }
    )
    # register host with pull provider rex
    result = client.register(
        module_org,
        smart_proxy_location,
        module_ak_with_cv.name,
        module_capsule_configured_mqtt,
        setup_remote_execution_pull=True,
        repo_data=f'repo={client_repo.baseurl}',
    )
    template_id = (
        module_target_sat.api.JobTemplate()
        .search(query={'search': 'name="Run Command - Script Default"'})[0]
        .id
    )
    # check that longrunning command is not affected by time_to_pickup BZ#2158738
    job = module_target_sat.api.JobInvocation().run(
        synchronous=False,
        data={
            'job_template_id': template_id,
            'organization': module_org.name,
            'location': smart_proxy_location.name,
            'inputs': {
                'command': 'echo start; sleep 25; echo done',
            },
            'targeting_type': 'static_query',
            'search_query': f'name = {client.hostname}',
            'time_to_pickup': '20',
        },
    )
    module_target_sat.wait_for_tasks(f'resource_type = JobInvocation and resource_id = {job["id"]}')
    result = module_target_sat.api.JobInvocation(id=job['id']).read()
    assert result.succeeded == 1
