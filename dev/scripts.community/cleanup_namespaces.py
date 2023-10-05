import argparse
import re

from django.contrib.auth import get_user_model

from galaxy_ng.app.models import Namespace
from galaxy_ng.app.api.v1.models import LegacyNamespace
from galaxy_ng.app.api.v1.models import LegacyRole
from galaxy_ng.app.utils import rbac

from pulp_ansible.app.models import CollectionVersion


User = get_user_model()


allowed_to_fix = [
    'yuvarajcloud',
    'wpninfra',
    'vladgh',
    'tonyskapunk',
    'shanemcd',
    'saiello',
    'rtnp',
    'rndmh3ro',
    'rathbunr',
    'nixocio',
    'navdeepsachdeva',
    'mdellweg',
    'maxamillion',
    'kubealex',
    'jorti',
    'rezizter',
    'kolesaev',
    'koalakangaroo',
    'jorneilander',
    'jgoos',
    'jeichler',
    'himdel',
    'geoffreyvanwyk',
    'charlesrocket',
    'borari',
]

ignore_list = [
    'spk',
    'sigma',
    'rmasters',
    'network',
    'roopamg',
    'wholeshoot',
    'tmiller',
    'kmf',
    'jdavid',
]


def strip_number_from_string(input_string):
    #match = re.search(r'(\D+)(\d+)$', input_string)
    #match = re.search(r'([\w\d_]*)(\d+)$', input_string)
    match = re.search(r'([\w_]*[A-Za-z_])(\d+)$', input_string)
    if match:
        prefix = match.group(1)
        number = match.group(2)
        return prefix, int(number)
    else:
        return input_string, None


def do_cleanup():


    # make a list of all namespace names
    ns_names = []
    for ns_name in Namespace.objects.values_list('name', flat=True):
        ns_names.append(ns_name)

    # map out names with a common prefix and a numbered suffix
    ns_map = {}
    for ns_name in ns_names:
        prefix, number = strip_number_from_string(ns_name)
        #print(f'{prefix} {number}')
        if number is None:
            if prefix not in ns_map:
                ns_map[prefix] = [prefix]
            continue
        if prefix not in ns_map:
            ns_map[prefix] = []
        ns_map[prefix].append(ns_name)

    # check each ns for content ...
    ns_keys = sorted(list(ns_map.keys()))
    counter = 0
    for ns_key in ns_keys:

        if ns_key in ignore_list:
            continue

        if len(ns_map[ns_key]) <= 1:
            continue

        ns = Namespace.objects.filter(name=ns_key).first()
        if not ns:
            continue

        if ns:
            collection_count = CollectionVersion.objects.filter(namespace=ns).count()
            owners = rbac.get_v3_namespace_owners(ns)
            legacy_count = LegacyNamespace.objects.filter(namespace=ns).count()
        else:
            collection_count = None
            owners = None
            legacy_count = None

        # is there a matching user for this namespace ...?
        found_user = User.objects.filter(username=ns_key).first()
        if not found_user:
            continue

        counter += 1
        print('-' * 100)
        print(f'{counter}. {ns_key}')

        print('')
        print(f'\tuser: {found_user}')

        print('')
        print(f'\tnamespace:{ns} legacy-ns:{legacy_count} collections:{collection_count} owners:{owners}')
        print('')

        for dupe_name in ns_map[ns_key]:

            if dupe_name == ns_key:
                continue

            dupe_ns = Namespace.objects.filter(name=dupe_name).first()
            collection_count = CollectionVersion.objects.filter(namespace=dupe_name).count()
            dupe_owners = rbac.get_v3_namespace_owners(dupe_ns)
            dupe_legacy_count = LegacyNamespace.objects.filter(namespace=dupe_ns).count()

            print(f'\t\tdupe:{dupe_name} legacy-ns:{dupe_legacy_count} collections:{collection_count} owners:{dupe_owners}')

            if dupe_legacy_count > 0:
                for lns in LegacyNamespace.objects.filter(namespace=dupe_ns):
                    print(f'\t\t\tlegacy:{lns.name} v3:{lns.namespace}')
                    print(f'\t\t\t\tFIXME - set v1:{lns} provider to {ns}')
                    if ns_key in allowed_to_fix:
                        lns.namespace = ns
                        lns.save()

                    #for role in LegacyRole.objects.filter(namespace=lns):
                    #    print(f'\t\t\t\t{role.namespace}.{role.name}')

            if (collection_count + dupe_legacy_count) == 0:
                for dupe_owner in dupe_owners:
                    if dupe_owner not in owners:
                        print(f'\t\t\tFIXME - add {dupe_owner} to {ns_key} owners')
                        if ns_key in allowed_to_fix:
                            rbac.add_user_to_v3_namespace(dupe_owner, ns)

                print(f'\t\t\tFIXME - delete v3 {dupe_name}')
                if ns_key in allowed_to_fix:
                    dupe_ns.delete()

    # import epdb; epdb.st()


do_cleanup()
