"""Unit tests for the ``content_view_filters`` paths.

A full API reference for content views can be found here:
http://www.katello.org/docs/api/apidoc/content_view_filters.html


:Requirement: Contentviewfilter

:CaseAutomation: Automated

:CaseComponent: ContentViews

:team: Phoenix-content

:CaseImportance: High

"""

from random import randint

from fauxfactory import gen_integer, gen_string
import pytest
from requests.exceptions import HTTPError

from robottelo.config import settings
from robottelo.utils.datafactory import (
    parametrized,
    valid_data_list,
)


@pytest.fixture(scope='module')
def sync_repo(module_product, module_target_sat):
    repo = module_target_sat.api.Repository(product=module_product).create()
    repo.sync()
    return repo


@pytest.fixture(scope='module')
def sync_repo_module_stream(module_product, module_target_sat):
    repo = module_target_sat.api.Repository(
        content_type='yum', product=module_product, url=settings.repos.module_stream_1.url
    ).create()
    repo.sync()
    return repo


@pytest.fixture
def content_view(module_org, sync_repo, module_target_sat):
    return module_target_sat.api.ContentView(
        organization=module_org, repository=[sync_repo]
    ).create()


@pytest.fixture
def content_view_module_stream(module_org, sync_repo_module_stream, module_target_sat):
    return module_target_sat.api.ContentView(
        organization=module_org, repository=[sync_repo_module_stream]
    ).create()


class TestContentViewFilter:
    """Tests for content view filters."""

    @pytest.mark.parametrize('name', **parametrized(valid_data_list()))
    def test_positive_create_erratum_with_name(self, name, content_view, target_sat):
        """Create new erratum content filter using different inputs as a name

        :id: f78a133f-441f-4fcc-b292-b9eed228d755

        :parametrized: yes

        :expectedresults: Content view filter created successfully and has
            correct name and type

        """
        cvf = target_sat.api.ErratumContentViewFilter(content_view=content_view, name=name).create()
        assert cvf.name == name
        assert cvf.type == 'erratum'

    @pytest.mark.parametrize('name', **parametrized(valid_data_list()))
    def test_positive_create_pkg_group_with_name(self, name, content_view, target_sat):
        """Create new package group content filter using different inputs as a name

        :id: f9bfb6bf-a879-4f1a-970d-8f4df533cd59

        :parametrized: yes

        :expectedresults: Content view filter created successfully and has
            correct name and type

        :CaseImportance: Medium
        """
        cvf = target_sat.api.PackageGroupContentViewFilter(
            content_view=content_view,
            name=name,
        ).create()
        assert cvf.name == name
        assert cvf.type == 'package_group'

    @pytest.mark.parametrize('name', **parametrized(valid_data_list()))
    def test_positive_create_rpm_with_name(self, name, content_view, target_sat):
        """Create new RPM content filter using different inputs as a name

        :id: f1c88e72-7993-47ac-8fbc-c749d32bc768

        :parametrized: yes

        :expectedresults: Content view filter created successfully and has
            correct name and type

        :CaseImportance: Medium
        """
        cvf = target_sat.api.RPMContentViewFilter(content_view=content_view, name=name).create()
        assert cvf.name == name
        assert cvf.type == 'rpm'

    @pytest.mark.parametrize('inclusion', [True, False])
    def test_positive_create_with_inclusion(self, inclusion, content_view, target_sat):
        """Create new content view filter with different inclusion values

        :id: 81130dc9-ae33-48bc-96a7-d54d3e99448e

        :parametrized: yes

        :expectedresults: Content view filter created successfully and has
            correct inclusion value

        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view, inclusion=inclusion
        ).create()
        assert cvf.inclusion == inclusion

    @pytest.mark.parametrize('description', **parametrized(valid_data_list()))
    def test_positive_create_with_description(self, description, content_view, target_sat):
        """Create new content filter using different inputs as a description

        :id: e057083f-e69d-46e7-b336-45faaf67fa52

        :parametrized: yes

        :expectedresults: Content view filter created successfully and has
            correct description

        :CaseImportance: Low
        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            description=description,
        ).create()
        assert cvf.description == description

    def test_positive_create_with_repo(self, content_view, sync_repo, target_sat):
        """Create new content filter with repository assigned

        :id: 7207d4cf-3ccf-4d63-a50a-1373b16062e2

        :expectedresults: Content view filter created successfully and has
            repository assigned

        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
        ).create()
        assert cvf.repository[0].id == sync_repo.id

    @pytest.mark.parametrize('original_packages', [True, False])
    def test_positive_create_with_original_packages(
        self, original_packages, content_view, sync_repo, target_sat
    ):
        """Create new content view filter with different 'original packages'
        option values

        :id: 789abd8a-9e9f-4c7c-b1ac-6b69f23f77dd

        :parametrized: yes

        :expectedresults: Content view filter created successfully and has
            'original packages' value

        :CaseImportance: Medium
        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
            original_packages=original_packages,
        ).create()
        assert cvf.original_packages == original_packages

    def test_positive_create_with_docker_repos(
        self, module_product, sync_repo, content_view, module_target_sat
    ):
        """Create new docker repository and add to content view that has yum
        repo already assigned to it. Create new content view filter and assign
        it to the content view.

        :id: 2cd28bf3-cd8a-4943-8e63-806d3676ada1

        :expectedresults: Content view filter created successfully and has both
            repositories assigned (yum and docker)

        """
        docker_repository = module_target_sat.api.Repository(
            content_type='docker',
            docker_upstream_name='busybox',
            product=module_product.id,
            url=settings.container.registry_hub,
        ).create()
        content_view.repository = [sync_repo, docker_repository]
        content_view.update(['repository'])

        cvf = module_target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo, docker_repository],
        ).create()
        assert len(cvf.repository) == 2
        for repo in cvf.repository:
            assert repo.id in (sync_repo.id, docker_repository.id)

    def test_negative_create_without_cv(self, target_sat):
        """Try to create content view filter without providing content
        view

        :id: 3b5af53f-9533-482f-9ec9-b313cbb91dd7

        :expectedresults: Content view filter is not created

        :CaseImportance: Low
        """
        with pytest.raises(HTTPError):
            target_sat.api.RPMContentViewFilter(content_view=None).create()

    def test_negative_create_with_invalid_repo_id(self, content_view, target_sat):
        """Try to create content view filter using incorrect repository
        id

        :id: aa427770-c327-4ca1-b67f-a9a94edca784

        :expectedresults: Content view filter is not created

        :CaseImportance: Low
        """
        with pytest.raises(HTTPError):
            target_sat.api.RPMContentViewFilter(
                content_view=content_view,
                repository=[gen_integer(10000, 99999)],
            ).create()

    def test_positive_delete_by_id(self, content_view, target_sat):
        """Delete content view filter

        :id: 07caeb9d-419d-43f8-996b-456b0cc0f70d

        :expectedresults: Content view filter was deleted

        :CaseImportance: Critical
        """
        cvf = target_sat.api.RPMContentViewFilter(content_view=content_view).create()
        cvf.delete()
        with pytest.raises(HTTPError):
            cvf.read()

    @pytest.mark.parametrize('name', **parametrized(valid_data_list()))
    def test_positive_update_name(self, name, content_view, target_sat):
        """Update content view filter with new name

        :id: f310c161-00d2-4281-9721-6e45cbc5e4ec

        :parametrized: yes

        :expectedresults: Content view filter updated successfully and name was
            changed

        """
        cvf = target_sat.api.RPMContentViewFilter(content_view=content_view).create()
        cvf.name = name
        assert cvf.update(['name']).name == name

    @pytest.mark.parametrize('description', **parametrized(valid_data_list()))
    def test_positive_update_description(self, description, content_view, target_sat):
        """Update content view filter with new description

        :id: f2c5db28-0163-4cf3-929a-16ba1cb98c34

        :parametrized: yes

        :expectedresults: Content view filter updated successfully and
            description was changed

        :CaseImportance: Low
        """
        cvf = target_sat.api.RPMContentViewFilter(content_view=content_view).create()
        cvf.description = description
        cvf = cvf.update(['description'])
        assert cvf.description == description

    @pytest.mark.parametrize('inclusion', [True, False])
    def test_positive_update_inclusion(self, inclusion, content_view, target_sat):
        """Update content view filter with new inclusion value

        :id: 0aedd2d6-d020-4a90-adcd-01694b47c0b0

        :parametrized: yes

        :expectedresults: Content view filter updated successfully and
            inclusion value was changed

        """
        cvf = target_sat.api.RPMContentViewFilter(content_view=content_view).create()
        cvf.inclusion = inclusion
        cvf = cvf.update(['inclusion'])
        assert cvf.inclusion == inclusion

    def test_positive_update_repo(self, module_product, sync_repo, content_view, target_sat):
        """Update content view filter with new repository

        :id: 329ef155-c2d0-4aa2-bac3-79087ae49bdf

        :expectedresults: Content view filter updated successfully and has new
            repository assigned

        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
        ).create()
        new_repo = target_sat.api.Repository(product=module_product).create()
        new_repo.sync()
        content_view.repository = [new_repo]
        content_view.update(['repository'])
        cvf.repository = [new_repo]
        cvf = cvf.update(['repository'])
        assert len(cvf.repository) == 1
        assert cvf.repository[0].id == new_repo.id

    def test_positive_update_repos(self, module_product, sync_repo, content_view, target_sat):
        """Update content view filter with multiple repositories

        :id: 478fbb1c-fa1d-4fcd-93d6-3a7f47092ed3

        :expectedresults: Content view filter updated successfully and has new
            repositories assigned

        :CaseImportance: Low
        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
        ).create()
        repos = [
            target_sat.api.Repository(product=module_product).create() for _ in range(randint(3, 5))
        ]
        for repo in repos:
            repo.sync()
        content_view.repository = repos
        content_view.update(['repository'])
        cvf.repository = repos
        cvf = cvf.update(['repository'])
        assert {repo.id for repo in cvf.repository} == {repo.id for repo in repos}

    @pytest.mark.parametrize('original_packages', [True, False])
    def test_positive_update_original_packages(
        self, original_packages, sync_repo, content_view, target_sat
    ):
        """Update content view filter with new 'original packages' option value

        :id: 0c41e57a-afa3-479e-83ba-01f09f0fd2b6

        :parametrized: yes

        :expectedresults: Content view filter updated successfully and
            'original packages' value was changed

        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
        ).create()
        cvf.original_packages = original_packages
        cvf = cvf.update(['original_packages'])
        assert cvf.original_packages == original_packages

    def test_positive_update_repo_with_docker(
        self, module_product, sync_repo, content_view, target_sat
    ):
        """Update existing content view filter which has yum repository
        assigned with new docker repository

        :id: 909db0c9-764a-4ca8-9b56-cd8fedd543eb

        :expectedresults: Content view filter was updated successfully and has
            both repositories assigned (yum and docker)

        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
        ).create()
        docker_repository = target_sat.api.Repository(
            content_type='docker',
            docker_upstream_name='busybox',
            product=module_product.id,
            url=settings.container.registry_hub,
        ).create()
        content_view.repository = [sync_repo, docker_repository]
        content_view = content_view.update(['repository'])
        cvf.repository = [sync_repo, docker_repository]
        cvf = cvf.update(['repository'])
        assert len(cvf.repository) == 2
        for repo in cvf.repository:
            assert repo.id in (sync_repo.id, docker_repository.id)

    def test_negative_update_same_name(self, content_view, target_sat):
        """Try to update content view filter's name to already used one

        :id: b68569f1-9f7b-4a95-9e2a-a5da348abff7

        :expectedresults: Content view filter was not updated

        :CaseImportance: Low
        """
        name = gen_string('alpha', 8)
        target_sat.api.RPMContentViewFilter(content_view=content_view, name=name).create()
        cvf = target_sat.api.RPMContentViewFilter(content_view=content_view).create()
        cvf.name = name
        with pytest.raises(HTTPError):
            cvf.update(['name'])

    def test_negative_update_cv_by_id(self, content_view, target_sat):
        """Try to update content view filter using incorrect content
        view ID

        :id: a6477d5f-e4d2-44ba-84f5-8f9004b52eb2

        :expectedresults: Content view filter was not updated

        """
        cvf = target_sat.api.RPMContentViewFilter(content_view=content_view).create()
        cvf.content_view.id = gen_integer(10000, 99999)
        with pytest.raises(HTTPError):
            cvf.update(['content_view'])

    def test_negative_update_repo_by_id(self, sync_repo, content_view, target_sat):
        """Try to update content view filter using incorrect repository
        ID

        :id: 43ded66a-331c-4160-820d-261f973a7be2

        :expectedresults: Content view filter was not updated

        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            repository=[sync_repo],
        ).create()
        cvf.repository[0].id = gen_integer(10000, 99999)
        with pytest.raises(HTTPError):
            cvf.update(['repository'])

    def test_negative_update_repo(self, module_product, sync_repo, content_view, target_sat):
        """Try to update content view filter with new repository which doesn't
        belong to filter's content view

        :id: e11ba045-da8a-4f26-a0b9-3b1149358717

        :expectedresults: Content view filter was not updated

        :CaseImportance: Low
        """
        cvf = target_sat.api.RPMContentViewFilter(
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
        ).create()
        new_repo = target_sat.api.Repository(product=module_product).create()
        new_repo.sync()
        cvf.repository = [new_repo]
        with pytest.raises(HTTPError):
            cvf.update(['repository'])

    @pytest.mark.parametrize(
        'filter_type', ['erratum', 'package_group', 'rpm', 'modulemd', 'docker']
    )
    def test_positive_check_filter_applied_flag(
        self, filter_type, target_sat, module_product, content_view, sync_repo
    ):
        """Create a filter and check that CVV returns its usage properly.

        :id: 0e014d70-171b-4f4d-9c56-1f484cada0ee

        :parametrized: yes

        :steps:
            1. Create a filter for a CV.
            2. Publish new CV version and assert it has filter applied.
            3. Remove the filter.
            4. Publish new CV version and assert it has not filter applied.

        :expectedresults:
            1. Filters applied flag is set correctly per usage.

        :CaseImportance: Medium

        """
        cvf = target_sat.api.AbstractContentViewFilter(
            type=filter_type,
            content_view=content_view,
            inclusion=True,
            repository=[sync_repo],
        ).create()

        content_view.publish()
        content_view = content_view.read()
        cvv = content_view.version[0].read()
        assert cvv.filters_applied is True

        cvf.delete()
        content_view.publish()
        content_view = content_view.read()
        cvv = max(content_view.version, key=lambda x: x.id).read()
        assert cvv.filters_applied is False


class TestContentViewFilterSearch:
    """Tests that search through content view filters."""

    def test_positive_search_erratum(self, content_view, target_sat):
        """Search for an erratum content view filter's rules.

        :id: 6a86060f-6b4f-4688-8ea9-c198e0aeb3f6

        :expectedresults: The search completes with no errors.

        :CaseImportance: Critical

        :BZ: 1242534
        """
        cv_filter = target_sat.api.ErratumContentViewFilter(content_view=content_view).create()
        target_sat.api.ContentViewFilterRule(content_view_filter=cv_filter).search()

    def test_positive_search_package_group(self, content_view, target_sat):
        """Search for an package group content view filter's rules.

        :id: 832c50cc-c2c8-48c9-9a23-80956baf5f3c

        :expectedresults: The search completes with no errors.

        :CaseImportance: Critical
        """
        cv_filter = target_sat.api.PackageGroupContentViewFilter(content_view=content_view).create()
        target_sat.api.ContentViewFilterRule(content_view_filter=cv_filter).search()

    def test_positive_search_rpm(self, content_view, target_sat):
        """Search for an rpm content view filter's rules.

        :id: 1c9058f1-35c4-46f2-9b21-155ef988564a

        :expectedresults: The search completes with no errors.

        :CaseImportance: Critical
        """
        cv_filter = target_sat.api.RPMContentViewFilter(content_view=content_view).create()
        target_sat.api.ContentViewFilterRule(content_view_filter=cv_filter).search()


class TestContentViewFilterRule:
    """Tests for content view filter rules."""

    @pytest.mark.skipif(
        (not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url'
    )
    def test_positive_promote_module_stream_filter(
        self, module_org, content_view_module_stream, target_sat
    ):
        """Verify Module Stream, Errata Count after Promote, Publish for Content View
        with Module Stream Exclude Filter

        :id: 2f5d21b1-8cbc-4a77-b8a2-09aa466f56a3

        :expectedresults: Content View should get published and promoted successfully
            with correct Module Stream count.

        """
        # Exclude module stream filter
        content_view = content_view_module_stream
        cv_filter = target_sat.api.ModuleStreamContentViewFilter(
            content_view=content_view,
            inclusion=False,
        ).create()
        module_streams = target_sat.api.ModuleStream().search(
            query={'search': 'name="{}"'.format('duck')}
        )
        target_sat.api.ContentViewFilterRule(
            content_view_filter=cv_filter, module_stream=module_streams
        ).create()
        content_view.publish()
        content_view = content_view.read()
        content_view_version_info = content_view.version[0].read()
        assert len(content_view.repository) == 1
        assert len(content_view.version) == 1

        # the module stream and errata count based in filter after publish
        assert content_view_version_info.module_stream_count == 4
        assert content_view_version_info.errata_counts['total'] == 3

        # Promote Content View
        lce = target_sat.api.LifecycleEnvironment(organization=module_org).create()
        content_view.version[0].promote(data={'environment_ids': lce.id, 'force': False})
        content_view = content_view.read()
        content_view_version_info = content_view.version[0].read()

        # assert the module stream and errata count based in filter after promote
        assert content_view_version_info.module_stream_count == 4
        assert content_view_version_info.errata_counts['total'] == 3

    @pytest.mark.skipif(
        (not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url'
    )
    def test_positive_include_exclude_module_stream_filter(
        self, content_view_module_stream, target_sat
    ):
        """Verify Include and Exclude Errata filter(modular errata) automatically force the copy
           of the module streams associated to it.

        :id: 20540722-b163-4ebb-b18d-351444ef0c86

        :steps:
            1. Create Include Errata filter
            2. Publish content view, Verify errata and stream count.
            3. Delete Filter (As we can not update the filter inclusion type)
            4. Create Exclude Errata filter
            5. Publish content view, Verify errata and stream count

        :expectedresults: Module Stream count changes automatically after including or
            excluding modular errata

        """
        content_view = content_view_module_stream
        cv_filter = target_sat.api.ErratumContentViewFilter(
            content_view=content_view,
            inclusion=True,
        ).create()
        errata = target_sat.api.Errata().search(
            query={'search': f'errata_id="{settings.repos.module_stream_0.errata[2]}"'}
        )[0]
        target_sat.api.ContentViewFilterRule(content_view_filter=cv_filter, errata=errata).create()

        content_view.publish()
        content_view = content_view.read()
        content_view_version_info = content_view.version[0].read()

        # verify the module_stream_count and errata_count for Exclude Filter
        assert content_view_version_info.module_stream_count == 2
        assert content_view_version_info.errata_counts['total'] == 1

        # delete the previous content_view_filter
        cv_filter.delete()
        cv_filter = target_sat.api.ErratumContentViewFilter(
            content_view=content_view,
            inclusion=False,
        ).create()
        errata = target_sat.api.Errata().search(
            query={'search': f'errata_id="{settings.repos.module_stream_0.errata[2]}"'}
        )[0]
        target_sat.api.ContentViewFilterRule(content_view_filter=cv_filter, errata=errata).create()

        content_view.publish()
        content_view_version_info = content_view.read().version[1].read()

        # verify the module_stream_count and errata_count for Include Filter
        assert content_view_version_info.module_stream_count == 5
        assert content_view_version_info.errata_counts['total'] == 5

    @pytest.mark.skipif(
        (not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url'
    )
    def test_positive_multi_level_filters(self, content_view_module_stream, target_sat):
        """Verify promotion of Content View and Verify count after applying
        multi_filters (errata and module stream)

        :id: aeaf2ac7-eda2-4f07-a1dd-fe6057934697

        :expectedresults: Verify module stream and errata count should correct

        """
        content_view = content_view_module_stream
        # apply include errata filter
        cv_filter = target_sat.api.ErratumContentViewFilter(
            content_view=content_view,
            inclusion=True,
        ).create()
        errata = target_sat.api.Errata().search(
            query={'search': f'errata_id="{settings.repos.module_stream_0.errata[2]}"'}
        )[0]
        target_sat.api.ContentViewFilterRule(content_view_filter=cv_filter, errata=errata).create()

        # apply exclude module filter
        cv_filter = target_sat.api.ModuleStreamContentViewFilter(
            content_view=content_view,
            inclusion=False,
        ).create()
        module_streams = target_sat.api.ModuleStream().search(
            query={'search': 'name="{}"'.format('walrus')}
        )
        target_sat.api.ContentViewFilterRule(
            content_view_filter=cv_filter, module_stream=module_streams
        ).create()
        content_view.publish()
        content_view = content_view.read()
        content_view_version_info = content_view.read().version[0].read()
        # verify the module_stream_count and errata_count for Include Filter
        assert content_view_version_info.module_stream_count == 2
        assert content_view_version_info.errata_counts['total'] == 1

    @pytest.mark.skipif(
        (not settings.robottelo.REPOS_HOSTING_URL), reason='Missing repos_hosting_url'
    )
    def test_positive_dependency_solving_module_stream_filter(
        self, content_view_module_stream, target_sat
    ):
        """Verify Module Stream Content View Filter's with Dependency Solve 'Yes'.
        If dependency solving enabled then module streams with deps will not get fetched
        over even if the exclude filter has been applied.
        e.g. duck module stream is dependent on cockateel and lion, hence even if add only
        exclude filter on duck it will get ignored as it is fetched because of the other two
        dependencies, but if both cockateel and lion are in exclude filter, then duck will
        not get fetched

        :id: ea8a4d95-dc36-4102-b1a9-d53beaf14352

        :expectedresults: Verify dependent/non dependent module streams are getting fetched.

        """
        content_view = content_view_module_stream
        content_view.solve_dependencies = True
        content_view = content_view.update(['solve_dependencies'])
        cv_filter = target_sat.api.ModuleStreamContentViewFilter(
            content_view=content_view,
            inclusion=False,
        ).create()
        module_streams = target_sat.api.ModuleStream().search(
            query={'search': 'name="{}" and version="{}'.format('duck', '20180704244205')}
        )
        target_sat.api.ContentViewFilterRule(
            content_view_filter=cv_filter, module_stream=module_streams
        ).create()
        content_view.publish()
        content_view = content_view.read()
        content_view_version_info = content_view.read().version[0].read()

        # Total Module Stream Count = 7, Exclude filter rule get ignored.
        assert content_view_version_info.module_stream_count == 7
