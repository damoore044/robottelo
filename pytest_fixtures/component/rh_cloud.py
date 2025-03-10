from broker import Broker
import pytest

from robottelo.config import settings
from robottelo.constants import CAPSULE_REGISTRATION_OPTS
from robottelo.hosts import SatelliteHostError


@pytest.fixture(scope='module')
def module_target_sat_insights(request, module_target_sat, satellite_factory):
    """A module-level fixture to provide a Satellite configured for Insights.
    By default, it returns the existing Satellite provided by module_target_sat.

    If parametrized with a false value, then it will deploy and return a Satellite with
    iop-advisor-engine (local Insights advisor) configured.
    """
    hosted_insights = getattr(request, 'param', True)
    satellite = module_target_sat if hosted_insights else satellite_factory()

    if not hosted_insights:
        image_url = getattr(settings.rh_cloud, 'iop_advisor_image', '')
        script = getattr(settings.rh_cloud, 'iop_setup_script', '').splitlines()

        # Configure installer to use downstream image.
        if image_url:
            satellite.execute(
                f'echo "iop_advisor_engine::image: {image_url!r}" >> /etc/foreman-installer/custom-hiera.yaml'
            )

        cmd_result = satellite.execute(
            'satellite-installer --foreman-plugin-rh-cloud-enable-iop-advisor-engine true'
        )
        if cmd_result.status != 0:
            raise SatelliteHostError(f'Error installing advisor engine: {cmd_result.stdout}')

        # Perform post-steps, such as generate custom rule content.
        for cmd in script:
            cmd_result = satellite.execute(cmd)
            if cmd_result.status != 0:
                raise SatelliteHostError(
                    f'Error during post-install of advisor engine: {cmd_result.stdout}'
                )

    yield satellite

    if not hosted_insights:
        satellite.teardown()
        Broker(hosts=[satellite]).checkin()


@pytest.fixture(scope='module')
def rhcloud_manifest_org(module_target_sat_insights, module_sca_manifest):
    """A module level fixture to get organization with manifest."""
    org = module_target_sat_insights.api.Organization().create()
    module_target_sat_insights.upload_manifest(org.id, module_sca_manifest.content)
    return org


@pytest.fixture(scope='module')
def rhcloud_activation_key(module_target_sat_insights, rhcloud_manifest_org):
    """A module-level fixture to create an Activation key in module_org"""
    return module_target_sat_insights.api.ActivationKey(
        content_view=rhcloud_manifest_org.default_content_view,
        organization=rhcloud_manifest_org,
        environment=module_target_sat_insights.api.LifecycleEnvironment(
            id=rhcloud_manifest_org.library.id
        ),
        service_level='Self-Support',
        purpose_usage='test-usage',
        purpose_role='test-role',
        auto_attach=False,
    ).create()


@pytest.fixture(scope='module')
def rhcloud_registered_hosts(
    rhcloud_activation_key, rhcloud_manifest_org, mod_content_hosts, module_target_sat_insights
):
    """Fixture that registers content hosts to Satellite and Insights."""
    for vm in mod_content_hosts:
        vm.configure_insights_client(
            satellite=module_target_sat_insights,
            activation_key=rhcloud_activation_key,
            org=rhcloud_manifest_org,
            rhel_distro=f"rhel{vm.os_version.major}",
        )
        assert vm.subscribed
    return mod_content_hosts


@pytest.fixture
def rhel_insights_vm(
    module_target_sat_insights,
    rhcloud_activation_key,
    rhcloud_manifest_org,
    rhel_contenthost,
):
    """A function-level fixture to create rhel content host registered with insights."""
    rhel_contenthost.configure_rex(
        satellite=module_target_sat_insights, org=rhcloud_manifest_org, register=False
    )
    rhel_contenthost.configure_insights_client(
        satellite=module_target_sat_insights,
        activation_key=rhcloud_activation_key,
        org=rhcloud_manifest_org,
        rhel_distro=f"rhel{rhel_contenthost.os_version.major}",
    )
    # Sync inventory if using hosted Insights
    if not module_target_sat_insights.local_advisor_enabled:
        module_target_sat_insights.generate_inventory_report(rhcloud_manifest_org)
        module_target_sat_insights.sync_inventory_status(rhcloud_manifest_org)
    return rhel_contenthost


@pytest.fixture
def inventory_settings(module_target_sat_insights):
    hostnames_setting = module_target_sat_insights.update_setting(
        'obfuscate_inventory_hostnames', False
    )
    ip_setting = module_target_sat_insights.update_setting('obfuscate_inventory_ips', False)
    packages_setting = module_target_sat_insights.update_setting(
        'exclude_installed_packages', False
    )
    parameter_tags_setting = module_target_sat_insights.update_setting(
        'include_parameter_tags', False
    )

    yield

    module_target_sat_insights.update_setting('obfuscate_inventory_hostnames', hostnames_setting)
    module_target_sat_insights.update_setting('obfuscate_inventory_ips', ip_setting)
    module_target_sat_insights.update_setting('exclude_installed_packages', packages_setting)
    module_target_sat_insights.update_setting('include_parameter_tags', parameter_tags_setting)


@pytest.fixture(scope='module')
def rhcloud_capsule(
    module_capsule_host, module_target_sat_insights, rhcloud_manifest_org, default_location
):
    """Configure the capsule instance with the satellite from settings.server.hostname"""
    org = rhcloud_manifest_org
    module_capsule_host.capsule_setup(
        sat_host=module_target_sat_insights, **CAPSULE_REGISTRATION_OPTS
    )
    module_target_sat_insights.cli.Capsule.update(
        {
            'name': module_capsule_host.hostname,
            'organization-ids': org.id,
            'location-ids': default_location.id,
        }
    )
    return module_capsule_host
