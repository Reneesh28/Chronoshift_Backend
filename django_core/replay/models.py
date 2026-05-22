from django.db import models

class Replay(models.Model):
    timeline_id = models.CharField(max_length=24)
    branch_id = models.CharField(max_length=24)
    event_sequence = models.JSONField(default=list) # List of ordered event IDs
    current_step = models.IntegerField(default=0)
    status = models.CharField(max_length=50, default="playing") # playing, paused, completed
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "replays"

    def __str__(self):
        return f"Replay Session: {self.timeline_id} - Step: {self.current_step}"
