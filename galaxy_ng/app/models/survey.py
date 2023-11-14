from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

from pulp_ansible.app.models import Collection
from galaxy_ng.app.api.v1.models import LegacyRole


User = get_user_model()


class SurveyBase(models.Model):

    class Meta:
        abstract = True

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    docs = models.IntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    ease_of_use = models.IntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    does_what_it_says = models.IntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    works_as_is = models.IntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )

    used_in_production = models.IntegerField(
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)]
    )


class CollectionSurvey(SurveyBase):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'collection',)


class LegacyRoleSurvey(SurveyBase):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(LegacyRole, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('user', 'role',)


class CollectionSurveyRollup(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)


class LegacyRoleSurveyRollup(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    role = models.ForeignKey(LegacyRole, on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
