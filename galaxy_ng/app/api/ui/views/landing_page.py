from galaxy_ng.app.access_control import access_policy
from random import sample
from rest_framework.response import Response
from pulp_ansible.app.models import CollectionVersion, AnsibleDistribution
from galaxy_ng.app.models import Namespace
from galaxy_ng.app import settings
from galaxy_ng.app.api import base as api_base


class LandingPageView(api_base.APIView):
    permission_classes = [access_policy.LandingPageAccessPolicy]
    action = "retrieve"

    def get(self, request, *args, **kwargs):
        golden_name = settings.GALAXY_API_DEFAULT_DISTRIBUTION_BASE_PATH

        distro = AnsibleDistribution.objects.get(base_path=golden_name)
        repository_version = distro.repository.latest_version()
        collection_count = CollectionVersion.objects.filter(
            pk__in=repository_version.content, is_highest=True
        ).count()

        partner_count = Namespace.objects.count()

        # If there are no partners dont show the recommendation for it
        recommendations = {}
        if partner_count > 0:
            namespace = sample(list(Namespace.objects.all()), 1)[0]
            recommendations = {
                "recs": [
                    {
                        "id": "ansible-partner",
                        "icon": "bulb",
                        "action": {
                            "title": "Check out our partner %s" % namespace.company,
                            "href": "./ansible/automation-hub/partners/%s" % namespace.name,
                        },
                        "description": "Discover automation from our partners.",
                    }
                ]
            }

        data = {
            "estate": {
                "items": [
                    {
                        "id": "ansible-collections",
                        "count": collection_count,
                        "shape": {
                            "title": "Collections",
                            "href": "./ansible/automation-hub/",
                        },
                    },
                    {
                        "id": "ansible-partners",
                        "count": partner_count,
                        "shape": {
                            "title": "Partners",
                            "href": "./ansible/automation-hub/partners/",
                        },
                    },
                ],
            },
            "recommendations": recommendations,
            "configTryLearn": {
                "configure": [
                    {
                        "shape": {
                            "title": "Sync Red Hat certified collections",
                            "description": (
                                "Configure access to sync collections ",
                                "to Private Automation Hub.",
                            ),
                            "link": {
                                "title": "Get started",
                                "href": "./ansible/automation-hub/token",
                            },
                        },
                    }
                ],
                "try": [
                    {
                        "shape": {
                            "title": "Install Private Automation Hub",
                            "link": {
                                "title": "Get started",
                                "external": True,
                                "href": (
                                    "https://access.redhat.com/documentation/en-us/"
                                    "red_hat_ansible_automation_platform/2.1/html/"
                                    "red_hat_ansible_automation_platform_installation_guide/index"
                                ),
                            },
                        },
                    },
                    {
                        "shape": {
                            "title": "Manage repositories in Private Automation Hub",
                            "description": (
                                "Add community and privately developed collections "
                                "to your Private Automation Hub."
                            ),
                            "link": {
                                "title": "Get started",
                                "external": True,
                                "href": (
                                    "https://access.redhat.com/documentation/en-us/"
                                    "red_hat_ansible_automation_platform/2.1/html/"
                                    "publishing_proprietary_content_collections_in_"
                                    "automation_hub/index"
                                ),
                            },
                        },
                    },
                ],
                "learn": [
                    {
                        "shape": {
                            "title": "Connect Automation Hub to your automation infrastructure",
                            "link": {
                                "title": "Get started",
                                "external": True,
                                "href": (
                                    "https://docs.ansible.com/ansible-tower/latest/html/userguide/"
                                    "projects.html?extIdCarryOver=true&"
                                    "sc_cid=701f2000001Css5AAC#using-collections-in-tower"
                                ),
                            },
                        },
                    },
                    {
                        "shape": {
                            "title": "Learn about namespaces",
                            "description": (
                                "Organize collections content into " "namespaces users can access."
                            ),
                            "link": {
                                "title": "Learn more",
                                "external": True,
                                "href": (
                                    "https://access.redhat.com/documentation"
                                    "/en-us/red_hat_ansible_automation_platform/2.1/html"
                                    "/curating_collections_using_namespaces_in_automation_hub/index"
                                ),
                            },
                        },
                    },
                    {
                        "shape": {
                            "title": "Explore Red Hat certified collections",
                            "link": {
                                "title": "Learn more",
                                "external": True,
                                "href": "https://www.ansible.com/partners",
                            },
                        },
                    },
                ],
            },
        }

        return Response(data)
