from galaxy_ng.app.models import Namespace

print('creating autohubtest2 namespace')
ns = Namespace.objects.create(name='autohubtest2')
ns.save()
