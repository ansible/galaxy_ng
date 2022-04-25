from galaxy_ng.app.models import Namespace

print('creating autohubtest2+3 namespace(s)')
for nsname in ['autohubtest2', 'autohubtest3']:
    ns = Namespace.objects.get_or_create(name=nsname)
