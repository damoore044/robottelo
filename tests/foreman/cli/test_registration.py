"""Tests for registration.

:Requirement: Registration

:CaseComponent: Registration

:CaseAutomation: Automated

:CaseImportance: Critical

:Team: Rocket

"""

import json
import re
from tempfile import mkstemp

from fauxfactory import gen_mac, gen_string
import pytest

from robottelo.config import settings
from robottelo.constants import CLIENT_PORT
from robottelo.exceptions import CLIReturnCodeError
from robottelo.utils.issue_handlers import is_open

pytestmark = pytest.mark.tier1


@pytest.mark.e2e
@pytest.mark.no_containers
def test_host_registration_end_to_end(
    module_sca_manifest_org,
    module_location,
    module_activation_key,
    module_target_sat,
    module_capsule_configured,
    rhel_contenthost,
):
    """Verify content host registration with global registration

    :id: b6cd60ba-8069-11ed-ac61-83315855d126

    :steps:
        1. Register host with global registration template to Satellite and Capsule
        2. Check the host is registered and verify host owner name

    :expectedresults: Host registered successfully with valid owner name

    :verifies: SAT-21682, SAT-14716

    :customerscenario: true
    """
    org = module_sca_manifest_org
    result = rhel_contenthost.register(
        org, module_location, module_activation_key.name, module_target_sat
    )

    rc = 1 if rhel_contenthost.os_version.major == 6 else 0
    assert result.status == rc, f'Failed to register host: {result.stderr}'

    owner_name = module_target_sat.cli.Host.info(
        options={'name': rhel_contenthost.hostname, 'fields': 'Additional info/owner'}
    )
    # Verify host owner name set correctly
    assert 'Admin User' in owner_name['additional-info']['owner']['name'], (
        f'Host owner name is incorrect: ' f'{owner_name["additional-info"]["owner"]["name"]}'
    )

    # Verify server.hostname and server.port from subscription-manager config
    assert module_target_sat.hostname == rhel_contenthost.subscription_config['server']['hostname']
    assert rhel_contenthost.subscription_config['server']['port'] == CLIENT_PORT

    # Update module_capsule_configured to include module_org/module_location
    module_target_sat.cli.Capsule.update(
        {
            'name': module_capsule_configured.hostname,
            'organization-ids': org.id,
            'location-ids': module_location.id,
        }
    )
    result = rhel_contenthost.register(
        org,
        module_location,
        module_activation_key.name,
        module_capsule_configured,
        force=True,
    )
    rc = 1 if rhel_contenthost.os_version.major == 6 else 0
    assert result.status == rc, f'Failed to register host: {result.stderr}'

    owner_name = module_target_sat.cli.Host.info(
        options={'name': rhel_contenthost.hostname, 'fields': 'Additional info/owner'}
    )
    # Verify capsule host owner name set correctly
    assert 'Admin User' in owner_name['additional-info']['owner']['name'], (
        f'Host owner name is incorrect: ' f'{owner_name["additional-info"]["owner"]["name"]}'
    )

    # Verify server.hostname and server.port from subscription-manager config
    assert (
        module_capsule_configured.hostname
        == rhel_contenthost.subscription_config['server']['hostname']
    )
    assert rhel_contenthost.subscription_config['server']['port'] == CLIENT_PORT


def test_upgrade_katello_ca_consumer_rpm(
    module_org, module_location, target_sat, rhel7_contenthost
):
    """After updating the consumer cert the rhsm.conf file still points to Satellite host name
    and not Red Hat CDN for subscription.

    :id: c8d861ec-0d81-4d89-a8e1-02afecfd8171

    :steps:

        1. Get consumer crt source file
        2. Install rpm-build
        3. Use rpmbuild to change the version in the spec file
        4. Build new RPM with higher version number
        5. Install new RPM and assert no change in server URL

    :expectedresults: Server URL is still Satellite host name not Red Hat CDN

    :CaseImportance: High

    :customerscenario: true

    :BZ: 1791503
    """
    consumer_cert_name = f'katello-ca-consumer-{target_sat.hostname}'
    consumer_cert_src = f'{consumer_cert_name}-1.0-1.src.rpm'
    new_consumer_cert_rpm = f'{consumer_cert_name}-1.0-2.noarch.rpm'
    spec_file = f'{consumer_cert_name}.spec'
    vm = rhel7_contenthost
    # Install consumer cert and check server URL in /etc/rhsm/rhsm.conf
    assert vm.execute(
        f'rpm -Uvh "http://{target_sat.hostname}/pub/{consumer_cert_name}-1.0-1.noarch.rpm"'
    )
    # Check server URL is not Red Hat CDN's "subscription.rhsm.redhat.com"
    assert vm.subscription_config['server']['hostname'] != 'subscription.rhsm.redhat.com'
    assert target_sat.hostname == vm.subscription_config['server']['hostname']

    # Get consumer cert source file
    assert vm.execute(f'curl -O "http://{target_sat.hostname}/pub/{consumer_cert_src}"')
    # Install repo for build tools
    vm.create_custom_repos(rhel7=settings.repos.rhel7_os)
    result = vm.execute('[ -s "/etc/yum.repos.d/rhel7.repo" ]')
    assert result.status == 0
    # Install tools
    assert vm.execute('yum -y install rpm-build')
    # Install src to create the SPEC
    assert vm.execute(f'rpm -i {consumer_cert_src}')
    # rpmbuild spec file
    assert vm.execute(
        f'rpmbuild --define "name {consumer_cert_name}" --define "release 2" \
        -ba rpmbuild/SPECS/{spec_file}'
    )
    # Install new rpmbuild/RPMS/noarch/katello-ca-consumer-*-2.noarch.rpm
    assert vm.execute(f'yum install -y rpmbuild/RPMS/noarch/{new_consumer_cert_rpm}')
    # Check server URL is not Red Hat CDN's "subscription.rhsm.redhat.com"
    assert vm.subscription_config['server']['hostname'] != 'subscription.rhsm.redhat.com'
    assert target_sat.hostname == vm.subscription_config['server']['hostname']

    # Register as final check
    vm.register_contenthost(module_org.label)
    result = vm.execute('subscription-manager identity')
    # Result will be 0 if registered
    assert result.status == 0


@pytest.mark.rhel_ver_match('[^6]')
@pytest.mark.tier3
def test_negative_register_twice(module_ak_with_cv, module_org, rhel_contenthost, target_sat):
    """Attempt to register a host twice to Satellite

    :id: 0af81129-cd69-4fa7-a128-9e8fcf2d03b1

    :expectedresults: host cannot be registered twice

    :parametrized: yes
    """
    rhel_contenthost.register(module_org, None, module_ak_with_cv.name, target_sat)
    assert rhel_contenthost.subscribed
    result = rhel_contenthost.register(
        module_org, None, module_ak_with_cv.name, target_sat, force=False
    )
    # host being already registered.
    assert result.status == 1
    assert 'This system is already registered' in str(result.stderr)


@pytest.mark.rhel_ver_match('[^6]')
@pytest.mark.tier3
def test_positive_force_register_twice(module_ak_with_cv, module_org, rhel_contenthost, target_sat):
    """Register a host twice to Satellite, with force=true

    :id: 7ccd4efd-54bb-4207-9acf-4c6243a32fab

    :expectedresults: Host will be re-registered

    :parametrized: yes

    :BZ: 1361309

    :customerscenario: true
    """
    reg_id_pattern = r"The system has been registered with ID: ([^\n]*)"
    name = gen_string('alpha') + ".example.com"
    rhel_contenthost.execute(f'hostnamectl set-hostname {name}')
    result = rhel_contenthost.register(module_org, None, module_ak_with_cv.name, target_sat)
    reg_id_old = re.search(reg_id_pattern, result.stdout).group(1)
    assert result.status == 0
    assert rhel_contenthost.subscribed
    result = rhel_contenthost.register(
        module_org, None, module_ak_with_cv.name, target_sat, force=True
    )
    assert result.status == 0
    assert rhel_contenthost.subscribed
    assert f'Unregistering from: {target_sat.hostname}' in str(result.stdout)
    assert f'The registered system name is: {rhel_contenthost.hostname}' in str(result.stdout)
    reg_id_new = re.search(reg_id_pattern, result.stdout).group(1)
    assert f'The system has been registered with ID: {reg_id_new}' in str(result.stdout)
    assert reg_id_new != reg_id_old
    assert (
        target_sat.cli.Host.info({'name': rhel_contenthost.hostname}, output_format='json')[
            'subscription-information'
        ]['uuid']
        == reg_id_new
    )


@pytest.mark.tier1
def test_negative_global_registration_without_ak(module_target_sat):
    """Attempt to register a host without ActivationKey

    :id: e48a6260-97e0-4234-a69c-77bbbcde85df

    :expectedresults: Generate command is disabled without ActivationKey
    """
    with pytest.raises(CLIReturnCodeError) as context:
        module_target_sat.cli.HostRegistration.generate_command(options=None)
    assert (
        'Failed to generate registration command:\n  Missing activation key!'
        in context.value.message
    )


@pytest.mark.rhel_ver_match('8')
def test_positive_custom_facts_for_host_registration(
    module_sca_manifest_org,
    module_location,
    module_target_sat,
    rhel_contenthost,
    module_activation_key,
):
    """Attempt to register a host and check all the interfaces are created from the custom facts

    :id: db73c146-4557-4bf4-a8e2-950ecba31620

    :steps:
        1. Register the host.
        2. Check the host is registered and all the interfaces are created successfully.

    :expectedresults: Host registered successfully with all interfaces created from the custom facts.

    :BZ: 2250397

    :customerscenario: true
    """
    interfaces = [
        {'name': gen_string('alphanumeric')},
        {'name': 'enp98s0f0', 'mac': gen_mac(multicast=False)},
        {'name': 'Datos', 'vlan_id': gen_string('numeric', 4)},
        {'name': 'bondBk', 'vlan_id': gen_string('numeric', 4)},
    ]
    facts = {
        f'net.interface.{interfaces[0]["name"]}.mac_address': gen_mac(),
        f'net.interface.{interfaces[1]["name"]}.mac_address': interfaces[1]["mac"],
        f'net.interface.{interfaces[2]["name"]}.{interfaces[2]["vlan_id"]}.mac_address': gen_mac(),
        f'net.interface.{interfaces[3]["name"]}.{interfaces[3]["vlan_id"]}.mac_address': gen_mac(),
    }
    _, facts_file = mkstemp(suffix='.facts')
    with open(facts_file, 'w') as f:
        json.dump(facts, f, indent=4)
    rhel_contenthost.put(facts_file, '/etc/rhsm/facts/')
    result = rhel_contenthost.register(
        module_sca_manifest_org, module_location, module_activation_key.name, module_target_sat
    )
    assert result.status == 0, f'Failed to register host: {result.stderr}'
    host_info = module_target_sat.cli.Host.info(
        {'name': rhel_contenthost.hostname}, output_format='json'
    )
    assert len(host_info['network-interfaces']) == len(interfaces) + 1  # facts + default interface
    for interface in interfaces:
        for interface_name in interface.values():
            assert interface_name in str(host_info['network-interfaces'])


@pytest.mark.upgrade
@pytest.mark.no_containers
@pytest.mark.rhel_ver_list([settings.content_host.default_rhel_version])
def test_positive_global_registration_with_gpg_repo(
    module_sca_manifest_org,
    module_location,
    module_activation_key,
    module_target_sat,
    rhel_contenthost,
):
    """Verify host registration command gets generated and host is registered successfully with gpg repo enabled.

    :id: 8f01d904-dd52-47eb-b909-975574a7c7c7

    :steps:
        1. Register host with global registration template with gpg repo and key to Satellite.

    :expectedresults: Host is successfully registered, gpg repo is enabled.
    """
    org = module_sca_manifest_org
    repo_url = settings.repos.gr_yum_repo.url
    repo_gpg_url = settings.repos.gr_yum_repo.gpg_url
    result = rhel_contenthost.register(
        org,
        module_location,
        module_activation_key.name,
        module_target_sat,
        repo_data=f'repo={repo_url},repo_gpg_key_url={repo_gpg_url}',
    )
    assert result.status == 0
    assert rhel_contenthost.subscribed
    result = rhel_contenthost.execute('yum -v repolist')
    assert repo_url in result.stdout
    assert result.status == 0
    if not is_open('SAT-27653'):
        assert rhel_contenthost.execute('dnf install -y bear').status == 0


@pytest.mark.parametrize('setting_update', ['default_location_subscribed_hosts'], indirect=True)
@pytest.mark.rhel_ver_list([settings.content_host.default_rhel_version])
def test_positive_verify_default_location_for_registered_host(
    module_target_sat,
    module_sca_manifest_org,
    module_location,
    rhel_contenthost,
    module_activation_key,
    setting_update,
):
    """Verify default location set for registered host with default_location_subscribed_hosts setting.

    :id: 6ea802d8-0788-4309-845c-c877013a8e48

    :steps:
        1. Create a location and set it as a default location in Administer --> Settings --> Content --> "Default Location subscribed hosts".
        2. Register the host without specifying the location.
        3. Verify that the default location in settings is set as host location after registration.
        4. Re-register the host with a new location.
        5. Verify the host location is registered to new location provided during registration.

    :expectedresults:
        1. Host registers in location set to "Default Location subscribed hosts" setting if no location is provided.
        2. Host registers in location is set to the location provided during registration which overrides the "Default Location subscribed hosts" setting.

    :Verifies: SAT-23047

    :customerscenario: true
    """
    org = module_sca_manifest_org
    location = module_target_sat.api.Location(organization=[org]).create()
    setting_update.value = location.name
    setting_update.update({'value'})
    location_set = (
        module_target_sat.api.Setting()
        .search(query={'search': f'name={setting_update.name}'})[0]
        .value
    )
    result = rhel_contenthost.register(
        module_sca_manifest_org,
        None,
        module_activation_key.name,
        module_target_sat,
    )
    assert result.status == 0, f'Failed to register host: {result.stderr}'
    host = module_target_sat.api.Host().search(
        query={"search": f'name={rhel_contenthost.hostname}'}
    )[0]
    assert host.location.read().name == location_set
    # Re-register the host with location provided during registration
    result = rhel_contenthost.register(
        module_sca_manifest_org,
        module_location,
        module_activation_key.name,
        module_target_sat,
        force=True,
    )
    assert result.status == 0, f'Failed to register host: {result.stderr}'
    host = module_target_sat.api.Host().search(
        query={"search": f'name={rhel_contenthost.hostname}'}
    )[0]
    assert host.location.read().name == module_location.name
