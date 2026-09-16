from django.contrib import admin
from .models import AnalysisRun, Store, UploadedDataset, UploadedFeature

# Register the Store model
admin.site.register(Store)
admin.site.register(UploadedDataset)
admin.site.register(UploadedFeature)
admin.site.register(AnalysisRun)
