"""Tests for satellite-maintain clone

:Requirement: foreman-maintain

:CaseAutomation: Automated

:CaseComponent: SatelliteClone

:Team: Rocket

:CaseImportance: High

"""

from fauxfactory import gen_string
import pytest

from robottelo.config import settings
from robottelo.hosts import Satellite, get_sat_rhel_version

SSH_PASS = settings.server.ssh_password
pytestmark = pytest.mark.destructive


@pytest.mark.pit_server
@pytest.mark.e2e
@pytest.mark.parametrize(
    "sat_ready_rhel",
    [8, 9] if get_sat_rhel_version().major < 9 else [9],
    indirect=True,
)
@pytest.mark.parametrize('backup_type', ['online', 'offline'])
@pytest.mark.parametrize('skip_pulp', [False, True], ids=['include_pulp', 'skip_pulp'])
def test_positive_clone_backup(
    target_sat, sat_ready_rhel, backup_type, skip_pulp, custom_synced_repo
):
    """Make an online/offline backup with/without pulp data of Satellite and clone it (restore it).

    :id: 5b9182d5-6789-4d2c-bcc3-6641b96ab277

    :steps:
        1. Create an online/offline backup with/without pulp data
        2. Copy it to target rhel
        3. Install satellite-clone
        4. Run satellite clone on target rhel

    :expectedresult:
        1. Satellite-clone ran successfully

    :parametrized: yes

    :Verifies: SAT-10789, SAT-15437, SAT-13950, SAT-27907

    :customerscenario: true
    """
    pulp_artifact_len = len(target_sat.execute('ls /var/lib/pulp/media/artifact').stdout)

    # occupy source user IDs by random users on target server (so clone has to change ownership and permissions)
    sat_src_users = ["foreman", "pulp"]
    sat_src_users_ids = []
    for user in sat_src_users:
        id = target_sat.execute(f'id -u {user}').stdout.strip()
        if id:
            sat_src_users_ids.append(id)
            sat_ready_rhel.execute(f"useradd {gen_string('alpha')} -u {id}")

    # SATELLITE PART - SOURCE SERVER
    # Enabling and starting services
    assert target_sat.cli.Service.enable().status == 0
    assert target_sat.cli.Service.start().status == 0

    # Doing backup
    backup_result = target_sat.cli.Backup.run_backup(
        backup_dir='/var/backup',
        backup_type=backup_type,
        options={'assumeyes': True, 'plaintext': True, 'skip-pulp-content': skip_pulp},
    )
    assert backup_result.status == 0
    sat_backup_dir = backup_result.stdout.strip().split()[-2]

    # Copying satellite backup to target RHEL
    assert (
        target_sat.execute(
            f'''sshpass -p "{SSH_PASS}" scp -o StrictHostKeyChecking=no \
            -r {sat_backup_dir} root@{sat_ready_rhel.hostname}:/backup/'''
        ).status
        == 0
    )
    assert target_sat.cli.Service.stop().status == 0
    assert target_sat.cli.Service.disable().status == 0

    # If --skip-pulp-data make sure you can rsync /var/lib/pulp over per BZ#2013776
    if skip_pulp:
        # Copying satellite pulp data to target RHEL
        assert (
            target_sat.execute(
                f'sshpass -p "{SSH_PASS}" rsync -e "ssh -o StrictHostKeyChecking=no" --archive --partial --progress --compress '
                f'/var/lib/pulp/ root@{sat_ready_rhel.hostname}:/var/lib/pulp/'
            ).status
            == 0
        )

    # RHEL PART - TARGET SERVER
    assert sat_ready_rhel.execute('ls /backup/config_files.tar.gz').status == 0
    # Registering to cdn
    sat_ready_rhel.register_to_cdn()
    # Setup repositories
    sat_ready_rhel.setup_rhel_repos()
    sat_ready_rhel.setup_satellite_repos()

    # Enabling satellite module for RHEL8
    sat_ready_rhel.enable_satellite_or_capsule_module_for_rhel8()
    # Install satellite-clone
    assert sat_ready_rhel.execute('yum install satellite-clone -y').status == 0
    # Disabling repos setup - they are already configured
    assert (
        sat_ready_rhel.execute(
            'echo "enable_repos: false" >> /etc/satellite-clone/satellite-clone-vars.yml'
        ).status
        == 0
    )
    # Assert clone won't fail due to BZ
    assert sat_ready_rhel.execute('satellite-clone --assume-yes --list-tasks').status == 0
    # Run satellite-clone
    assert sat_ready_rhel.execute('satellite-clone -y', timeout='3h').status == 0
    cloned_sat = Satellite(sat_ready_rhel.hostname)
    assert cloned_sat.cli.Health.check().status == 0

    # Make sure all of the pulp data that was on the original Satellite is on the clone
    assert (
        len(sat_ready_rhel.execute('ls /var/lib/pulp/media/artifact').stdout) == pulp_artifact_len
    )

    # verify if owherships of pulp directory was changed (owner's user id has changed)
    assert (
        sat_ready_rhel.execute('stat -c "%u" /var/lib/pulp/').stdout.strip()
        not in sat_src_users_ids
    )


def test_positive_list_tasks(target_sat):
    """Test that satellite-clone --list-tasks command doesn't fail.

    :id: fb34b70f-dc69-482c-bfbe-9b433cdce89e

    :BZ: 2170034

    :steps:
        1. Install satellite-clone
        2. Run satellite-clone --assume-yes --list-tasks

    :expectedresult:
        1. Satellite-clone ran successfully
    """
    result = target_sat.execute('dnf install -y --disableplugin=foreman-protector satellite-clone')
    assert result.status == 0
    result = target_sat.execute('satellite-clone --assume-yes --list-tasks')
    assert result.status == 0
