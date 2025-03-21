"""Test class for Sync Plan CLI

:Requirement: Syncplan

:CaseAutomation: Automated

:CaseComponent: SyncPlans

:team: Phoenix-content

:CaseImportance: High

"""

from datetime import datetime, timedelta
from time import sleep

from fauxfactory import gen_string
import pytest

from robottelo.constants import PRDS, REPOS, REPOSET
from robottelo.exceptions import CLIFactoryError, CLIReturnCodeError
from robottelo.logging import logger
from robottelo.utils.datafactory import (
    filtered_datapoint,
    invalid_values_list,
    parametrized,
    valid_data_list,
)

SYNC_DATE_FMT = '%Y-%m-%d %H:%M:%S UTC'


@filtered_datapoint
def valid_name_interval_create_tests():
    """Returns a list of valid data for interval create tests."""
    return [
        {'name': gen_string('alpha', 15), 'interval': 'hourly'},
        {'name': gen_string('alphanumeric', 15), 'interval': 'hourly'},
        {'name': gen_string('numeric', 15), 'interval': 'hourly'},
        {'name': gen_string('latin1', 15), 'interval': 'hourly'},
        {'name': gen_string('utf8', 15), 'interval': 'hourly'},
        {'name': gen_string('html', 15), 'interval': 'hourly'},
        {'name': gen_string('alpha', 15), 'interval': 'daily'},
        {'name': gen_string('alphanumeric', 15), 'interval': 'daily'},
        {'name': gen_string('numeric', 15), 'interval': 'daily'},
        {'name': gen_string('latin1', 15), 'interval': 'daily'},
        {'name': gen_string('utf8', 15), 'interval': 'daily'},
        {'name': gen_string('html', 15), 'interval': 'daily'},
        {'name': gen_string('alpha', 15), 'interval': 'weekly'},
        {'name': gen_string('alphanumeric', 15), 'interval': 'weekly'},
        {'name': gen_string('numeric', 15), 'interval': 'weekly'},
        {'name': gen_string('latin1', 15), 'interval': 'weekly'},
        {'name': gen_string('utf8', 15), 'interval': 'weekly'},
        {'name': gen_string('html', 15), 'interval': 'weekly'},
    ]


@filtered_datapoint
def valid_name_interval_update_tests():
    """Returns a list of valid data for interval update tests."""
    return [
        {'name': gen_string('alpha', 15), 'interval': 'daily', 'new-interval': 'hourly'},
        {'name': gen_string('alphanumeric', 15), 'interval': 'daily', 'new-interval': 'hourly'},
        {'name': gen_string('numeric', 15), 'interval': 'daily', 'new-interval': 'hourly'},
        {'name': gen_string('latin1', 15), 'interval': 'daily', 'new-interval': 'hourly'},
        {'name': gen_string('utf8', 15), 'interval': 'daily', 'new-interval': 'hourly'},
        {'name': gen_string('html', 15), 'interval': 'daily', 'new-interval': 'hourly'},
        {'name': gen_string('alpha', 15), 'interval': 'weekly', 'new-interval': 'daily'},
        {'name': gen_string('alphanumeric', 15), 'interval': 'weekly', 'new-interval': 'daily'},
        {'name': gen_string('numeric', 15), 'interval': 'weekly', 'new-interval': 'daily'},
        {'name': gen_string('latin1', 15), 'interval': 'weekly', 'new-interval': 'daily'},
        {'name': gen_string('utf8', 15), 'interval': 'weekly', 'new-interval': 'daily'},
        {'name': gen_string('html', 15), 'interval': 'weekly', 'new-interval': 'daily'},
        {'name': gen_string('alpha', 15), 'interval': 'hourly', 'new-interval': 'weekly'},
        {'name': gen_string('alphanumeric', 15), 'interval': 'hourly', 'new-interval': 'weekly'},
        {'name': gen_string('numeric', 15), 'interval': 'hourly', 'new-interval': 'weekly'},
        {'name': gen_string('latin1', 15), 'interval': 'hourly', 'new-interval': 'weekly'},
        {'name': gen_string('utf8', 15), 'interval': 'hourly', 'new-interval': 'weekly'},
        {'name': gen_string('html', 15), 'interval': 'hourly', 'new-interval': 'weekly'},
    ]


def validate_task_status(sat, repo_id, org_id, max_tries=10):
    """Wait for foreman_tasks to complete or timeout

    :param repo_id: Repository Id to identify the correct task
    :param max_tries: Max tries to poll for the task creation
    :param org_id: Org ID to ensure valid check on busy Satellite
    """
    sat.wait_for_tasks(
        search_query='Actions::Katello::Repository::Sync'
        f' and organization_id = {org_id}'
        f' and resource_id = {repo_id}'
        ' and resource_type = Katello::Repository',
        max_tries=max_tries,
        search_rate=10,
    )


def validate_repo_content(sat, repo, content_types, after_sync=True):
    """Check whether corresponding content is present in repository before
    or after synchronization is performed

    :param repo: Repository instance to be validated
    :param content_types: List of repository content entities that should
        be validated (e.g. package, erratum)
    :param bool after_sync: Specify whether you perform validation before
        synchronization procedure is happened or after
    """
    repo = sat.cli.Repository.info({'id': repo['id']})
    for content in content_types:
        count = int(repo['content-counts'][content])
        assert count > 0 if after_sync else count == 0


@pytest.mark.parametrize('name', **parametrized(valid_data_list()))
def test_positive_create_with_name(module_org, name, module_target_sat):
    """Check if syncplan can be created with random names

    :id: dc0a86f7-4219-427e-92fd-29352dbdbfce

    :parametrized: yes

    :expectedresults: Sync plan is created and has random name

    :CaseImportance: Critical
    """
    sync_plan = module_target_sat.cli_factory.sync_plan(
        {'enabled': 'false', 'name': name, 'organization-id': module_org.id}
    )
    result = module_target_sat.cli.SyncPlan.info({'id': sync_plan['id']})
    assert result['name'] == name


@pytest.mark.parametrize('desc', **parametrized(valid_data_list()))
def test_positive_create_with_description(module_org, desc, module_target_sat):
    """Check if syncplan can be created with random description

    :id: a1bbe81b-60f5-4a19-b400-a02a23fa1dfa

    :parametrized: yes

    :expectedresults: Sync plan is created and has random description

    :CaseImportance: Critical
    """
    new_sync_plan = module_target_sat.cli_factory.sync_plan(
        {'enabled': 'false', 'description': desc, 'organization-id': module_org.id}
    )
    result = module_target_sat.cli.SyncPlan.info({'id': new_sync_plan['id']})
    assert result['description'] == desc


@pytest.mark.parametrize('test_data', **parametrized(valid_name_interval_create_tests()))
def test_positive_create_with_interval(module_org, test_data, module_target_sat):
    """Check if syncplan can be created with varied intervals

    :id: 32eb0c1d-0c9a-4fb5-a185-68d0d705fbce

    :parametrized: yes

    :expectedresults: Sync plan is created and has selected interval

    :CaseImportance: Critical
    """
    new_sync_plan = module_target_sat.cli_factory.sync_plan(
        {
            'enabled': 'false',
            'interval': test_data['interval'],
            'name': test_data['name'],
            'organization-id': module_org.id,
        }
    )
    result = module_target_sat.cli.SyncPlan.info({'id': new_sync_plan['id']})
    assert result['name'] == test_data['name']
    assert result['interval'] == test_data['interval']


@pytest.mark.parametrize('name', **parametrized(invalid_values_list()))
def test_negative_create_with_name(module_org, name, module_target_sat):
    """Check if syncplan can be created with random invalid names

    :id: 4c1aee35-271e-4ed8-9369-d2abfea8cfd9

    :parametrized: yes

    :expectedresults: Sync plan is not created

    :CaseImportance: Critical
    """
    with pytest.raises(CLIFactoryError, match='Could not create the sync plan:'):
        module_target_sat.cli_factory.sync_plan(
            {'enabled': 'false', 'name': name, 'organization-id': module_org.id}
        )


@pytest.mark.parametrize('new_desc', **parametrized(valid_data_list()))
def test_positive_update_description(module_org, new_desc, module_target_sat):
    """Check if syncplan description can be updated

    :id: 00a279cd-1f49-4ebb-a59a-6f0b4e4cb83c

    :parametrized: yes

    :expectedresults: Sync plan is created and description is updated
    """
    new_sync_plan = module_target_sat.cli_factory.sync_plan(
        {'enabled': 'false', 'organization-id': module_org.id}
    )
    module_target_sat.cli.SyncPlan.update({'description': new_desc, 'id': new_sync_plan['id']})
    result = module_target_sat.cli.SyncPlan.info({'id': new_sync_plan['id']})
    assert result['description'] == new_desc


@pytest.mark.parametrize('test_data', **parametrized(valid_name_interval_update_tests()))
def test_positive_update_interval(module_org, test_data, request, target_sat):
    """Check if syncplan interval can be updated

    :id: d676d7f3-9f7c-4375-bb8b-277d71af94b4

    :parametrized: yes

    :expectedresults: Sync plan interval is updated

    :CaseImportance: Critical
    """
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'false',
            'interval': test_data['interval'],
            'name': test_data['name'],
            'organization-id': module_org.id,
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    target_sat.cli.SyncPlan.update(
        {'id': new_sync_plan['id'], 'interval': test_data['new-interval']}
    )
    result = target_sat.cli.SyncPlan.info({'id': new_sync_plan['id']})
    assert result['interval'] == test_data['new-interval']


@pytest.mark.upgrade
def test_positive_update_sync_date(module_org, request, target_sat):
    """Check if syncplan sync date can be updated

    :id: f0c17d7d-3e86-4b64-9747-6cba6809815e

    :expectedresults: Sync plan is created and sync plan is updated

    :BZ: 1336790

    :CaseImportance: Critical
    """
    # Set the sync date to today/right now
    today = datetime.now()
    sync_plan_name = gen_string('alphanumeric')
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'name': sync_plan_name,
            'sync-date': today.strftime(SYNC_DATE_FMT),
            'organization-id': module_org.id,
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    # Assert that sync date matches data passed
    assert new_sync_plan['start-date'] == today.strftime("%Y/%m/%d %H:%M:%S")
    # Set sync date 5 days in the future
    future_date = today + timedelta(days=5)
    # Update sync interval
    target_sat.cli.SyncPlan.update(
        {'id': new_sync_plan['id'], 'sync-date': future_date.strftime(SYNC_DATE_FMT)}
    )
    # Fetch it
    result = target_sat.cli.SyncPlan.info({'id': new_sync_plan['id']})
    assert result['start-date'] != new_sync_plan['start-date']
    assert datetime.strptime(result['start-date'], '%Y/%m/%d %H:%M:%S') > datetime.strptime(
        new_sync_plan['start-date'], '%Y/%m/%d %H:%M:%S'
    ), 'Sync date was not updated'


@pytest.mark.upgrade
def test_positive_create_sync_date_custom_timezone(module_org, request, target_sat):
    """Check if syncplan sync date accepts supplied timezone

    :id: 9b5f421d-b925-4ea6-9000-e69ed5e35640

    :expectedresults: Sync plan is created with correct start date

    :BZ: 2015344

    :customerscenario: true

    :CaseImportance: High
    """
    future_date = datetime.now() + timedelta(days=5)
    format = '%Y-%m-%d %H:%M:%S CEST'
    sync_plan_name = gen_string('alphanumeric')
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'name': sync_plan_name,
            'sync-date': future_date.strftime(format),
            'organization-id': module_org.id,
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    expected_date = future_date + timedelta(hours=4)
    # Assert that sync date was converted to UTC correctly
    assert new_sync_plan['start-date'] == expected_date.strftime("%Y/%m/%d %H:%M:%S")


@pytest.mark.parametrize('name', **parametrized(valid_data_list()))
@pytest.mark.upgrade
def test_positive_delete_by_id(module_org, module_target_sat, name):
    """Check if syncplan can be created and deleted

    :id: b5d97c6b-aead-422b-8d9f-4a192bbe4a3b

    :parametrized: yes

    :expectedresults: Sync plan is created and then deleted

    :CaseImportance: Critical
    """
    new_sync_plan = module_target_sat.cli_factory.sync_plan(
        {'name': name, 'organization-id': module_org.id}
    )
    module_target_sat.cli.SyncPlan.delete({'id': new_sync_plan['id']})
    with pytest.raises(CLIReturnCodeError):
        module_target_sat.cli.SyncPlan.info({'id': new_sync_plan['id']})


def test_positive_info_enabled_field_is_displayed(module_org, request, target_sat):
    """Check if Enabled field is displayed in sync-plan info output

    :id: 54e3a4ea-315c-4026-8101-c4605ca6b874

    :expectedresults: Sync plan Enabled state is displayed

    :CaseImportance: Critical
    """
    new_sync_plan = target_sat.cli_factory.sync_plan({'organization-id': module_org.id})
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    result = target_sat.cli.SyncPlan.info({'id': new_sync_plan['id']})
    assert result.get('enabled') is not None


@pytest.mark.upgrade
def test_positive_info_with_assigned_product(module_org, module_target_sat):
    """Verify that sync plan info command returns list of products which
    are assigned to that sync plan

    :id: 7a7e5e40-7776-4d26-9173-73f00de6e8e9

    :customerscenario: true

    :expectedresults: Expected product information is returned in info
        command

    :BZ: 1390545

    :CaseImportance: Critical
    """
    prod1 = gen_string('alpha')
    prod2 = gen_string('alpha')
    sync_plan = module_target_sat.cli_factory.sync_plan(
        {
            'enabled': 'false',
            'organization-id': module_org.id,
            'sync-date': datetime.utcnow().strftime(SYNC_DATE_FMT),
        }
    )
    for prod_name in [prod1, prod2]:
        product = module_target_sat.cli_factory.make_product(
            {'organization-id': module_org.id, 'name': prod_name}
        )
        module_target_sat.cli.Product.set_sync_plan(
            {'id': product['id'], 'sync-plan-id': sync_plan['id']}
        )
    updated_plan = module_target_sat.cli.SyncPlan.info({'id': sync_plan['id']})
    assert len(updated_plan['products']) == 2
    assert {prod['name'] for prod in updated_plan['products']} == {prod1, prod2}


@pytest.mark.upgrade
def test_negative_synchronize_custom_product_past_sync_date(module_org, request, target_sat):
    """Verify product won't get synced immediately after adding association
    with a sync plan which has already been started

    :id: c80f5c0c-3863-47da-8d7b-7d65c73664b0

    :expectedresults: Repository was not synchronized

    :BZ: 1279539
    """
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'true',
            'organization-id': module_org.id,
            'sync-date': datetime.utcnow().strftime(SYNC_DATE_FMT),
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    product = target_sat.cli_factory.make_product({'organization-id': module_org.id})
    repo = target_sat.cli_factory.make_repository({'product-id': product['id']})
    target_sat.cli.Product.set_sync_plan({'id': product['id'], 'sync-plan-id': new_sync_plan['id']})
    with pytest.raises(AssertionError):
        validate_task_status(target_sat, repo['id'], module_org.id, max_tries=2)


@pytest.mark.upgrade
def test_positive_synchronize_custom_product_past_sync_date(module_org, request, target_sat):
    """Create a sync plan with a past datetime as a sync date, add a
    custom product and verify the product gets synchronized on the next
    sync occurrence

    :id: 21efdd08-698c-443c-a681-edce19a4c83a

    :expectedresults: Product is synchronized successfully.

    :BZ: 1279539
    """
    interval = 60 * 60  # 'hourly' sync interval in seconds
    delay = 2 * 60
    product = target_sat.cli_factory.make_product({'organization-id': module_org.id})
    repo = target_sat.cli_factory.make_repository({'product-id': product['id']})
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'true',
            'interval': 'hourly',
            'organization-id': module_org.id,
            'sync-date': (datetime.utcnow() - timedelta(seconds=interval - delay)).strftime(
                SYNC_DATE_FMT
            ),
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    # Associate sync plan with product
    target_sat.cli.Product.set_sync_plan({'id': product['id'], 'sync-plan-id': new_sync_plan['id']})
    # Wait quarter of expected time
    logger.info(
        f"Waiting {(delay / 4)} seconds to check product {product['name']}"
        f" was not synced by {new_sync_plan['name']}"
    )
    sleep(delay / 4)
    # Verify product has not been synced yet
    with pytest.raises(AssertionError):
        validate_task_status(target_sat, repo['id'], module_org.id, max_tries=1)
    validate_repo_content(target_sat, repo, ['errata', 'packages'], after_sync=False)
    # Wait until the first recurrence
    logger.info(
        f"Waiting {(delay * 3 / 4)} seconds to check product {product['name']}"
        f" was synced by {new_sync_plan['name']}"
    )
    sleep(delay * 3 / 4)
    # Verify product was synced successfully
    validate_task_status(target_sat, repo['id'], module_org.id)
    validate_repo_content(target_sat, repo, ['errata', 'package-groups', 'packages'])


@pytest.mark.upgrade
def test_positive_synchronize_custom_product_future_sync_date(module_org, request, target_sat):
    """Create a sync plan with sync date in a future and sync one custom
    product with it automatically.

    :id: 635bffe2-df98-4971-8950-40edc89e479e

    :expectedresults: Product is synchronized successfully.

    :BZ: 1655595
    """
    cron_multiple = 5  # sync event is on every multiple of this value, starting from 00 mins
    delay = (cron_multiple) * 60  # delay for sync date in seconds
    guardtime = 180  # do not start test less than 3 mins before the next sync event
    product = target_sat.cli_factory.make_product({'organization-id': module_org.id})
    repo = target_sat.cli_factory.make_repository({'product-id': product['id']})
    # if < 3 mins before the target event rather wait 3 mins for the next test window
    if int(datetime.utcnow().strftime('%M')) % (cron_multiple) > int(guardtime / 60):
        sleep(guardtime)
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'true',
            'organization-id': module_org.id,
            'sync-date': (datetime.utcnow().replace(second=0) + timedelta(seconds=delay)).strftime(
                SYNC_DATE_FMT
            ),
            'cron-expression': [f'*/{cron_multiple} * * * *'],
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    # Verify product is not synced and doesn't have any content
    validate_repo_content(target_sat, repo, ['errata', 'packages'], after_sync=False)
    # Associate sync plan with product
    target_sat.cli.Product.set_sync_plan({'id': product['id'], 'sync-plan-id': new_sync_plan['id']})
    # Wait quarter of expected time
    logger.info(
        f"Waiting {(delay / 4)} seconds to check product {product['name']}"
        f" was not synced by {new_sync_plan['name']}"
    )
    sleep(delay / 4)
    # Verify product has not been synced yet
    with pytest.raises(AssertionError):
        validate_task_status(target_sat, repo['id'], module_org.id, max_tries=1)
    validate_repo_content(target_sat, repo, ['errata', 'packages'], after_sync=False)
    # Wait the rest of expected time
    logger.info(
        f"Waiting {(delay * 3 / 4)} seconds to check product {product['name']}"
        f" was synced by {new_sync_plan['name']}"
    )
    sleep(delay * 3 / 4)
    # Verify product was synced successfully
    validate_task_status(target_sat, repo['id'], module_org.id)
    validate_repo_content(target_sat, repo, ['errata', 'package-groups', 'packages'])


@pytest.mark.upgrade
def test_positive_synchronize_custom_products_future_sync_date(module_org, request, target_sat):
    """Create a sync plan with sync date in a future and sync multiple
    custom products with multiple repos automatically.

    :id: dd262cf3-b836-422c-baca-b3adbc532478

    :expectedresults: Products are synchronized successfully.

    :BZ: 1655595
    """
    cron_multiple = 5  # sync event is on every multiple of this value, starting from 00 mins
    delay = (cron_multiple) * 60  # delay for sync date in seconds
    guardtime = 210  # do not start test less than 3.5 mins before the next sync event
    products = [
        target_sat.cli_factory.make_product({'organization-id': module_org.id}) for _ in range(2)
    ]
    repos = [
        target_sat.cli_factory.make_repository({'product-id': product['id']})
        for product in products
        for _ in range(2)
    ]
    # if < 3 mins before the target event rather wait 3 mins for the next test window
    if int(datetime.utcnow().strftime('%M')) % (cron_multiple) > int(guardtime / 60):
        sleep(guardtime)
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'true',
            'organization-id': module_org.id,
            'sync-date': (datetime.utcnow().replace(second=0) + timedelta(seconds=delay)).strftime(
                SYNC_DATE_FMT
            ),
            'cron-expression': [f'*/{cron_multiple} * * * *'],
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    # Verify products have not been synced yet
    logger.info(
        f"Check products {products[0]['name']} and {products[1]['name']}"
        f" were not synced before sync plan created in org {module_org.label}"
    )
    for repo in repos:
        with pytest.raises(AssertionError):
            validate_task_status(target_sat, repo['id'], module_org.id, max_tries=1)
    # Associate sync plan with products
    for product in products:
        target_sat.cli.Product.set_sync_plan(
            {'id': product['id'], 'sync-plan-id': new_sync_plan['id']}
        )
    # Wait fifth of expected time
    logger.info(
        f"Waiting {(delay / 5)} seconds to check products {products[0]['name']}"
        f" and {products[1]['name']} were not synced by {new_sync_plan['name']} "
    )
    sleep(delay / 5)
    # Verify products have not been synced yet
    for repo in repos:
        with pytest.raises(AssertionError):
            validate_task_status(target_sat, repo['id'], module_org.id, max_tries=1)
    # Wait the rest of expected time
    logger.info(
        f"Waiting {(delay * 4 / 5)} seconds to check product {products[0]['name']}"
        f" and {products[1]['name']} were synced by {new_sync_plan['name']}"
    )
    sleep(delay * 4 / 5)
    # Verify products were synced successfully
    for repo in repos:
        validate_task_status(target_sat, repo['id'], module_org.id)
        validate_repo_content(target_sat, repo, ['errata', 'package-groups', 'packages'])


@pytest.mark.run_in_one_thread
@pytest.mark.upgrade
def test_positive_synchronize_rh_product_past_sync_date(
    target_sat, function_sca_manifest_org, request
):
    """Create a sync plan with past datetime as a sync date, add a
    RH product and verify the product gets synchronized on the next sync
    occurrence

    :id: 47280ef4-3936-4dbc-8ed0-1076aa8d40df

    :expectedresults: Product is synchronized successfully.

    :BZ: 1279539
    """
    interval = 60 * 60  # 'hourly' sync interval in seconds
    delay = 2 * 60
    org = function_sca_manifest_org
    target_sat.cli.RepositorySet.enable(
        {
            'name': REPOSET['rhva6'],
            'organization-id': org.id,
            'product': PRDS['rhel'],
            'releasever': '6Server',
            'basearch': 'x86_64',
        }
    )
    product = target_sat.cli.Product.info({'name': PRDS['rhel'], 'organization-id': org.id})
    repo = target_sat.cli.Repository.info(
        {'name': REPOS['rhva6']['name'], 'product': product['name'], 'organization-id': org.id}
    )
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'true',
            'interval': 'hourly',
            'organization-id': org.id,
            'sync-date': (datetime.utcnow() - timedelta(seconds=interval - delay)).strftime(
                SYNC_DATE_FMT
            ),
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    # Associate sync plan with product
    target_sat.cli.Product.set_sync_plan({'id': product['id'], 'sync-plan-id': new_sync_plan['id']})
    # Wait quarter of expected time
    logger.info(
        f"Waiting {(delay / 4)} seconds to check product {product['name']}"
        f" was not synced by {new_sync_plan['name']}"
    )
    sleep(delay / 4)
    # Verify product has not been synced yet
    with pytest.raises(AssertionError):
        validate_task_status(target_sat, repo['id'], org.id, max_tries=1)
    validate_repo_content(target_sat, repo, ['errata', 'packages'], after_sync=False)
    # Wait the rest of expected time
    logger.info(
        f"Waiting {(delay * 3 / 4)} seconds to check product {product['name']}"
        f" was synced by {new_sync_plan['name']}"
    )
    sleep(delay * 3 / 4)
    # Verify product was synced successfully
    validate_task_status(target_sat, repo['id'], org.id)
    validate_repo_content(target_sat, repo, ['errata', 'packages'])


@pytest.mark.run_in_one_thread
@pytest.mark.upgrade
def test_positive_synchronize_rh_product_future_sync_date(
    target_sat, function_sca_manifest_org, request
):
    """Create a sync plan with sync date in a future and sync one RH
    product with it automatically.

    :id: 6ce2f777-f230-4bb8-9822-2cf3580c21aa

    :expectedresults: Product is synchronized successfully.

    :BZ: 1655595
    """
    cron_multiple = 5  # sync event is on every multiple of this value, starting from 00 mins
    delay = (cron_multiple) * 60  # delay for sync date in seconds
    guardtime = 180  # do not start test less than 2 mins before the next sync event
    org = function_sca_manifest_org
    target_sat.cli.RepositorySet.enable(
        {
            'name': REPOSET['rhva6'],
            'organization-id': org.id,
            'product': PRDS['rhel'],
            'releasever': '6Server',
            'basearch': 'x86_64',
        }
    )
    product = target_sat.cli.Product.info({'name': PRDS['rhel'], 'organization-id': org.id})
    repo = target_sat.cli.Repository.info(
        {'name': REPOS['rhva6']['name'], 'product': product['name'], 'organization-id': org.id}
    )
    # if < 3 mins before the target event rather wait 3 mins for the next test window
    if int(datetime.utcnow().strftime('%M')) % (cron_multiple) > int(guardtime / 60):
        sleep(guardtime)
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'true',
            'organization-id': org.id,
            'sync-date': (datetime.utcnow().replace(second=0) + timedelta(seconds=delay)).strftime(
                SYNC_DATE_FMT
            ),
            'cron-expression': [f'*/{cron_multiple} * * * *'],
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    # Verify product is not synced and doesn't have any content
    with pytest.raises(AssertionError):
        validate_task_status(target_sat, repo['id'], org.id, max_tries=1)
    validate_repo_content(target_sat, repo, ['errata', 'packages'], after_sync=False)
    # Associate sync plan with product
    target_sat.cli.Product.set_sync_plan({'id': product['id'], 'sync-plan-id': new_sync_plan['id']})
    # Wait fifth of expected time
    logger.info(
        f"Waiting {(delay / 5)} seconds to check product {product['name']}"
        f" was not synced by {new_sync_plan['name']}"
    )
    sleep(delay / 5)
    # Verify product has not been synced yet
    with pytest.raises(AssertionError):
        validate_task_status(target_sat, repo['id'], org.id, max_tries=1)
    validate_repo_content(target_sat, repo, ['errata', 'packages'], after_sync=False)
    # Wait the rest of expected time
    logger.info(
        f"Waiting {(delay * 4 / 5)} seconds to check product {product['name']}"
        f" was synced by {new_sync_plan['name']}"
    )
    sleep(delay * 4 / 5)
    # Verify product was synced successfully
    validate_task_status(target_sat, repo['id'], org.id)
    validate_repo_content(target_sat, repo, ['errata', 'packages'])


def test_positive_synchronize_custom_product_weekly_recurrence(module_org, request, target_sat):
    """Create a weekly sync plan with a past datetime as a sync date,
    add a custom product and verify the product gets synchronized on
    the next sync occurrence

    :id: 1079a66d-7c23-44f6-a4a0-47f4c74d92a4

    :expectedresults: Product is synchronized successfully.

    :BZ: 1396647
    """
    delay = 2 * 60
    product = target_sat.cli_factory.make_product({'organization-id': module_org.id})
    repo = target_sat.cli_factory.make_repository({'product-id': product['id']})
    start_date = datetime.utcnow() - timedelta(weeks=1) + timedelta(seconds=delay)
    new_sync_plan = target_sat.cli_factory.sync_plan(
        {
            'enabled': 'true',
            'interval': 'weekly',
            'organization-id': module_org.id,
            'sync-date': start_date.strftime(SYNC_DATE_FMT),
        }
    )
    sync_plan = target_sat.api.SyncPlan(organization=module_org.id, id=new_sync_plan['id']).read()
    request.addfinalizer(lambda: target_sat.api_factory.disable_syncplan(sync_plan))
    # Associate sync plan with product
    target_sat.cli.Product.set_sync_plan({'id': product['id'], 'sync-plan-id': new_sync_plan['id']})
    # Wait quarter of expected time
    logger.info(
        f"Waiting {(delay / 4)} seconds to check product {product['name']}"
        f" was not synced by {new_sync_plan['name']}"
    )
    sleep(delay / 4)
    # Verify product has not been synced yet
    with pytest.raises(AssertionError):
        validate_task_status(target_sat, repo['id'], module_org.id, max_tries=1)
    validate_repo_content(target_sat, repo, ['errata', 'packages'], after_sync=False)
    # Wait until the first recurrence
    logger.info(
        f"Waiting {(delay * 3 / 4)} seconds to check product {product['name']}"
        f" was synced by {new_sync_plan['name']}"
    )
    sleep(delay * 3 / 4)
    # Verify product was synced successfully
    validate_task_status(target_sat, repo['id'], module_org.id)
    validate_repo_content(target_sat, repo, ['errata', 'package-groups', 'packages'])
