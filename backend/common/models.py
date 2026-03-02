from django.db import models

class Code(models.Model):
    group = models.CharField(max_length=50)
    code = models.CharField(max_length=50)
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name