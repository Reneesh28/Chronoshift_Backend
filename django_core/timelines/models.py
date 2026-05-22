from django.db import models

class Timeline(models.Model):
    user_id = models.IntegerField(help_text="ID of the Django user who owns this timeline")
    title = models.CharField(max_length=255)
    description = models.TextField()
    root_branch_id = models.CharField(max_length=24, null=True, blank=True, help_text="MongoDB ObjectId of the root branch")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        managed = False
        db_table = "timelines"

    def __str__(self):
        return self.title
