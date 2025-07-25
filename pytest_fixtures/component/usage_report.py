from datetime import datetime

from fauxfactory import gen_string
import pytest
import yaml

from robottelo.constants import DataFile


def process_keys(keys):
    # get unique highest level items from report keys
    return set([key.split('|')[0] for key in keys])


@pytest.fixture(scope='module')
def module_generate_report(module_target_sat):
    filename = f'usage_report-{datetime.timestamp(datetime.now())}-{gen_string("alphanumeric")}.yml'
    result = module_target_sat.cli.SatelliteMaintainReport.generate({'output': filename})
    assert result.status == 0, 'failed to generate report'
    return module_target_sat.load_remote_yaml_file(filename)


@pytest.fixture(scope='module')
def module_report_keys(module_generate_report):
    return process_keys(module_generate_report.keys())


@pytest.fixture(scope='module')
def module_expected_keys():
    return process_keys(yaml.safe_load(DataFile.USAGE_REPORT_ITEMS.read_text()).keys())
