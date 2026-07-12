import uuid
from django.db import models


class Tournament(models.Model):
    api_id   = models.CharField(max_length=20, unique=True)
    slug     = models.CharField(max_length=60)
    name     = models.CharField(max_length=120)
    category = models.CharField(max_length=80, blank=True)

    def __str__(self): return self.name


class Fixture(models.Model):
    STATUS = [("upcoming","Upcoming"),("live","Live"),("finished","Finished")]

    fixture_id = models.CharField(max_length=60, unique=True)
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE,
                                   related_name="fixtures", null=True)
    home_team  = models.CharField(max_length=120)
    away_team  = models.CharField(max_length=120)
    kickoff    = models.DateTimeField(null=True, blank=True)
    status     = models.CharField(max_length=20, choices=STATUS, default="upcoming")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["kickoff"]
        indexes  = [models.Index(fields=["kickoff"]),
                    models.Index(fields=["status"])]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team}"


class BookmakerOdds(models.Model):
    MARKETS = [
        ("FT_1X2","Full Time 1X2"), ("H2H","Head to Head 2-way"),
        ("BTTS","Both Teams To Score"),
        ("OU25","Over/Under 2.5"),  ("OU15","Over/Under 1.5"),
        ("OU35","Over/Under 3.5"),
    ]
    SOURCES = [
        ("oddspapi","OddsPapi"), ("theodds","The-Odds-API"), ("manual","Manual"),
    ]

    fixture    = models.ForeignKey(Fixture, on_delete=models.CASCADE, related_name="odds")
    bookmaker  = models.CharField(max_length=40)
    market     = models.CharField(max_length=20, choices=MARKETS)
    source     = models.CharField(max_length=20, choices=SOURCES, default="oddspapi")
    is_active  = models.BooleanField(default=True)
    leg1       = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    leg2       = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    leg3       = models.DecimalField(max_digits=8, decimal_places=3, null=True, blank=True)
    leg1_label = models.CharField(max_length=20, default="")
    leg2_label = models.CharField(max_length=20, default="")
    leg3_label = models.CharField(max_length=20, default="")
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("fixture","bookmaker","market")
        indexes = [models.Index(fields=["fixture","market"]),
                   models.Index(fields=["bookmaker"])]

    def __str__(self):
        return f"{self.bookmaker} | {self.fixture} | {self.market}"

    def as_dict(self):
        out = {}
        for label, val in [(self.leg1_label, self.leg1),
                           (self.leg2_label, self.leg2),
                           (self.leg3_label, self.leg3)]:
            if label and val:
                out[label.lower()] = float(val)
        return out


class ArbitrageResult(models.Model):
    fixture      = models.ForeignKey(Fixture, on_delete=models.CASCADE,
                                     related_name="arb_results")
    market       = models.CharField(max_length=20)
    pair_label   = models.CharField(max_length=30)
    books        = models.JSONField()
    odds         = models.JSONField()
    stakes       = models.JSONField()
    bankroll     = models.DecimalField(max_digits=12, decimal_places=2, default=10000)
    payout       = models.DecimalField(max_digits=12, decimal_places=2)
    profit       = models.DecimalField(max_digits=12, decimal_places=2)
    profit_pct   = models.DecimalField(max_digits=8,  decimal_places=3)
    arb_sum      = models.DecimalField(max_digits=8,  decimal_places=4)
    is_high_odds = models.BooleanField(default=False)
    scanned_at   = models.DateTimeField(auto_now_add=True)
    is_valid     = models.BooleanField(default=True)

    class Meta:
        ordering = ["-profit_pct"]
        indexes  = [models.Index(fields=["scanned_at"]),
                    models.Index(fields=["profit_pct"])]

    def __str__(self):
        return f"{self.fixture} | {self.market} | +{self.profit_pct}%"


class Report(models.Model):
    """A generated, traceable arbitrage report.

    Each row is an immutable snapshot of the arbs at generation time, sealed
    with a content hash + HMAC signature so a printed PDF can be verified as
    genuinely produced by this system (the QR code carries these fields)."""
    report_id    = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    title        = models.CharField(max_length=120, default="Arbitrage Report")
    sport        = models.CharField(max_length=40,  blank=True)
    market       = models.CharField(max_length=20,  blank=True)
    target       = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    bankroll     = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    books        = models.JSONField(default=list)
    arb_count    = models.IntegerField(default=0)
    total_profit = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    snapshot     = models.JSONField(default=list)         # frozen, sized arb rows
    content_hash = models.CharField(max_length=64, blank=True)   # sha256 of snapshot
    signature    = models.CharField(max_length=64, blank=True)   # hmac-sha256 proof
    pdf_path     = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes  = [models.Index(fields=["created_at"]),
                    models.Index(fields=["report_id"])]

    def __str__(self):
        return f"Report {self.short_id} | {self.created_at:%Y-%m-%d %H:%M} | {self.arb_count} arbs"

    @property
    def short_id(self) -> str:
        return str(self.report_id)[:8]
