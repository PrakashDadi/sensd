from django.contrib.gis.db import models
from encrypted_fields.fields import (
    EncryptedCharField,
    EncryptedTextField,
    EncryptedIntegerField,
    EncryptedFloatField,
    EncryptedEmailField,
    EncryptedDateField,
    EncryptedDateTimeField,
)


# Unified Store Model


class Store(models.Model):
    STORE_CHOICES = [
        ('Walmart', 'Walmart'),
        ('Schnucks', 'Schnucks'),
        ('Save A Lot', 'Save A Lot'),
        ('Whole Foods', 'Whole Foods'),
    ]

    object_id = EncryptedCharField(max_length=20, primary_key=True)
    company = EncryptedCharField(max_length=100, choices=STORE_CHOICES)
    street = EncryptedCharField(max_length=225)
    city = EncryptedCharField(max_length=100)
    state = EncryptedCharField(max_length=100)
    zip_code = EncryptedCharField(max_length=20)
    phone = EncryptedCharField(max_length=20, blank=True, null=True)
    latitude = EncryptedFloatField()
    longitude = EncryptedFloatField()
    location = models.PointField()

    def __str__(self):
        return f"{self.company} - {self.city}"


class FSISCoordinates(models.Model):
    object_id = EncryptedIntegerField(primary_key=True)
    company = EncryptedCharField(max_length=300)
    est_number = EncryptedCharField(max_length=255)
    establishment_id = EncryptedCharField(max_length=255)
    street = EncryptedCharField(max_length=255)
    city = EncryptedCharField(max_length=100)
    state = EncryptedCharField(max_length=10)
    zip_code = EncryptedCharField(max_length=20)
    phone = EncryptedCharField(max_length=30, blank=True, null=True)
    activities = EncryptedTextField(blank=True, null=True)
    dbas = EncryptedTextField(blank=True, null=True)
    county = EncryptedCharField(max_length=100)
    latitude = EncryptedFloatField()
    longitude = EncryptedFloatField()
    location = models.PointField()

    def __str__(self):
        return f"{self.company} - {self.city}, {self.state}"
    
class FlowWithQuantity(models.Model):
    """Points representing flow origin/destination nodes with quantity data."""
    object_id     = EncryptedIntegerField(unique=True)
    product_type_i = EncryptedCharField(max_length=50)
    from_id       = EncryptedCharField(max_length=100)
    from_node     = EncryptedCharField(max_length=200)
    from_city_area = EncryptedCharField(max_length=200, blank=True)
    from_state    = EncryptedCharField(max_length=10, blank=True)
    from_latitude = EncryptedFloatField()
    from_longitude = EncryptedFloatField()
    product_type_j = EncryptedCharField(max_length=50)
    to_id         = EncryptedCharField(max_length=100)
    to_node       = EncryptedCharField(max_length=200)
    to_city_area  = EncryptedCharField(max_length=200, blank=True)
    to_state      = EncryptedCharField(max_length=10, blank=True)
    to_latitude   = EncryptedFloatField()
    to_longitude  = EncryptedFloatField()
    quantity      = EncryptedFloatField()
    location      = models.PointField(srid=4326)
 
    def __str__(self):
        return f"{self.from_id} → {self.to_id} ({self.product_type_i})"
    
class FlowLineQuantity(models.Model):
    """LineStrings representing supply chain flows with quantity and product type."""
    oid           = EncryptedIntegerField(unique=True)
    product_type_i = EncryptedCharField(max_length=50)
    from_id       = EncryptedCharField(max_length=100)
    from_node     = EncryptedCharField(max_length=200)
    from_city_area = EncryptedCharField(max_length=200, blank=True)
    from_state    = EncryptedCharField(max_length=10, blank=True)
    from_latitude = EncryptedFloatField()
    from_longitude = EncryptedFloatField()
    product_type_j = EncryptedCharField(max_length=50)
    to_id         = EncryptedCharField(max_length=100)
    to_node       = EncryptedCharField(max_length=200)
    to_city_area  = EncryptedCharField(max_length=200, blank=True)
    to_state      = EncryptedCharField(max_length=10, blank=True)
    to_latitude   = EncryptedFloatField()
    to_longitude  = EncryptedFloatField()
    quantity      = EncryptedFloatField()
    orig_fid      = EncryptedIntegerField(null=True, blank=True)
    shape_length  = EncryptedFloatField(null=True, blank=True)
    line          = models.LineStringField(srid=4326)

    def __str__(self):
        return f"{self.from_id} → {self.to_id} ({self.product_type_i})"


class CountyBivariate(models.Model):
    geoid = EncryptedCharField(max_length=20, primary_key=True)
    geo_id = EncryptedCharField(max_length=50, null=True, blank=True)
    state = EncryptedCharField(max_length=5, null=True, blank=True)
    county = EncryptedCharField(max_length=5, null=True, blank=True)
    name = EncryptedCharField(
        max_length=200, null=True, blank=True)   # County name (NAME)
    lsad = EncryptedCharField(max_length=50, null=True, blank=True)
    state_name = EncryptedCharField(max_length=100, null=True, blank=True)
    stusps = EncryptedCharField(
        max_length=5, null=True, blank=True)   # State USPS code
    county_name = EncryptedCharField(max_length=200, null=True, blank=True)
    censusarea = EncryptedFloatField(null=True, blank=True)
    objectid = EncryptedIntegerField(null=True, blank=True)
    statefp = EncryptedCharField(max_length=5, null=True, blank=True)
    countyfp = EncryptedCharField(max_length=5, null=True, blank=True)
    countyns = EncryptedCharField(max_length=20, null=True, blank=True)
    intptlat = EncryptedFloatField(null=True, blank=True)
    intptlon = EncryptedFloatField(null=True, blank=True)
    salmonella_rate = EncryptedFloatField(null=True, blank=True)
    social_vulnerability = EncryptedFloatField(null=True, blank=True)
    salmonella_class = EncryptedCharField(max_length=50, null=True, blank=True)
    svi_class = EncryptedCharField(max_length=50, null=True, blank=True)
    bivariate_class = EncryptedCharField(max_length=50, null=True, blank=True)
    overall_food_insecurity = EncryptedFloatField(null=True, blank=True)
    child_food_insecurity = EncryptedFloatField(null=True, blank=True)
    rpl_themes = EncryptedFloatField(null=True, blank=True)
    geom = models.MultiPolygonField(srid=4326)

    def __str__(self):
        return f"{self.county_name}, {self.state_name}"


class USStates(models.Model):
    state_name = EncryptedCharField(max_length=100)
    state_fips = EncryptedCharField(max_length=10)
    geom = models.MultiPolygonField(srid=4326)

    def __str__(self):
        return f"{self.state_name}"

class UploadedLayer(models.Model):
    """Model to store user-uploaded geospatial data as an encrypted GeoJSON string."""
    id = models.AutoField(primary_key=True)
    name = EncryptedCharField(max_length=255)
    file_type = EncryptedCharField(max_length=10)  # e.g., CSV, JSON, XLSX
    layer_type = EncryptedCharField(
        max_length=50, null=True, blank=True)  # e.g., Point, Polygon
    feature_count = EncryptedIntegerField(default=0)
    # EncryptedTextField is suitable for storing large GeoJSON strings
    geojson_data = EncryptedTextField()
    uploaded_at = EncryptedDateTimeField(auto_now_add=True)

    def __str__(self):
        return f"[{self.id}] {self.name} ({self.feature_count} features)"