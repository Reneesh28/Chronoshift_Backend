from django.db import models

class Branch(models.Model):
    timeline_id = models.CharField(max_length=24, help_text="MongoDB ObjectId of the parent timeline")
    parent_branch_id = models.CharField(max_length=24, null=True, blank=True, help_text="MongoDB ObjectId of the parent branch")
    branch_name = models.CharField(max_length=255)
    decision_trigger = models.TextField(help_text="Decision that triggered this branch")
    divergence_score = models.FloatField(default=0.0)
    depth_level = models.IntegerField(default=1)
    status = models.CharField(max_length=50, default="active") # active, merged
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "branches"

    def __str__(self):
        return f"{self.branch_name} (Timeline: {self.timeline_id})"


class Event(models.Model):
    timeline_id = models.CharField(max_length=24)
    branch_id = models.CharField(max_length=24)
    event_type = models.CharField(max_length=50) # decision, simulation, replay, divergence
    event_value = models.TextField()
    created_by = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "events"

    def __str__(self):
        return f"Event {self.event_type} - {self.branch_id}"


class Simulation(models.Model):
    timeline_id = models.CharField(max_length=24)
    source_branch_id = models.CharField(max_length=24)
    generated_branch_ids = models.JSONField(default=list) # List of generated branch IDs
    simulation_status = models.CharField(max_length=50, default="queued") # queued, processing, completed, failed
    divergence_results = models.JSONField(default=dict) # Mapping of branch ID to divergence score
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = "simulations"

    def __str__(self):
        return f"Simulation {self.id} Status: {self.simulation_status}"


class AISummary(models.Model):
    timeline_id = models.CharField(max_length=24)
    branch_id = models.CharField(max_length=24)
    simulation_id = models.CharField(max_length=24)
    risk_score = models.FloatField()
    confidence_score = models.FloatField()
    summary = models.TextField()
    generated_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        managed = False
        db_table = "ai_summaries"

    def __str__(self):
        return f"AI Summary for Branch: {self.branch_id}"
