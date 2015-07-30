"""Unit tests for the ``subscription`` paths.

A full API reference for subscriptions can be found here:
https://<sat6.com>/apidoc/v2/subscriptions.html

"""
from nailgun import entities
from nailgun.entity_mixins import TaskFailedError
from robottelo.common import manifests
from robottelo.test import APITestCase


class SubscriptionsTestCase(APITestCase):
    """Tests for the ``subscriptions`` path."""

    def test_positive_create_1(self):
        """@Test: Upload a manifest.

        @Assert: Manifest is uploaded successfully

        @Feature: Subscriptions

        """
        org = entities.Organization().create()
        sub = entities.Subscription()
        with open(manifests.clone(), 'rb') as manifest:
            sub.upload({'organization_id': org.id}, manifest)

    def test_positive_delete_1(self):
        """@Test: Delete an Uploaded manifest.

        @Assert: Manifest is Deleted successfully

        @Feature: Subscriptions

        """
        org = entities.Organization().create()
        sub = entities.Subscription(organization=org)
        payload = {'organization_id': org.id}
        with open(manifests.clone(), 'rb') as manifest:
            sub.upload(payload, manifest)
        self.assertGreater(len(sub.search()), 0)
        sub.delete_manifest(payload)
        self.assertEqual(len(sub.search()), 0)

    def test_negative_create_1(self):
        """@Test: Upload the same manifest to two organizations.

        @Assert: The manifest is not uploaded to the second organization.

        @Feature: Subscriptions

        """
        orgs = [entities.Organization().create() for _ in range(2)]
        sub = entities.Subscription()
        with open(manifests.clone(), 'rb') as manifest:
            sub.upload({'organization_id': orgs[0].id}, manifest)
            with self.assertRaises(TaskFailedError):
                sub.upload({'organization_id': orgs[1].id}, manifest)
        self.assertEqual(
            len(entities.Subscription(organization=orgs[1]).search()), 0)
