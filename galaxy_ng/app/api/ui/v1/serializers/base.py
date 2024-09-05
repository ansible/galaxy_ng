from rest_framework import serializers


class Serializer(serializers.Serializer):
    def __init_subclass__(cls, **kwargs):
        """Set default attributes in subclasses.

        Sets the default for the ``ref_name`` attribute for a ModelSerializers's
        ``Meta`` class.

        If the ``Meta.ref_name`` attribute is not yet defined, set it according
        to the best practice established within Pulp: ``<app label>.<model class
        name>``. ``app_label`` is used to create a per plugin namespace.

        Serializers in pulpcore (``app_label`` is 'core') will not be
        namespaced, i.e. ref_name is not set in this case.

        The ``ref_name`` default value is computed using ``Meta.model``. If that
        is not defined (because the class must be subclassed to be useful),
        `ref_name` is not set.

        """
        super().__init_subclass__(**kwargs)
        meta = cls.Meta

        try:
            if not hasattr(meta, "ref_name"):
                meta.ref_name = f"galaxy.{cls.__name__.replace('Serializer', '')}"
        except AttributeError:
            pass

    class Meta:
        pass
