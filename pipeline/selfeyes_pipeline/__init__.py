# selfeyes-pipeline
# Automated ingestion pipeline for the selfeyes gallery.
#
# IMPORTANT: This pipeline detects eye *regions* (geometry) to locate where
# reflections may appear. It does NOT perform facial recognition, identity
# matching, or biometric embedding of any kind. No face-recognition library
# is imported. Future maintainers: keep it that way.
